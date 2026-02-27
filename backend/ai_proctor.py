import cv2
import mediapipe as mp
import numpy as np
import base64

class AIProctor:
    def __init__(self):
        # Initialize MediaPipe Face Mesh
        # refine_landmarks=True gives us Iris landmarks for gaze tracking
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            min_detection_confidence=0.5, 
            min_tracking_confidence=0.5,
            refine_landmarks=True
        )

    def get_head_pose(self, shape, face_landmarks):
        """
        Calculates 3D Head Pose (Pitch, Yaw, Roll) using PnP.
        """
        h, w, _ = shape
        img_pts = []
        
        # Key landmarks for PnP (Nose tip, Chin, Left Eye, Right Eye, Mouth corners)
        # 1: Nose, 152: Chin, 33: Left Eye, 263: Right Eye, 61: Left Mouth, 291: Right Mouth
        ids = [1, 152, 33, 263, 61, 291]
        
        for idx in ids:
            lm = face_landmarks.landmark[idx]
            img_pts.append([lm.x * w, lm.y * h])
            
        img_pts = np.array(img_pts, dtype=np.float64)

        # 3D Model Points (Generic face model)
        model_pts = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left Mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ])

        # Camera Internals (Approximate)
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype="double")
        
        dist_coeffs = np.zeros((4, 1)) # Assuming no lens distortion

        # PnP Solve
        (success, rotation_vector, translation_vector) = cv2.solvePnP(
            model_pts, img_pts, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
        )

        # Convert Rotation Vector to Matrix to Euler Angles
        rmat, jac = cv2.Rodrigues(rotation_vector)
        angles, mtxR, mtxQ, Q, Qx, Qy, Qz = cv2.RQDecomp3x3(rmat)

        # Angles in degrees
        pitch = angles[0] * 360 # Up/Down
        yaw = angles[1] * 360   # Left/Right
        # roll = angles[2] * 360

        return pitch, yaw

    def process_frame(self, base64_image):
        """
        Analyzes a single frame for cheating behaviors.
        """
        try:
            # Decode image
            if ',' in base64_image:
                encoded_data = base64_image.split(',')[1]
            else:
                encoded_data = base64_image
                
            nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return False, None

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = frame.shape

            results = self.face_mesh.process(frame_rgb)

            # 1. No Face Detected
            if not results.multi_face_landmarks:
                return True, "No Face Detected! Please stay in frame."
            
            # 2. Multiple Faces
            if len(results.multi_face_landmarks) > 1:
                return True, "Multiple Faces Detected!"

            # 3. Head Pose Analysis (Looking Away)
            face_landmarks = results.multi_face_landmarks[0]
            pitch, yaw = self.get_head_pose(frame.shape, face_landmarks)

            # Thresholds (Tuned for typical webcams)
            if abs(yaw) > 25:
                direction = "Right" if yaw > 0 else "Left"
                return True, f"Looking away ({direction})"
            
            if pitch > 20: 
                return True, "Looking Down (Suspicious - Phone?)"
            
            if pitch < -25:
                return True, "Looking Up"

            # 4. Mouth Open Check (Speaking)
            top_lip = face_landmarks.landmark[13]
            bottom_lip = face_landmarks.landmark[14]
            
            # Calculate distance relative to face height
            face_top = face_landmarks.landmark[10].y
            face_bottom = face_landmarks.landmark[152].y
            face_height = face_bottom - face_top
            
            lip_dist = bottom_lip.y - top_lip.y
            
            if (lip_dist / face_height) > 0.08: # Threshold for open mouth
                return True, "Mouth Open / Talking detected"

            return False, None

        except Exception as e:
            print(f"AI Error: {e}")
            return False, None

    def analyze_audio(self, audio_level):
        """
        Checks if audio volume exceeds ambient threshold.
        """
        # Threshold adjusted. 0.25 is usually quite loud for normalized audio.
        THRESHOLD = 0.35 
        if audio_level > THRESHOLD:
            return True, "High Volume / Speech Detected"
        return False, None