document.addEventListener('DOMContentLoaded', () => {
    const editBtn = document.getElementById('editProfileBtn');
    const saveBtn = document.getElementById('saveProfileBtn');
    const modalEl = document.getElementById('editProfileModal');

    if (editBtn && modalEl && window.bootstrap) {
        editBtn.addEventListener('click', () => {
            const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();
        });
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            const payload = {
                name: (document.getElementById('editName')?.value || '').trim(),
                email: (document.getElementById('editEmail')?.value || '').trim(),
                mobile_number: (document.getElementById('editMobile')?.value || '').trim(),
                institution: (document.getElementById('editInstitution')?.value || '').trim(),
                course: (document.getElementById('editCourse')?.value || '').trim(),
                semester: (document.getElementById('editSemester')?.value || '').trim(),
                cgpa: (document.getElementById('editCgpa')?.value || '').trim(),
            };

            try {
                const res = await fetch('/api/profile/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (!res.ok || !data.success) {
                    throw new Error(data.message || 'Update failed');
                }

                window.location.reload();
            } catch (err) {
                console.error(err);
                alert(err.message || 'Failed to update profile');
            }
        });
    }
});
