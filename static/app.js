// State
let isClockRunning = false;
let totalTimeSeconds = 0;
let taskTimeSeconds = 0;
let clockInterval = null;
let currentTimetableDate = new Date();

// Auth State
let authToken = localStorage.getItem('timeTrackerToken');
let currentUser = null;

// Hierarchical Data
let userTasks = [];
let masterHierarchy = []; // Processes and Subprocesses
let systemUsers = [];

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
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const sidebar = document.querySelector('.sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');

// Quick Add Elements
const quickAddTaskCard = document.getElementById('quickAddTaskCard');
const quickTaskNumericId = document.getElementById('quickTaskNumericId');
const quickTaskName = document.getElementById('quickTaskName');
const quickTaskProcessSelect = document.getElementById('quickTaskProcessSelect');
const quickUserSelect = document.getElementById('quickUserSelect');
const btnQuickAddConfirm = document.getElementById('btnQuickAddConfirm');

// Admin Elements
const btnCreateRealTask = document.getElementById('btnCreateRealTask');
const newTaskNumericId = document.getElementById('newTaskNumericId');
const newTaskName = document.getElementById('newTaskName');
const newTaskProcessSelect = document.getElementById('newTaskProcessSelect');

// API Wrapper to include Token automatically
async function apiFetch(url, options = {}) {
    if (!options.headers) options.headers = {};
    if (authToken) options.headers['Authorization'] = `Bearer ${authToken}`;
    if (!(options.body instanceof FormData) && !options.headers['Content-Type']) {
        options.headers['Content-Type'] = 'application/json';
    }
    const res = await fetch(url, options);
    if (res.status === 401) { logout(); throw new Error("Unauthorized"); }
    return res;
}

// Initial Auth Check
if (!authToken) {
    loginOverlay.classList.remove('hidden');
} else {
    loginOverlay.classList.add('hidden');
    appInit();
}

async function appInit() {
    try {
        const res = await apiFetch('/api/me');
        currentUser = await res.json();
        footerUserLabel.innerText = currentUser.username;
        fetchTasksAndHierarchy();
        renderTimetable();
        fetchAdminData();
    } catch(e) { logout(); }
}

