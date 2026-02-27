import base64
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class ProctorResult:
    violation: bool
    message: Optional[str] = None


class ProctorEngine:
    """Lightweight proctoring engine.

    Design goals:
    - Fast enough for low-end laptops: low FPS, small frames, simple models.
    - Optional CV dependencies: works even if OpenCV is not installed.
    - Stateless per-call; stateful per-session via `session_state` dict.

    Inputs:
    - `image_data_url`: data:image/jpeg;base64,... or None
    - `audio_level`: float 0..1 (client-computed)

    Outputs:
    - violation + message
    """

    def __init__(
        self,
        *,
        audio_threshold: float = 0.35,
        min_violation_gap_sec: float = 2.5,
        look_away_grace_count: int = 4,
    ) -> None:
        self.audio_threshold = audio_threshold
        self.min_violation_gap_sec = min_violation_gap_sec
        self.look_away_grace_count = look_away_grace_count

        self._cv2 = None
        self._np = None
        self._face_cascade = None

        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore

            self._cv2 = cv2
            self._np = np
            self._face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        except Exception:
            self._cv2 = None
            self._np = None
            self._face_cascade = None

    def _cooldown_ok(self, session_state: Dict[str, Any], key: str) -> bool:
        now = time.time()
        last = float(session_state.get(f'last_{key}_ts', 0.0))
        if now - last < self.min_violation_gap_sec:
            return False
        session_state[f'last_{key}_ts'] = now
        return True

    def _decode_image(self, image_data_url: str):
        if not self._cv2 or not self._np:
            return None

        try:
            if ',' in image_data_url:
                image_data_url = image_data_url.split(',', 1)[1]
            raw = base64.b64decode(image_data_url)
            arr = self._np.frombuffer(raw, dtype=self._np.uint8)
            img = self._cv2.imdecode(arr, self._cv2.IMREAD_COLOR)
            return img
        except Exception:
            return None

    def analyze_tab_event(self, session_state: Dict[str, Any], event_name: str) -> ProctorResult:
        if not self._cooldown_ok(session_state, 'tab'):
            return ProctorResult(False)
        return ProctorResult(True, event_name)

    def analyze_audio(self, session_state: Dict[str, Any], audio_level: float) -> ProctorResult:
        if audio_level is None:
            return ProctorResult(False)

        try:
            lvl = float(audio_level)
        except Exception:
            return ProctorResult(False)

        if lvl < self.audio_threshold:
            session_state['noise_streak'] = 0
            return ProctorResult(False)

        # Require 2 consecutive loud samples to reduce false positives.
        streak = int(session_state.get('noise_streak', 0)) + 1
        session_state['noise_streak'] = streak
        if streak < 2:
            return ProctorResult(False)

        if not self._cooldown_ok(session_state, 'audio'):
            return ProctorResult(False)

        session_state['noise_streak'] = 0
        return ProctorResult(True, 'Background Noise / Talking detected')

    def analyze_frame(self, session_state: Dict[str, Any], image_data_url: Optional[str]) -> ProctorResult:
        # If client did not send a frame, do not flag by default.
        if not image_data_url:
            return ProctorResult(False)

        # Without CV deps, we cannot do face checks.
        if not self._cv2 or not self._np or not self._face_cascade:
            return ProctorResult(False)

        img = self._decode_image(image_data_url)
        if img is None:
            return ProctorResult(False)

        try:
            gray = self._cv2.cvtColor(img, self._cv2.COLOR_BGR2GRAY)
            faces = self._face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        except Exception:
            return ProctorResult(False)

        face_count = 0 if faces is None else len(faces)

        if face_count == 0:
            if not self._cooldown_ok(session_state, 'noface'):
                return ProctorResult(False)
            return ProctorResult(True, 'No Face Detected')

        if face_count >= 2:
            if not self._cooldown_ok(session_state, 'multiface'):
                return ProctorResult(False)
            return ProctorResult(True, 'Multiple Faces Detected')

        # Single-face: estimate "looking away" using bounding box center drift.
        (x, y, w, h) = faces[0]
        ih, iw = gray.shape[:2]
        cx = (x + (w / 2.0)) / float(iw)
        cy = (y + (h / 2.0)) / float(ih)

        # Center window: tolerate movement.
        centered = (0.25 <= cx <= 0.75) and (0.20 <= cy <= 0.80)
        if centered:
            session_state['look_away_count'] = 0
            return ProctorResult(False)

        look_away = int(session_state.get('look_away_count', 0)) + 1
        session_state['look_away_count'] = look_away

        if look_away < self.look_away_grace_count:
            return ProctorResult(False)

        if not self._cooldown_ok(session_state, 'lookaway'):
            return ProctorResult(False)

        session_state['look_away_count'] = 0
        return ProctorResult(True, 'Looking Away Frequently')

    def analyze(
        self,
        *,
        session_state: Dict[str, Any],
        image_data_url: Optional[str],
        audio_level: float,
        client_violation_type: Optional[str] = None,
    ) -> ProctorResult:
        if client_violation_type:
            if not self._cooldown_ok(session_state, 'client'):
                return ProctorResult(False)
            return ProctorResult(True, str(client_violation_type))

        video_res = self.analyze_frame(session_state, image_data_url)
        if video_res.violation:
            return video_res

        return self.analyze_audio(session_state, audio_level)
