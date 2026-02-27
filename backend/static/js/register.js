// Register Page Logic - Connected to Backend (Fixed Version)

document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('registerForm');
    const passwordInput = document.getElementById('regPassword');
    const confirmInput = document.getElementById('regConfirmPassword');
    const errorMsg = document.getElementById('passwordError');

    const startCameraBtn = document.getElementById('startCameraBtn');
    const captureFaceBtn = document.getElementById('captureFaceBtn');
    const video = document.getElementById('regWebcam');
    const canvas = document.getElementById('regCaptureCanvas');
    const faceImageData = document.getElementById('faceImageData');

    let regStream = null;

    if (startCameraBtn && video) {
        startCameraBtn.addEventListener('click', async () => {
            try {
                regStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                video.srcObject = regStream;
            } catch (e) {
                alert('Camera access denied. Webcam capture is required.');
            }
        });
    }

    if (captureFaceBtn && video && canvas && faceImageData) {
        captureFaceBtn.addEventListener('click', () => {
            if (!video.srcObject || video.videoWidth === 0) {
                alert('Start the camera first.');
                return;
            }
            const ctx = canvas.getContext('2d');
            canvas.width = 320;
            canvas.height = 240;
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            faceImageData.value = canvas.toDataURL('image/jpeg', 0.8);
            alert('Photo captured successfully.');
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            // FIX: Use 'name' attribute selectors for reliability
            // FIX: Add .trim() to avoid accidental spaces
            const first_name = document.querySelector('input[name="first_name"]').value.trim();
            const last_name = document.querySelector('input[name="last_name"]').value.trim();
            const email = document.querySelector('input[name="email"]').value.trim();
            const password = passwordInput.value.trim(); // Trimmed
            const confirm = confirmInput.value.trim();   // Trimmed

            // Reset error states
            errorMsg.classList.add('d-none');
            passwordInput.classList.remove('is-invalid');
            confirmInput.classList.remove('is-invalid');

            // Client-side Validation
            if (password !== confirm) {
                errorMsg.classList.remove('d-none');
                passwordInput.classList.add('is-invalid');
                confirmInput.classList.add('is-invalid');
                return;
            }

            if (password.length < 6) {
                alert('Password must be at least 6 characters long.');
                return;
            }

            // API Call to Backend (multipart)
            try {
                const formData = new FormData(registerForm);
                const response = await fetch('/register', {
                    method: 'POST',
                    body: formData
                });

                if (response.redirected) {
                    window.location.href = response.url;
                    return;
                }

                // If backend returns JSON in some cases
                let data = null;
                try { data = await response.json(); } catch {}

                if (response.ok) {
                    alert('Registration Successful! Please Login.');
                    window.location.href = '/login';
                } else {
                    alert((data && data.message) || 'Registration failed');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Server error. Is the backend running?');
            }
        });
    }
});