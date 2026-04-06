// State
let isClockRunning = false;
let totalTimeSeconds = 0;
let taskTimeSeconds = 0;
let clockInterval = null;
let currentTimetableDate = new Date();

// Auth State
let authToken = localStorage.getItem('timeTrackerToken');
let currentUser = null;

// DOM Elements
const loginOverlay = document.getElementById('loginOverlay');
const loginError = document.getElementById('loginError');
const totalTimeDisplay = document.getElementById('totalTimeDisplay');
const taskTimeDisplay = document.getElementById('taskTimeDisplay');
const mainClockBtn = document.getElementById('mainClockBtn');
const toastContainer = document.getElementById('toastContainer');
const processesList = document.getElementById('processesList');
const adminEditList = document.getElementById('adminEditList');
const adminUserList = document.getElementById('adminUserList');
const parentProcessSelect = document.getElementById('parentProcessSelect');
const currentDateDisplay = document.getElementById('currentDateDisplay');
const footerUserLabel = document.getElementById('footerUserLabel');
const assignOverlay = document.getElementById('assignOverlay');
const assignUserSelect = document.getElementById('assignUserSelect');
const assignTaskLabel = document.getElementById('assignTaskLabel');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const sidebar = document.querySelector('.sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');

// Quick Add Elements
const quickAddTaskCard = document.getElementById('quickAddTaskCard');
const quickProcessSelect = document.getElementById('quickProcessSelect');
const quickTaskName = document.getElementById('quickTaskName');
const quickUserSelect = document.getElementById('quickUserSelect');
const btnQuickAddConfirm = document.getElementById('btnQuickAddConfirm');

let currentAssignTaskId = null;
let systemUsers = [];

// API Wrapper to include Token automatically
async function apiFetch(url, options = {}) {
    if (!options.headers) options.headers = {};
    options.headers['Authorization'] = `Bearer ${authToken}`;
    
    // Auto Content-Type unless FormData
    if (!(options.body instanceof FormData) && !options.headers['Content-Type']) {
        options.headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(url, options);
    if (res.status === 401) {
        logout();
        throw new Error("Unauthorized");
    }
    return res;
}

// Initial Auth Check
if (!authToken) {
    loginOverlay.classList.remove('hidden');
} else {
    loginOverlay.classList.add('hidden');
    appInit();
}

// Login Logic
document.getElementById('btnLogin').addEventListener('click', async () => {
    const user = document.getElementById('loginUsername').value;
    const pass = document.getElementById('loginPassword').value;
    if(!user || !pass) return;

    const formData = new FormData();
    formData.append('username', user); 
    formData.append('password', pass);

    try {
        const res = await fetch('/api/auth/token', {
            method: 'POST',
            body: formData
        });
        if (!res.ok) {
            const data = await res.json();
            loginError.innerText = data.detail || "Błąd logowania";
            loginError.style.display = 'block';
            return;
        }
        const data = await res.json();
        authToken = data.access_token;
        localStorage.setItem('timeTrackerToken', authToken);
        
        loginOverlay.classList.add('hidden');
        appInit();
        showToast("Zalogowano pomyślnie");
    } catch(e) {
        loginError.innerText = "Brak połączenia z serwerem";
        loginError.style.display = 'block';
    }
});

document.getElementById('btnLogout').addEventListener('click', () => logout());

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('timeTrackerToken');
    loginOverlay.classList.remove('hidden');
    if(isClockRunning) toggleClock();
}

// Start app data fetch after login
async function appInit() {
    try {
        const res = await apiFetch('/api/me');
        currentUser = await res.json();
        footerUserLabel.innerText = `Zalogowany jako: ${currentUser.username}`;
        
        // Initial population of selects
        fetchAdminData(); 
        fetchProcesses();
    } catch(e) {}
}

