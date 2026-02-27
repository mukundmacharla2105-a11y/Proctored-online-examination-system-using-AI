console.log("Exam JS Loaded");

let examMeta = null;
let questions = [];
let questionIdByIndex = [];

let currentIdx = 0;
let answers = {};
const socket = io();

document.addEventListener('DOMContentLoaded', () => {
    const examId = document.body ? document.body.getAttribute('data-exam-id') : null;
    loadExam(examId);
});

async function loadExam(examId) {
    try {
        const res = await fetch(`/api/exams/${encodeURIComponent(examId)}`);
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.message || 'Failed to load exam');
        }

        examMeta = data.exam;
        questions = (data.questions || []).map((q) => ({
            id: q.id,
            q: q.question_text,
            opts: q.options
        }));
        questionIdByIndex = questions.map((q) => q.id);

        document.getElementById('examTitle').innerText = examMeta.name || 'Exam';
        const totalEl = document.getElementById('totalQDisplay');
        if (totalEl) totalEl.innerText = String(questions.length);

        renderPalette();
        loadQuestion(0);

        const duration = parseInt(examMeta.duration_minutes || 30, 10);
        startTimer(duration * 60);
    } catch (err) {
        console.error(err);
        if (window.Swal) {
            Swal.fire({
                icon: 'error',
                title: 'Failed to load exam',
                text: 'Please try again from the dashboard.'
            }).then(() => {
                window.location.href = '/student_dashboard';
            });
        } else {
            alert('Failed to load exam');
            window.location.href = '/student_dashboard';
        }
    }
}

// --- Standard Exam Logic (Questions, Timer) ---

function loadQuestion(idx) {
    currentIdx = idx;
    const qData = questions[idx];
    if (!qData) return;
    document.getElementById('questionText').innerText = `Q${idx+1}: ${qData.q}`;
    document.getElementById('currentQDisplay').innerText = idx + 1;
    const container = document.getElementById('optionsContainer');
    container.innerHTML = '';
    qData.opts.forEach((opt, i) => {
        const qId = qData.id;
        const isChecked = answers[qId] === i ? 'checked' : '';
        container.innerHTML += `
            <label class="option-label">
                <input type="radio" name="opt" value="${i}" ${isChecked} onchange="saveAnswer(${qId}, ${i})">
                ${opt}
            </label>
        `;
    });
    updatePalette();
}

function saveAnswer(questionId, optIdx) {
    answers[String(questionId)] = optIdx;
    updatePalette();
}

function renderPalette() {
    const p = document.getElementById('palette');
    p.innerHTML = '';
    questions.forEach((_, i) => {
        p.innerHTML += `<button id="p-${i}" onclick="loadQuestion(${i})" class="palette-btn">${i+1}</button>`;
    });
}

function updatePalette() {
    questions.forEach((_, i) => {
        const btn = document.getElementById(`p-${i}`);
        if (!btn) return;
        btn.className = 'palette-btn';
        if (i === currentIdx) {
            btn.classList.add('active');
        } else {
            const qId = questionIdByIndex[i];
            if (qId !== undefined && answers[String(qId)] !== undefined) {
                btn.classList.add('answered');
            }
        }
    });
}

function nextQ() {
    if(currentIdx < questions.length - 1) loadQuestion(currentIdx + 1);
}

function prevQ() {
    if(currentIdx > 0) loadQuestion(currentIdx - 1);
}

function submitExam() {
    Swal.fire({
        title: 'Submit Exam?',
        text: "Are you sure you want to finish?",
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Yes, Submit'
    }).then((result) => {
        if (!result.isConfirmed) return;

        submitToServer();
    })
}

async function submitToServer() {
    try {
        const res = await fetch('/api/exam/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.message || 'Submission failed');
        }

        socket.emit('submit_exam');

        if (window.Swal) {
            Swal.fire({
                icon: 'success',
                title: 'Submitted',
                text: `Score: ${Math.round(data.percentage)}% (${data.result_status})`,
                confirmButtonText: 'Back to Dashboard'
            }).then(() => {
                window.location.href = '/student_dashboard';
            });
        } else {
            window.location.href = '/student_dashboard';
        }
    } catch (err) {
        console.error(err);
        if (window.Swal) {
            Swal.fire({
                icon: 'error',
                title: 'Submission failed',
                text: 'Please try again.'
            });
        } else {
            alert('Submission failed');
        }
    }
}

function startTimer(duration) {
    let timer = duration, minutes, seconds;
    const display = document.getElementById('timer');
    const interval = setInterval(() => {
        minutes = parseInt(timer / 60, 10);
        seconds = parseInt(timer % 60, 10);
        display.textContent = (minutes < 10 ? "0" + minutes : minutes) + ":" + (seconds < 10 ? "0" + seconds : seconds);
        if (--timer < 0) {
            clearInterval(interval);
            submitExam();
        }
    }, 1000);
}