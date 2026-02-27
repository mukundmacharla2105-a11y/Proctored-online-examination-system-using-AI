// Student Dashboard Logic

document.addEventListener('DOMContentLoaded', () => {
    // Highlight active link (simple mock)
    const links = document.querySelectorAll('.nav-link');
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            // e.preventDefault(); // Un-comment if you want to stop navigation
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });

    const examButtons = document.querySelectorAll('.start-exam-btn');
    examButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const examId = btn.getAttribute('data-exam-id');
            const examName = btn.getAttribute('data-exam-name') || '';
            if (!examId) return;
            startExam(examId, examName);
        });
    });
});

function startExam(examId, examName) {
    const nameText = examName ? `"${examName}"` : 'this exam';
    if (confirm(`Are you ready to start ${nameText}? \n\nEnsure you have a stable internet connection and your webcam is ready.`)) {
        window.location.href = `/exam?exam_id=${encodeURIComponent(examId)}`;
    }
}