function formatTime(seconds) {
    const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
    const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${h}:${m}:${s}`;
}
function formatDate(date) { return date.toISOString().split('T')[0]; }

// Clock Logic
function toggleClock() {
    isClockRunning = !isClockRunning;
    if (isClockRunning) {
        mainClockBtn.classList.add('running');
        mainClockBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
        clockInterval = setInterval(() => {
            totalTimeSeconds++;
            taskTimeSeconds++;
            totalTimeDisplay.innerText = formatTime(totalTimeSeconds);
            taskTimeDisplay.innerText = formatTime(taskTimeSeconds);
        }, 1000);
    } else {
        mainClockBtn.classList.remove('running');
        mainClockBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
        clearInterval(clockInterval);
    }
}
mainClockBtn.addEventListener('click', toggleClock);

// View Navigation
document.querySelectorAll('.sidebar li[data-view]').forEach(item => {
    item.addEventListener('click', (e) => {
        document.querySelectorAll('.sidebar li').forEach(li => li.classList.remove('active'));
        e.currentTarget.classList.add('active');
        
        const viewName = e.currentTarget.getAttribute('data-view');
        document.querySelectorAll('.view-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`view-${viewName}`).classList.add('active');

        if(viewName === 'tasks') fetchProcesses();
        if(viewName === 'admin') fetchAdminData();
        if(viewName === 'timetable') renderTimetable();

        // Close sidebar on mobile after selecting a view
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('open');
            sidebarOverlay.classList.remove('active');
        }
    });
});

// Mobile Sidebar Toggles
if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        sidebarOverlay.classList.toggle('active');
    });
}

if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
    });
}

// Desktop Sidebar Collapse Toggle
const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
const appFooter = document.querySelector('.app-footer');

function updateFooterPosition() {
    if (window.innerWidth > 768 && appFooter) {
        if (sidebar.classList.contains('collapsed')) {
            appFooter.style.left = 'var(--sidebar-collapsed-width)';
        } else {
            appFooter.style.left = 'var(--sidebar-width)';
        }
    }
}

// Restore sidebar collapsed state from localStorage
if (localStorage.getItem('sidebarCollapsed') === 'true') {
    sidebar.classList.add('collapsed');
    updateFooterPosition();
}

if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
        updateFooterPosition();
    });
}

function showToast(msg) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerText = msg;
    toastContainer.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3000);
}

// API Fetching
async function fetchProcesses() {
    try {
        const res = await apiFetch('/api/processes');
        const data = await res.json();
        renderProcesses(data);
    } catch(e) {}
}

async function fetchAdminData() {
    try {
        // Fetch processes (get ALL for admin mode)
        let res = await apiFetch('/api/processes?all_data=true');
        let data = await res.json();
        
        const populateSelect = (select) => {
            select.innerHTML = '<option value="">Wybierz...</option>';
            data.forEach(p => { select.innerHTML += `<option value="${p.id}">${p.name}</option>`; });
        };
        
        populateSelect(parentProcessSelect);
        populateSelect(quickProcessSelect);

        renderAdminEditList(data);

        // Fetch users
        res = await apiFetch('/api/users');
        systemUsers = await res.json();
        
        quickUserSelect.innerHTML = '<option value="">Przypisz do...</option>';
        systemUsers.forEach(u => {
            quickUserSelect.innerHTML += `<option value="${u.id}">${u.username}</option>`;
        });

        renderAdminUserList(systemUsers);
    } catch(e) {}
}

// Render Functions
function renderProcesses(processes) {
    processesList.innerHTML = '';
    
    // Check if empty
    let hasTasks = false;
    processes.forEach(p => { if(p.subprocesses && p.subprocesses.length > 0) hasTasks = true; });
    if(!hasTasks) {
        processesList.innerHTML = '<p style="color:var(--text-secondary); text-align:center; padding: 20px;">Brak przypisanych tasków dla Ciebie w jakimkolwiek procesie.</p>';
        return;
    }

    processes.forEach(p => {
        if(!p.subprocesses || p.subprocesses.length === 0) return; // Ukryj puste procesy

        const item = document.createElement('div');
        item.className = 'process-item';
        
        const header = document.createElement('div');
        header.className = 'process-header';
        header.innerHTML = `<span><i class="fa-solid fa-folder"></i> ${p.name}</span> <i class="fa-solid fa-chevron-down"></i>`;
        header.onclick = () => item.classList.toggle('open');
        
        const subcontainer = document.createElement('div');
        subcontainer.className = 'subprocesses';
        
        p.subprocesses.forEach(sp => {
            const row = document.createElement('div');
            row.className = `subprocess-row ${sp.completed ? 'completed' : ''}`;
            
            // Build Time Details HTML
            let timeSums = {};
            let totalTaskTime = 0;
            sp.time_entries.forEach(e => {
                const uName = e.user ? e.user.username : 'Unknown';
                if(!timeSums[uName]) timeSums[uName] = 0;
                timeSums[uName] += e.time_allocated_seconds;
                totalTaskTime += e.time_allocated_seconds;
            });
            
            let timeDetailsHtml = '';
            Object.keys(timeSums).forEach(uname => {
                timeDetailsHtml += `<div class="time-detail-row"><span class="user-badge"><i class="fa-solid fa-user"></i> ${uname}</span><span>${formatTime(timeSums[uname])}</span></div>`;
            });
            if(Object.keys(timeSums).length === 0) {
                timeDetailsHtml = '<div style="color:var(--text-secondary); font-size:12px;">Brak zalogowanego czasu.</div>';
            }

            row.innerHTML = `
                <div class="sp-row-top">
                    <div class="sp-name"><b>[TaskID: ${sp.id}]</b> ${sp.name} <i class="fa-solid fa-clock-rotate-left details-toggler" style="margin-left:10px; color:var(--text-secondary); cursor:pointer;" title="Time Details" onclick="this.closest('.subprocess-row').querySelector('.time-details-container').classList.toggle('open')"></i></div>
                    <div class="sp-actions">
                        <button class="btn-icon" title="Dodaj/Zaproś Usera do Taska" onclick="openAssignModal(${sp.id}, '${sp.name}')"><i class="fa-solid fa-user-plus"></i></button>
                        <button class="btn-icon allocate" title="Alokuj Mój Czas" onclick="allocateTime(${sp.id}, '${sp.name}')"><i class="fa-regular fa-clock"></i></button>
                        <button class="btn-icon" title="Oznacz Zakończone" onclick="toggleComplete(${sp.id})"><i class="fa-solid ${sp.completed ? 'fa-rotate-left' : 'fa-check'}"></i></button>
                    </div>
                </div>
                <div class="time-details-container glass">
                    <div class="time-details-header">
                        <span>Raport Czasu Użytkowników</span>
                        <span>Suma: ${formatTime(totalTaskTime)}</span>
                    </div>
                    ${timeDetailsHtml}
                </div>
            `;
            subcontainer.appendChild(row);
        });
        
        item.appendChild(header);
        item.appendChild(subcontainer);
        processesList.appendChild(item);
    });
}

function renderAdminEditList(processes) {
    adminEditList.innerHTML = '';
    processes.forEach(p => {
        const item = document.createElement('div');
        item.className = 'process-item';
        const header = document.createElement('div');
        header.className = 'process-header';
        header.innerHTML = `
            <span><i class="fa-solid fa-folder"></i> ${p.name}</span> 
            <div class="sp-actions" onclick="event.stopPropagation()">
                <button class="btn-icon edit-btn" title="Edytuj Proces" onclick="editProcess(${p.id}, '${p.name}')"><i class="fa-solid fa-pen"></i></button>
                <button class="btn-icon delete-btn" title="Usuń Proces" onclick="deleteProcess(${p.id})"><i class="fa-solid fa-trash"></i></button>
                <i class="fa-solid fa-chevron-down" onclick="this.closest('.process-item').classList.toggle('open')" style="cursor:pointer; margin-left:10px;"></i>
            </div>
        `;
        const subcontainer = document.createElement('div');
        subcontainer.className = 'subprocesses';
        p.subprocesses.forEach(sp => {
            const row = document.createElement('div');
            row.className = `subprocess-row`;
            row.innerHTML = `
                <div class="sp-row-top">
                    <div class="sp-name"><b>[TaskID: ${sp.id}]</b> ${sp.name}</div>
                    <div class="sp-actions">
                        <button class="btn-icon edit-btn" onclick="editSubprocess(${sp.id}, '${sp.name}')"><i class="fa-solid fa-pen"></i></button>
                        <button class="btn-icon delete-btn" onclick="deleteSubprocess(${sp.id})"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>
            `;
            subcontainer.appendChild(row);
        });
        item.appendChild(header);
        item.appendChild(subcontainer);
        adminEditList.appendChild(item);
    });
}

function renderAdminUserList(users) {
    adminUserList.innerHTML = '';
    users.forEach(u => {
        const row = document.createElement('div');
        row.className = 'admin-user-row glass';
        row.style.marginBottom = "10px";
        row.innerHTML = `
            <div>
                <strong>${u.username}</strong> <br>
                <small style="color:var(--text-secondary)">${u.email}</small>
            </div>
            <div class="sp-actions">
                <button class="btn-icon edit-btn" title="Zmień hasło" onclick="editUserPassword(${u.id})"><i class="fa-solid fa-key"></i></button>
                <button class="btn-icon delete-btn" title="Usuń" onclick="deleteUser(${u.id}, '${u.username}')"><i class="fa-solid fa-trash"></i></button>
            </div>
        `;
        adminUserList.appendChild(row);
    });
}

// Core Actions
window.allocateTime = async (spId, spName) => {
    if(taskTimeSeconds === 0) return showToast("Brak czasu do alokacji (0s).");
    const timeToAllocate = taskTimeSeconds;
    try {
        await apiFetch(`/api/subprocesses/${spId}/allocate`, {
            method: 'POST',
            body: JSON.stringify({ time_allocated_seconds: timeToAllocate })
        });
        showToast(`Zalokowano ${formatTime(timeToAllocate)} na ${spName}`);
        taskTimeSeconds = 0; taskTimeDisplay.innerText = formatTime(taskTimeSeconds);
        fetchProcesses(); // Refresh times
    } catch(e) {}
};
window.toggleComplete = async (spId) => {
    try { await apiFetch(`/api/subprocesses/${spId}/toggle_complete`, { method: 'PATCH' }); fetchProcesses(); } catch(e) {}
};

// Modals Setup
window.openAssignModal = async (spId, spName) => {
    currentAssignTaskId = spId;
    assignTaskLabel.innerHTML = `Dla obszaru: <b>${spName}</b>`;
    assignOverlay.classList.remove('hidden');
    
    try {
        const res = await apiFetch('/api/users');
        const users = await res.json();
        assignUserSelect.innerHTML = '';
        users.forEach(u => {
            assignUserSelect.innerHTML += `<option value="${u.id}">${u.username}</option>`;
        });
    } catch(e) {}
};

document.getElementById('btnAssignCancel').addEventListener('click', () => { assignOverlay.classList.add('hidden'); });
document.getElementById('btnAssignConfirm').addEventListener('click', async () => {
    const u_id = assignUserSelect.value;
    if(!u_id || !currentAssignTaskId) return;
    try {
        await apiFetch(`/api/subprocesses/${currentAssignTaskId}/assign`, {
            method: 'POST',
            body: JSON.stringify({ user_id: parseInt(u_id) })
        });
        showToast("Przypisano poprawnie.");
        assignOverlay.classList.add('hidden');
        fetchProcesses();
    } catch(e) {
        showToast("Wystąpił błąd");
    }
});

// Admin Edit Actions
window.editProcess = async (id, oldName) => {
    const newName = prompt("Podaj nową nazwę Procesu:", oldName);
    if(newName && newName !== oldName) {
        await apiFetch(`/api/processes/${id}`, { method: 'PUT', body: JSON.stringify({ name: newName }) });
        showToast(`Zmieniono na ${newName}`); fetchAdminData();
    }
};
window.deleteProcess = async (id) => {
    if(confirm("Usunąć ten Proces wraz z zawartością?")) {
        await apiFetch(`/api/processes/${id}`, { method: 'DELETE' }); showToast("Usunięto."); fetchAdminData();
    }
};
window.editSubprocess = async (id, oldName) => {
    const newName = prompt("Podaj nową nazwę Zadania (Taska):", oldName);
    if(newName && newName !== oldName) {
        await apiFetch(`/api/subprocesses/${id}`, { method: 'PUT', body: JSON.stringify({ name: newName }) });
        showToast(`Zmieniono na ${newName}`); fetchAdminData();
    }
};
window.deleteSubprocess = async (id) => {
    if(confirm("Usunąć ten Task?")) {
        await apiFetch(`/api/subprocesses/${id}`, { method: 'DELETE' }); showToast("Usunięto."); fetchAdminData();
    }
};

// Admin Users Actions
document.getElementById('btnAddUser').addEventListener('click', async () => {
    const u = document.getElementById('newUsername').value;
    const e = document.getElementById('newUserEmail').value;
    const p = document.getElementById('newUserPass').value;
    if(!u || !p) return;
    try {
        await apiFetch('/api/users', { method: 'POST', body: JSON.stringify({ username: u, email: e, password: p }) });
        showToast(`Dodano usera: ${u}`);
        document.getElementById('newUsername').value=''; document.getElementById('newUserEmail').value=''; document.getElementById('newUserPass').value='';
        fetchAdminData();
    } catch(err) { showToast("Błąd przy dodawaniu usera."); }
});
window.editUserPassword = async (id) => {
    const p = prompt("Wpisz nowe hasło dla tego użytkownika:");
    if(p) {
        await apiFetch(`/api/users/${id}`, { method: 'PUT', body: JSON.stringify({ password: p }) });
        showToast("Hasło zmienione!"); fetchAdminData();
    }
};
window.deleteUser = async (id, name) => {
    if(confirm(`Usunąć trwale usera ${name}? Czasów nie usunie, ale user straci dostęp.`)) {
        await apiFetch(`/api/users/${id}`, { method: 'DELETE' }); showToast("Usunięto."); fetchAdminData();
    }
};

// Admin Add Objects
document.getElementById('btnAddProcess').addEventListener('click', async () => {
    const name = document.getElementById('newProcessName').value;
    if(!name) return;
    const res = await apiFetch('/api/processes', { method: 'POST', body: JSON.stringify({ name }) });
    const p = await res.json();
    document.getElementById('newProcessName').value = ''; showToast(`Dodano proces [ID: ${p.id}]`); fetchAdminData();
});
document.getElementById('btnAddSubprocess').addEventListener('click', async () => {
    const parentId = parentProcessSelect.value;
    const name = document.getElementById('newSubprocessName').value;
    if(!parentId || !name) return;
    const res = await apiFetch('/api/subprocesses', { method: 'POST', body: JSON.stringify({ name, process_id: parseInt(parentId) }) });
    const sp = await res.json();
    document.getElementById('newSubprocessName').value = ''; showToast(`Utworzono task [ID: ${sp.id}] z Twoim przypisaniem`); fetchAdminData();
});

// Quick Add Handler
btnQuickAddConfirm.addEventListener('click', async () => {
    const pId = quickProcessSelect.value;
    const name = quickTaskName.value;
    const uId = quickUserSelect.value;
    
    if(!pId || !name) return showToast("Wypełnij Proces i Nazwę!");
    
    try {
        const res = await apiFetch('/api/subprocesses', {
            method: 'POST',
            body: JSON.stringify({ 
                name: name, 
                process_id: parseInt(pId),
                user_id: uId ? parseInt(uId) : null
            })
        });
        const sp = await res.json();
        showToast(`Utworzono nowy Task [ID: ${sp.id}]`);
        quickTaskName.value = '';
        quickAddTaskCard.classList.add('hidden');
        fetchProcesses();
    } catch(e) {
        showToast("Błąd przy tworzeniu taska");
    }
});

// Reporting (Uses token in URL)
document.getElementById('btnExportReportTxt').addEventListener('click', () => { window.open(`/api/report/allcharges?token=${authToken}`, '_blank'); });
document.getElementById('btnExportReportCsv').addEventListener('click', () => { window.open(`/api/report/csv?token=${authToken}`, '_blank'); });

// Timetable Day Navigation
document.getElementById('btnPrevDay').addEventListener('click', () => { currentTimetableDate.setDate(currentTimetableDate.getDate() - 1); renderTimetable(); });
document.getElementById('btnNextDay').addEventListener('click', () => { currentTimetableDate.setDate(currentTimetableDate.getDate() + 1); renderTimetable(); });

async function renderTimetable() {
    if(!currentUser) return;

    const todayStr = formatDate(new Date());
    const currentStr = formatDate(currentTimetableDate);
    currentDateDisplay.innerText = currentStr === todayStr ? 'Dzisiaj' : currentStr;

    try {
        const res = await apiFetch('/api/processes');
        const processes = await res.json();
        const container = document.getElementById('calendarContainer');
        container.innerHTML = '';
        
        let maxTime = 1; let pTimes = {};
        processes.forEach(p => {
            pTimes[p.id] = { name: p.name, time: 0 };
            p.subprocesses.forEach(sp => {
                sp.time_entries.forEach(e => {
                    // FILTER OUT OTHER USERS' TIME ENTRIES IN TIMETABLE !!!
                    if (e.user_id !== currentUser.id) return;

                    if (e.start_time.split('T')[0] === currentStr) {
                        pTimes[p.id].time += e.time_allocated_seconds;
                    }
                });
            });
            if(pTimes[p.id].time > maxTime) maxTime = pTimes[p.id].time;
        });

        let hasEntries = false;
        Object.values(pTimes).forEach(item => {
            if(item.time > 0) hasEntries = true;
            const width = item.time === 0 ? 0 : Math.max(10, (item.time / maxTime) * 100);
            container.innerHTML += `
                <div class="tt-item" style="opacity: ${item.time === 0 ? '0.3' : '1'}">
                    <div class="tt-label">${item.name}</div>
                    <div class="tt-bar-wrapper">
                        <div class="tt-bar" style="width: ${width}%">${formatTime(item.time)}</div>
                    </div>
                </div>
            `;
        });
        if(!hasEntries) container.innerHTML += '<p style="text-align:center; color: var(--text-secondary); margin-top: 30px;">Brak Twoich logowań dla tego dnia.</p>';
    } catch(e) {}
}
