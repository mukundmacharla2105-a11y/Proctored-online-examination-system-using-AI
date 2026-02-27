// Login Page Logic - Connected to Backend

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');

    const forgotPasswordLink = document.getElementById('forgotPasswordLink');
    const forgotPasswordPanel = document.getElementById('forgotPasswordPanel');
    const requestOtpBtn = document.getElementById('requestOtpBtn');
    const resetPasswordBtn = document.getElementById('resetPasswordBtn');
    const cancelForgotBtn = document.getElementById('cancelForgotBtn');

    const fpEmail = document.getElementById('fpEmail');
    const fpOtp = document.getElementById('fpOtp');
    const fpNewPassword = document.getElementById('fpNewPassword');

    if (forgotPasswordLink && forgotPasswordPanel) {
        forgotPasswordLink.addEventListener('click', (e) => {
            e.preventDefault();
            forgotPasswordPanel.classList.toggle('d-none');
        });
    }

    if (cancelForgotBtn && forgotPasswordPanel) {
        cancelForgotBtn.addEventListener('click', () => {
            forgotPasswordPanel.classList.add('d-none');
        });
    }

    if (requestOtpBtn && fpEmail) {
        requestOtpBtn.addEventListener('click', async () => {
            const email = fpEmail.value.trim();
            if (!email) {
                alert('Please enter your email.');
                return;
            }

            try {
                const response = await fetch('/forgot-password/request', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email })
                });
                const data = await response.json();
                alert(data.message || 'If the email exists, an OTP has been sent.');
            } catch (error) {
                console.error('OTP Request Error:', error);
                alert('Failed to send OTP. Please try again.');
            }
        });
    }

    if (resetPasswordBtn && fpEmail && fpOtp && fpNewPassword) {
        resetPasswordBtn.addEventListener('click', async () => {
            const email = fpEmail.value.trim();
            const otp = fpOtp.value.trim();
            const new_password = fpNewPassword.value.trim();

            if (!email || !otp || !new_password) {
                alert('Please fill email, OTP, and new password.');
                return;
            }

            try {
                const response = await fetch('/forgot-password/reset', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, otp, new_password })
                });
                const data = await response.json();

                if (response.ok && data.success) {
                    alert('Password updated successfully. You can now login.');
                    forgotPasswordPanel.classList.add('d-none');
                } else {
                    alert(data.message || 'Reset failed');
                }
            } catch (error) {
                console.error('Reset Error:', error);
                alert('Reset failed. Please try again.');
            }
        });
    }

    if (!loginForm) return;

    loginForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value.trim();

        if (!email || !password) {
            alert('Please fill in all fields.');
            return;
        }

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            let data;
            try {
                data = await response.json();
            } catch {
                throw new Error('Invalid server response (Non-JSON)');
            }

            if (response.ok && data.user) {
                localStorage.setItem('user', JSON.stringify(data.user));
                alert(`Login Successful! Welcome ${data.user.name}`);

                if (data.redirect) {
                    window.location.href = data.redirect;
                } else {
                    if (data.user.role === 'admin') {
                        window.location.href = '/admin_dashboard.html';
                    } else {
                        window.location.href = '/student_dashboard.html';
                    }
                }
            } else {
                alert(data.message || 'Invalid email or password');
            }
        } catch (error) {
            console.error('Login Error:', error);
            alert('Login failed. Please check backend connection.');
        }
    });
});