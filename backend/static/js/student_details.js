// Fetch and Display Students from Backend

document.addEventListener('DOMContentLoaded', async () => {
    const tableBody = document.getElementById('studentsTableBody');

    let _allStudents = [];
    let _filteredStudents = [];
    let _page = 1;
    const _pageSize = 8;

    function _initials(name) {
        const safe = (name || '').trim();
        if (!safe) return 'U';
        return safe.split(' ').filter(Boolean).slice(0, 2).map(p => p[0]).join('').toUpperCase();
    }

    function _avatarColorClass(seedText) {
        const colors = ['bg-primary', 'bg-warning', 'bg-info', 'bg-danger', 'bg-success'];
        const s = (seedText || 'x');
        let acc = 0;
        for (let i = 0; i < s.length; i++) acc += s.charCodeAt(i);
        return colors[acc % colors.length];
    }

    function _renderTable() {
        tableBody.innerHTML = '';
        if (!_filteredStudents || _filteredStudents.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4" class="text-center">No students found.</td></tr>';
            return;
        }

        const totalPages = Math.max(1, Math.ceil(_filteredStudents.length / _pageSize));
        if (_page > totalPages) _page = totalPages;
        if (_page < 1) _page = 1;

        const start = (_page - 1) * _pageSize;
        const items = _filteredStudents.slice(start, start + _pageSize);

        items.forEach((student) => {
            const initials = _initials(student.name);
            const color = _avatarColorClass(student.email || student.name);
            const studentIdText = student.student_uid || (`STU-${student.id}`);
            const mobile = student.mobile_number || '';

            const row = `
                <tr>
                    <td class="ps-4">
                        <div class="d-flex align-items-center">
                            <div class="avatar-circle ${color} text-white me-3">${initials}</div>
                            <div>
                                <div class="fw-bold">${student.name || '--'}</div>
                                <small class="text-muted">ID: ${studentIdText}</small>
                            </div>
                        </div>
                    </td>
                    <td>${student.email || ''}</td>
                    <td>${mobile}</td>
                    <td class="text-end pe-4">
                        <button class="btn btn-sm btn-light border text-secondary me-1 view-student-btn" data-student-id="${student.id}" title="View"><i class="fa-solid fa-eye"></i></button>
                        <button class="btn btn-sm btn-light border text-danger delete-student-btn" data-student-id="${student.id}" title="Delete"><i class="fa-solid fa-trash"></i></button>
                    </td>
                </tr>
            `;
            tableBody.insertAdjacentHTML('beforeend', row);
        });

        _wireRowActions();
        _updatePagination();
    }

    function _updatePagination() {
        const prev = document.getElementById('studentsPrev');
        const next = document.getElementById('studentsNext');
        const totalPages = Math.max(1, Math.ceil((_filteredStudents.length || 0) / _pageSize));
        if (prev) prev.parentElement.classList.toggle('disabled', _page <= 1);
        if (next) next.parentElement.classList.toggle('disabled', _page >= totalPages);
    }

    function _applySearch() {
        const q = (document.getElementById('studentSearch')?.value || '').trim().toLowerCase();
        if (!q) {
            _filteredStudents = _allStudents.slice();
        } else {
            _filteredStudents = _allStudents.filter((s) => (s.name || '').toLowerCase().includes(q));
        }
        _page = 1;
        _renderTable();
    }

    async function _openStudentView(studentId) {
        try {
            const res = await fetch(`/admin/api/users/${encodeURIComponent(studentId)}`);
            const data = await res.json();
            if (!res.ok || !data.success) throw new Error(data.message || 'Failed to load student');

            document.getElementById('svName').innerText = data.user.name || '--';
            document.getElementById('svStudentId').innerText = data.user.student_uid || `STU-${data.user.id}`;
            document.getElementById('svEmail').innerText = data.user.email || '--';
            document.getElementById('svMobile').innerText = data.user.mobile_number || '--';
            document.getElementById('svInstitution').innerText = data.user.institution || '--';
            document.getElementById('svDob').innerText = data.user.date_of_birth || '--';

            const idProof = document.getElementById('svIdProof');
            if (idProof) {
                if (data.user.id_proof_url) {
                    idProof.href = data.user.id_proof_url;
                    idProof.classList.remove('disabled');
                    idProof.innerText = 'View';
                } else {
                    idProof.href = '#';
                    idProof.innerText = '--';
                }
            }

            const face = document.getElementById('svFace');
            if (face) {
                if (data.user.face_url) {
                    face.href = data.user.face_url;
                    face.innerText = 'View';
                } else {
                    face.href = '#';
                    face.innerText = '--';
                }
            }

            const hist = document.getElementById('svHistoryBody');
            if (hist) {
                hist.innerHTML = '';
                const rows = data.history || [];
                if (!rows.length) {
                    hist.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No exam history.</td></tr>';
                } else {
                    rows.forEach((r) => {
                        const score = (r.percentage === null || r.percentage === undefined) ? '--' : `${Math.round(r.percentage)}%`;
                        hist.innerHTML += `
                            <tr>
                                <td>${r.exam_name || '--'}</td>
                                <td>${r.date || ''}</td>
                                <td>${r.status || ''}</td>
                                <td>${score}</td>
                            </tr>
                        `;
                    });
                }
            }

            const modalEl = document.getElementById('studentViewModal');
            if (modalEl && window.bootstrap) {
                const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
            }
        } catch (err) {
            console.error(err);
            alert(err.message || 'Failed to load student details');
        }
    }

    async function _deleteStudent(studentId) {
        if (!confirm('Are you sure you want to delete this student? This action cannot be undone.')) return;
        try {
            const res = await fetch(`/admin/api/users/${encodeURIComponent(studentId)}`, { method: 'DELETE' });
            const data = await res.json();
            if (!res.ok || !data.success) throw new Error(data.message || 'Delete failed');
            _allStudents = _allStudents.filter((s) => String(s.id) !== String(studentId));
            _applySearch();
        } catch (err) {
            console.error(err);
            alert(err.message || 'Failed to delete student');
        }
    }

    function _wireRowActions() {
        document.querySelectorAll('.view-student-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-student-id');
                if (id) _openStudentView(id);
            });
        });
        document.querySelectorAll('.delete-student-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-student-id');
                if (id) _deleteStudent(id);
            });
        });
    }

    async function _fetchStudents() {
        try {
            const response = await fetch('/admin/users');
            if (!response.ok) throw new Error('Failed to fetch data');
            const students = await response.json();
            _allStudents = Array.isArray(students) ? students : [];
            _applySearch();
        } catch (error) {
            console.error('Error loading students:', error);
            tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Error loading data. Ensure backend is running.</td></tr>';
        }
    }

    const searchInput = document.getElementById('studentSearch');
    const searchBtn = document.getElementById('studentSearchBtn');
    if (searchInput) searchInput.addEventListener('input', _applySearch);
    if (searchBtn) searchBtn.addEventListener('click', _applySearch);

    const prev = document.getElementById('studentsPrev');
    const next = document.getElementById('studentsNext');
    if (prev) {
        prev.addEventListener('click', (e) => {
            e.preventDefault();
            if (_page > 1) {
                _page -= 1;
                _renderTable();
            }
        });
    }
    if (next) {
        next.addEventListener('click', (e) => {
            e.preventDefault();
            const totalPages = Math.max(1, Math.ceil((_filteredStudents.length || 0) / _pageSize));
            if (_page < totalPages) {
                _page += 1;
                _renderTable();
            }
        });
    }

    await _fetchStudents();
});