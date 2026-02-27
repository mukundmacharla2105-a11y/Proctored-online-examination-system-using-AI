let _allSessions = [];

function _renderSessions(sessions) {
    const tbody = document.getElementById('sessionTable');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!sessions || sessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">No active or recent sessions found.</td></tr>';
        return;
    }

    sessions.forEach((s) => {
        let statusBadge = '<span class="badge bg-secondary">' + (s.status || '--') + '</span>';
        const statusText = (s.status || '').toLowerCase();
        if (statusText.includes('completed')) statusBadge = '<span class="badge bg-success">Completed</span>';
        else if (statusText.includes('terminated')) statusBadge = '<span class="badge bg-danger">Terminated</span>';
        else if (statusText.includes('active')) statusBadge = '<span class="badge bg-warning text-dark">Active</span>';

        const scoreText = (s.percentage === null || s.percentage === undefined) ? '--' : `${Math.round(s.percentage)}%`;
        const violationText = s.violation_summary ? ` (${s.violation_summary})` : '';

        const viewBtn = s.report_pdf_url
            ? `<a class="btn btn-sm btn-outline-secondary me-1" href="${s.report_pdf_url}" target="_blank">View</a>`
            : `<button class="btn btn-sm btn-outline-secondary me-1" disabled>View</button>`;
        const csvBtn = s.report_csv_url
            ? `<a class="btn btn-sm btn-outline-secondary" href="${s.report_csv_url}">CSV</a>`
            : `<button class="btn btn-sm btn-outline-secondary" disabled>CSV</button>`;

        tbody.innerHTML += `
            <tr>
                <td>${(s.student_name || '--')}${violationText}</td>
                <td>${(s.exam_name || '--')}</td>
                <td>${statusBadge}</td>
                <td>${scoreText}</td>
                <td>${viewBtn}${csvBtn}</td>
            </tr>
        `;
    });
}

function _applySearchFilter() {
    const q = (document.getElementById('sessionSearch')?.value || '').trim().toLowerCase();
    if (!q) {
        _renderSessions(_allSessions);
        return;
    }
    const filtered = _allSessions.filter((s) => {
        const sn = (s.student_name || '').toLowerCase();
        const en = (s.exam_name || '').toLowerCase();
        return sn.includes(q) || en.includes(q);
    });
    _renderSessions(filtered);
}

async function updateDashboard() {
    try {
        // Fetch Stats
        const statsRes = await fetch('/admin/api/stats');
        if (!statsRes.ok) throw new Error('Failed to fetch stats');
        const stats = await statsRes.json();

        const totalEl = document.getElementById('totalStudents');
        if (totalEl) totalEl.innerText = stats.total_students ?? 0;
        const createdEl = document.getElementById('createdExams');
        if (createdEl) createdEl.innerText = stats.created_exams ?? 0;
        const pendingEl = document.getElementById('pendingResults');
        if (pendingEl) pendingEl.innerText = stats.pending_results ?? 0;

        // Fetch Table
        const sessionsRes = await fetch('/admin/api/sessions');
        if (!sessionsRes.ok) throw new Error('Failed to fetch sessions');
        const sessions = await sessionsRes.json();

        _allSessions = Array.isArray(sessions) ? sessions : [];
        _applySearchFilter();
    } catch (error) {
        console.error("Dashboard update error:", error);
    }
}

// Update every 5 seconds
setInterval(updateDashboard, 5000);

// Initial call
document.addEventListener('DOMContentLoaded', () => {
    const search = document.getElementById('sessionSearch');
    if (search) {
        search.addEventListener('input', () => {
            _applySearchFilter();
        });
    }
    updateDashboard();
});