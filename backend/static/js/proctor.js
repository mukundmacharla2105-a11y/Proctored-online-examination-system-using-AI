(() => {
  const MAX_WARNINGS = 6;
  const FRAME_INTERVAL_MS = 2000;

  let socket;
  let isActive = false;

  let audioContext;
  let analyser;
  let dataArray;

  function getAudioLevel() {
    if (!analyser || !dataArray) return 0;
    analyser.getByteFrequencyData(dataArray);
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
    const avg = sum / dataArray.length;
    return avg / 255;
  }

  function emitViolation(type) {
    if (!isActive || !socket) return;
    socket.emit('process_frame', {
      image: null,
      audio_level: 0,
      violation_type: type
    });
  }

  function setupSecurityMonitors() {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) emitViolation('Tab Switch / Minimized');
    });

    window.addEventListener('blur', () => {
      emitViolation('Window Focus Lost (Alt+Tab)');
    });

    document.addEventListener('keydown', (e) => {
      if (
        e.key === 'F12' ||
        (e.ctrlKey && (e.key === 'c' || e.key === 'v' || e.key === 'x')) ||
        (e.altKey && e.key === 'Tab')
      ) {
        e.preventDefault();
        emitViolation('Restricted Key Pressed');
      }
    });
  }

  function captureAndSendFrame(video, canvas) {
    if (!isActive || !socket) return;

    if (!video || video.videoWidth === 0) return;

    const ctx = canvas.getContext('2d');
    canvas.width = 320;
    canvas.height = 240;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const imageData = canvas.toDataURL('image/jpeg', 0.4);
    const audioLevel = getAudioLevel();

    socket.emit('process_frame', {
      image: imageData,
      audio_level: audioLevel,
      violation_type: null
    });
  }

  async function start() {
    const video = document.getElementById('webcam');
    const canvas = document.getElementById('capture-canvas');

    if (!video || !canvas) return;

    socket = window.io ? window.io() : null;
    if (!socket) return;

    socket.on('warning_alert', (data) => {
      const remaining = MAX_WARNINGS - data.count;
      if (window.Swal) {
        Swal.fire({
          icon: 'warning',
          title: '⚠️ Violation Detected',
          html: `<b>${data.message}</b><br>Warnings: ${data.count}/${MAX_WARNINGS}<br>Exam will terminate in ${remaining} warnings!`,
          timer: 4000,
          toast: true,
          position: 'top-end',
          showConfirmButton: false,
          background: '#fff3cd',
          color: '#856404'
        });
      }
    });

    socket.on('exam_terminated', (data) => {
      isActive = false;
      if (window.Swal) {
        Swal.fire({
          icon: 'error',
          title: 'EXAM TERMINATED',
          text: data.reason,
          allowOutsideClick: false,
          confirmButtonText: 'Exit',
          confirmButtonColor: '#d33'
        }).then(() => {
          window.location.href = data.redirect || '/student_dashboard';
        });
      } else {
        window.location.href = data.redirect || '/student_dashboard';
      }
    });

    setupSecurityMonitors();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      video.srcObject = stream;
      isActive = true;

      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const mic = audioContext.createMediaStreamSource(stream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      mic.connect(analyser);
      dataArray = new Uint8Array(analyser.frequencyBinCount);

      setInterval(() => captureAndSendFrame(video, canvas), FRAME_INTERVAL_MS);
    } catch (err) {
      isActive = false;
      if (window.Swal) {
        Swal.fire({
          icon: 'error',
          title: 'Camera/Microphone Access Denied',
          text: 'You cannot take this exam without camera and microphone access.',
          allowOutsideClick: false
        }).then(() => {
          window.location.href = '/student_dashboard';
        });
      }
    }
  }

  document.addEventListener('DOMContentLoaded', start);
})();