function logout() {
    localStorage.removeItem('timeTrackerToken');
    window.location.reload();
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
        const res = await fetch('/api/auth/token', { method: 'POST', body: formData });
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

// Main Functional Logic
async function fetchTasksAndHierarchy() {
    try {
        const [tRes, hRes] = await Promise.all([
            apiFetch('/api/tasks'),
            apiFetch('/api/processes')
        ]);
        userTasks = await tRes.json();
        masterHierarchy = await hRes.json();
        renderTasksHierarchy();
    } catch(e) {}
}

function renderTasksHierarchy() {
    processesList.innerHTML = '';
    if (userTasks.length === 0) {
        processesList.innerHTML = '<p style="text-align:center; color:var(--text-secondary); margin-top:20px;">Brak przypisanych do Ciebie zadań.</p>';
        return;
    }
    const tree = document.createElement('div');
    tree.className = 'task-tree';
    userTasks.forEach(task => {
        const taskProcess = masterHierarchy.find(p => p.id === task.process_id);
        
        const taskEl = document.createElement('div');
        taskEl.className = 'task-item';
        taskEl.innerHTML = `
            <div class="task-header" onclick="this.parentElement.classList.toggle('expanded')">
                <div class="task-info">
                    <span class="task-badge">${task.numeric_id}</span>
                    <span class="task-name">${task.name}</span>
                </div>
                <i class="fa-solid ${task.completed ? 'fa-check-circle' : 'fa-chevron-down'}" ${task.completed ? 'style="color:var(--accent-green)"' : ''}></i>
            </div>
            <div class="task-content">
                <div style="font-size:12px; margin-bottom:10px; color:var(--text-secondary);">Kategorie prac przypisane do tego projektu:</div>
                <div class="processes-container">
                    ${taskProcess ? `
                        <div class="process-group">
                            <div class="process-header"><i class="fa-solid fa-folder-open"></i> ${taskProcess.name}</div>
                            <div class="subprocess-list">
                                ${taskProcess.subprocesses.map(sp => `
                                    <div class="subprocess-row">
                                        <span class="subprocess-name" style="${sp.completed ? 'text-decoration: line-through; opacity: 0.6;' : ''}">${sp.name}</span>
                                        <div class="subprocess-actions">
                                            <button class="icon-btn clock-btn" onclick="allocateAndCheck(${task.id}, ${sp.id}, '${task.name} / ${sp.name}')" title="Allocate time">
                                                <i class="fa-solid fa-clock"></i>
                                            </button>
                                            <button class="icon-btn ${sp.completed ? 'success-active' : ''}" onclick="toggleSubprocess(${sp.id})" title="${sp.completed ? 'Mark as incomplete' : 'Mark as completed'}">
                                                <i class="fa-solid fa-circle-check"></i>
                                            </button>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : '<p style="font-size:11px; color:var(--accent-red);">Błąd: Brak przypisanego procesu do tego zadania.</p>'}
                </div>
            </div>
        `;
        tree.appendChild(taskEl);
    });
    processesList.appendChild(tree);
}

// completion toggle
async function toggleSubprocess(id) {
    try {
        await apiFetch(`/api/subprocesses/${id}/toggle_complete`, { method: 'PATCH' });
        fetchTasksAndHierarchy();
        showToast("Status zaktualizowany");
    } catch(e) { showToast("Błąd aktualizacji statusu"); }
}

// allocation from clock
async function allocateAndCheck(taskId, subprocessId, label) {
    if (taskTimeSeconds <= 0) return showToast("Brak czasu na zegarze zadaniowym (Task Time)!");
    
    // Capture current time to allocate
    const timeToAllocate = taskTimeSeconds;
    
    if(!confirm(`Czy chcesz zaalokować ${formatTime(timeToAllocate)} na: ${label}?`)) return;

    try {
        // Reset local task timer immediately to prevent drift if confirmed
        taskTimeSeconds = 0;
        taskTimeDisplay.innerText = formatTime(taskTimeSeconds);

        await apiFetch('/api/allocate', {
            method: 'POST',
            body: JSON.stringify({
                task_id: taskId,
                subprocess_id: subprocessId,
                time_allocated_seconds: timeToAllocate
            })
        });
        showToast("Czas zalokowany pomyślnie!");
        renderTimetable();
    } catch(e) { 
        showToast("Błąd podczas alokacji czasu."); 
    }
}

// Clock logic
function toggleClock() {
    if (!userTasks.length) return showToast("Musisz mieć przypisane zadania, by mierzyć czas.");
    isClockRunning = !isClockRunning;
    if (isClockRunning) {
        mainClockBtn.classList.add('running');
        mainClockBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
        clockInterval = setInterval(() => {
            totalTimeSeconds++; taskTimeSeconds++;
            totalTimeDisplay.innerText = formatTime(totalTimeSeconds);
            taskTimeDisplay.innerText = formatTime(taskTimeSeconds);
        }, 1000);
    } else {
        mainClockBtn.classList.remove('running');
        mainClockBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
        clearInterval(clockInterval);
        showToast("Zegar zatrzymany. Użyj przycisku 'Rejestruj' przy wybranym zadaniu, aby zalokować ten czas.");
    }
}
mainClockBtn.addEventListener('click', toggleClock);

// Admin Logic
async function fetchAdminData() {
    try {
        const [pRes, tRes, uRes] = await Promise.all([
            apiFetch('/api/processes'),
            apiFetch('/api/tasks?all_data=true'),
            apiFetch('/api/users')
        ]);
        const processes = await pRes.json();
        const tasks = await tRes.json();
        systemUsers = await uRes.json();
        
        parentProcessSelect.innerHTML = '<option value="">Wybierz Proces...</option>';
        quickTaskProcessSelect.innerHTML = '<option value="">Wybierz Proces...</option>';
        newTaskProcessSelect.innerHTML = '<option value="">Wybierz Proces...</option>';
        
        processes.forEach(p => { 
            const opt = `<option value="${p.id}">${p.name}</option>`;
            parentProcessSelect.innerHTML += opt;
            quickTaskProcessSelect.innerHTML += opt;
            newTaskProcessSelect.innerHTML += opt;
        });
        
        quickUserSelect.innerHTML = '<option value="">Przypisz...</option>';
        systemUsers.forEach(u => { quickUserSelect.innerHTML += `<option value="${u.id}">${u.username}</option>`; });

        renderAdminEditList(processes, tasks);
        renderAdminUserList();
    } catch(e) {}
}

function renderAdminEditList(processes, tasks) {
    adminEditList.innerHTML = '';
    processes.forEach(p => {
        const pEl = document.createElement('div');
        pEl.className = 'admin-edit-item';
        pEl.style.marginBottom = '15px';
        pEl.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.05); padding:10px; border-radius:8px;">
                <strong><i class="fa-solid fa-folder"></i> [PROCES] ${p.name}</strong>
                <div>
                    <button class="btn sm" onclick="editProcess(${p.id}, '${p.name}')"><i class="fa-solid fa-pen"></i></button>
                    <button class="btn sm danger" onclick="deleteProcess(${p.id})"><i class="fa-solid fa-trash"></i></button>
                </div>
            </div>
            <div style="padding-left: 20px; margin-top:5px;">
                ${p.subprocesses.map(sp => `
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:5px 0; border-bottom:1px solid #333;">
                        <span style="font-size:13px;"><i class="fa-solid fa-tag"></i> [KAT] ${sp.name}</span>
                        <div>
                            <button class="btn sm" onclick="editSubprocess(${sp.id}, '${sp.name}')"><i class="fa-solid fa-pen"></i></button>
                            <button class="btn sm danger" onclick="deleteSubprocess(${sp.id})"><i class="fa-solid fa-trash"></i></button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        adminEditList.appendChild(pEl);
    });

    adminEditList.innerHTML += '<hr style="margin:20px 0; border:0; border-top: 1px solid var(--border-color);">';
    
    tasks.forEach(t => {
        const tEl = document.createElement('div');
        tEl.style.marginBottom = '10px';
        tEl.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(0,180,255,0.05); padding:10px; border-radius:8px;">
                <strong><i class="fa-solid fa-ticket"></i> [TICKET] ${t.numeric_id}: ${t.name}</strong>
                <div>
                    <button class="btn sm" onclick="assignUserToTask(${t.id}, '${t.name}')" title="Przypisz Usera"><i class="fa-solid fa-user-plus"></i></button>
                    <button class="btn sm ${t.completed ? 'success' : ''}" onclick="toggleTask(${t.id})" title="Status"><i class="fa-solid fa-check"></i></button>
                    <button class="btn sm danger" onclick="deleteTask(${t.id})"><i class="fa-solid fa-trash"></i></button>
                </div>
            </div>
            <div style="padding-left: 20px; font-size: 11px; color:var(--text-secondary); margin-top:3px;">
                Przypisani: ${t.users.map(u => u.username).join(', ') || 'brak'}
            </div>
        `;
        adminEditList.appendChild(tEl);
    });
}

function renderAdminUserList() {
    adminUserList.innerHTML = '';
    systemUsers.forEach(u => {
        adminUserList.innerHTML += `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #333;">
                <span style="font-size:13px;">${u.username} (ID: ${u.id})</span>
                <div>
                    <button class="btn sm" onclick="editUserPassword(${u.id})"><i class="fa-solid fa-key"></i></button>
                    <button class="btn sm danger" onclick="deleteUser(${u.id}, '${u.username}')"><i class="fa-solid fa-trash"></i></button>
                </div>
            </div>
        `;
    });
}

// Global Actions
window.editProcess = async (id, oldName) => {
    const newName = prompt("Nowa nazwa procesu:", oldName);
    if(newName && newName !== oldName) { await apiFetch(`/api/processes/${id}`, { method: 'PUT', body: JSON.stringify({ name: newName }) }); fetchAdminData(); }
};
window.deleteProcess = async (id) => {
    if(confirm("Usunąć proces?")) { await apiFetch(`/api/processes/${id}`, { method: 'DELETE' }); fetchAdminData(); }
};
window.editSubprocess = async (id, oldName) => {
    const newName = prompt("Nowa nazwa kategorii:", oldName);
    if(newName && newName !== oldName) { await apiFetch(`/api/subprocesses/${id}`, { method: 'PUT', body: JSON.stringify({ name: newName }) }); fetchAdminData(); }
};
window.deleteSubprocess = async (id) => {
    if(confirm("Usunąć kategorię?")) { await apiFetch(`/api/subprocesses/${id}`, { method: 'DELETE' }); fetchAdminData(); }
};
window.deleteTask = async (id) => {
    if(confirm("Usunąć ten ticket?")) { await apiFetch(`/api/tasks/${id}`, { method: 'DELETE' }); fetchAdminData(); }
};
window.toggleTask = async (id) => {
    await apiFetch(`/api/tasks/${id}/toggle_complete`, { method: 'PATCH' }); fetchAdminData(); fetchTasksAndHierarchy();
};
window.assignUserToTask = async (taskId, taskName) => {
    const userId = prompt(`Wpisz ID użytkownika do przypisania do: ${taskName}\n(ID widoczne na liście obok nazwy)`);
    if(userId) { await apiFetch(`/api/tasks/${taskId}/assign`, { method: 'POST', body: JSON.stringify({ user_id: parseInt(userId) }) }); showToast("Przypisano!"); fetchAdminData(); }
};
window.editUserPassword = async (id) => {
    const p = prompt("Nowe hasło dla użytkownika:");
    if(p) { await apiFetch(`/api/users/${id}`, { method: 'PUT', body: JSON.stringify({ password: p }) }); showToast("Hasło zmienione!"); }
};
window.deleteUser = async (id, name) => {
    if(confirm(`Usunąć trwale usera ${name}?`)) { await apiFetch(`/api/users/${id}`, { method: 'DELETE' }); fetchAdminData(); }
};

// Event Listeners for Buttons
document.getElementById('btnLogout').addEventListener('click', logout);
document.getElementById('btnAddProcess').addEventListener('click', async () => {
    const name = document.getElementById('newProcessName').value;
    if(!name) return;
    await apiFetch('/api/processes', { method: 'POST', body: JSON.stringify({ name }) });
    document.getElementById('newProcessName').value = ''; 
    fetchAdminData(); 
    fetchTasksAndHierarchy(); // Refresh hierarchy for Tasks view
    showToast("Dodano proces");
});
document.getElementById('btnAddSubprocess').addEventListener('click', async () => {
    const pId = parentProcessSelect.value;
    const name = document.getElementById('newSubprocessName').value;
    if(!pId || !name) return showToast("Wybierz proces i podaj nazwę!");
    await apiFetch('/api/subprocesses', { method: 'POST', body: JSON.stringify({ name, process_id: parseInt(pId) }) });
    document.getElementById('newSubprocessName').value = ''; 
    fetchAdminData(); 
    fetchTasksAndHierarchy(); // Refresh hierarchy for Tasks view
    showToast("Dodano kategorię");
});
document.getElementById('btnCreateRealTask').addEventListener('click', async () => {
    const nid = newTaskNumericId.value;
    const name = newTaskName.value;
    const pId = newTaskProcessSelect.value;
    if(!nid || !name || !pId) return showToast("Wypełnij ID, Nazwę i wybierz Proces!");
    await apiFetch('/api/tasks', { method: 'POST', body: JSON.stringify({ numeric_id: parseInt(nid), name, process_id: parseInt(pId) }) });
    newTaskNumericId.value = ''; newTaskName.value = ''; 
    fetchAdminData(); 
    fetchTasksAndHierarchy(); // Refresh Tasks view
    showToast("Utworzono ticket!");
});
document.getElementById('btnAddUser').addEventListener('click', async () => {
    const u = document.getElementById('newUsername').value;
    const e = document.getElementById('newUserEmail').value;
    const p = document.getElementById('newUserPass').value;
    if(!u || !p) return;
    try {
        await apiFetch('/api/users', { method: 'POST', body: JSON.stringify({ username: u, email: e, password: p }) });
        document.getElementById('newUsername').value=''; document.getElementById('newUserEmail').value=''; document.getElementById('newUserPass').value='';
        fetchAdminData(); showToast("Dodano użytkownika");
    } catch(err) { showToast("Błąd przy dodawaniu."); }
});
btnQuickAddConfirm.addEventListener('click', async () => {
    const nid = quickTaskNumericId.value;
    const name = quickTaskName.value;
    const pId = quickTaskProcessSelect.value;
    const uid = quickUserSelect.value;
    if(!nid || !name || !pId) return showToast("Wypełnij ID, Nazwę i wybierz Proces!");
    try {
        await apiFetch('/api/tasks', { method: 'POST', body: JSON.stringify({ 
            numeric_id: parseInt(nid), 
            name, 
            process_id: parseInt(pId),
            user_ids: uid ? [parseInt(uid)] : [] 
        }) });
        quickTaskNumericId.value = ''; quickTaskName.value = ''; quickAddTaskCard.classList.add('hidden');
        fetchTasksAndHierarchy(); showToast("Utworzono ticket!");
    } catch(e) {}
});

// View Navigation
document.querySelectorAll('.sidebar li[data-view]').forEach(item => {
    item.addEventListener('click', (e) => {
        document.querySelectorAll('.sidebar li').forEach(li => li.classList.remove('active'));
        e.currentTarget.classList.add('active');
        const viewName = e.currentTarget.getAttribute('data-view');
        document.querySelectorAll('.view-section').forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${viewName}`).classList.add('active');
        if (window.innerWidth <= 768) { sidebar.classList.add('collapsed'); sidebarOverlay.classList.remove('active'); }
    });
});

// Reporting
document.getElementById('btnExportReportTxt').addEventListener('click', () => { window.open(`/api/report/allcharges?token=${authToken}`, '_blank'); });
document.getElementById('btnExportReportCsv').addEventListener('click', () => { window.open(`/api/report/csv?token=${authToken}`, '_blank'); });

// Timetable
document.getElementById('prevDate').addEventListener('click', () => { currentTimetableDate.setDate(currentTimetableDate.getDate() - 1); renderTimetable(); });
document.getElementById('nextDate').addEventListener('click', () => { currentTimetableDate.setDate(currentTimetableDate.getDate() + 1); renderTimetable(); });

async function renderTimetable() {
    if(!currentUser) return;
    const currentStr = formatDate(currentTimetableDate);
    document.getElementById('currentDateDisplay').innerText = (currentStr === formatDate(new Date())) ? 'Dzisiaj' : currentStr;
    try {
        const res = await apiFetch('/api/tasks?all_data=true');
        const tasks = await res.json();
        const container = document.getElementById('timelineList');
        container.innerHTML = '';
        let hasEntries = false;
        tasks.forEach(t => {
            let taskTotal = 0;
            t.time_entries.forEach(e => { if (e.user_id === currentUser.id && e.start_time.split('T')[0] === currentStr) taskTotal += e.time_allocated_seconds; });
            if (taskTotal > 0) {
                hasEntries = true;
                container.innerHTML += `<div class="timeline-item"><div class="timeline-info"><h4>${t.numeric_id}: ${t.name}</h4><div class="timeline-meta">Suma zalogowana dzisiaj</div></div><div class="timeline-time">${formatTime(taskTotal)}</div></div>`;
            }
        });
        if(!hasEntries) container.innerHTML = '<p style="text-align:center; color:var(--text-secondary); margin-top:20px;">Brak wpisów dla tego dnia.</p>';
    } catch(e) {}
}

// Sidebar Logic
const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
if (localStorage.getItem('sidebarCollapsed') === 'true') sidebar.classList.add('collapsed');
sidebarToggleBtn.addEventListener('click', () => { sidebar.classList.toggle('collapsed'); localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed')); });

// Utils
function formatTime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}/${m.toString().padStart(2, '0')}/${s.toString().padStart(2, '0')}`;
}
function formatDate(date) {
    const y = date.getFullYear();
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const d = date.getDate().toString().padStart(2, '0');
    return `${y}-${m}-${d}`;
}
function showToast(msg) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerText = msg;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
