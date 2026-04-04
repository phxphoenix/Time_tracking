// State
let isClockRunning = false;
let totalTimeSeconds = 0;
let taskTimeSeconds = 0;
let clockInterval = null;

let currentTimetableDate = new Date();

// DOM Elements
const totalTimeDisplay = document.getElementById('totalTimeDisplay');
const taskTimeDisplay = document.getElementById('taskTimeDisplay');
const mainClockBtn = document.getElementById('mainClockBtn');
const toastContainer = document.getElementById('toastContainer');
const processesList = document.getElementById('processesList');
const adminEditList = document.getElementById('adminEditList');
const parentProcessSelect = document.getElementById('parentProcessSelect');
const currentDateDisplay = document.getElementById('currentDateDisplay');

// Format Time hh:mm:ss
function formatTime(seconds) {
    const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
    const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${h}:${m}:${s}`;
}

// Format Date YYYY-MM-DD
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

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
document.querySelectorAll('.sidebar li').forEach(item => {
    item.addEventListener('click', (e) => {
        document.querySelectorAll('.sidebar li').forEach(li => li.classList.remove('active'));
        e.currentTarget.classList.add('active');
        
        const viewName = e.currentTarget.getAttribute('data-view');
        document.querySelectorAll('.view-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(`view-${viewName}`).classList.add('active');

        if(viewName === 'tasks') fetchProcesses();
        if(viewName === 'admin') fetchProcessesForAdmin();
        if(viewName === 'timetable') renderTimetable();
    });
});

// Utilities
function showToast(msg) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerText = msg;
    toastContainer.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3000);
}

// API Calls
async function fetchProcesses() {
    const res = await fetch('/api/processes');
    const data = await res.json();
    renderProcesses(data);
}

async function fetchProcessesForAdmin() {
    const res = await fetch('/api/processes');
    const data = await res.json();
    
    // Update Select
    parentProcessSelect.innerHTML = '<option value="">Wybierz proces docelowy...</option>';
    data.forEach(p => {
        parentProcessSelect.innerHTML += `<option value="${p.id}">${p.name}</option>`;
    });
    
    // Render Edit List
    renderAdminEditList(data);
}

// Render Functions
function renderProcesses(processes) {
    processesList.innerHTML = '';
    processes.forEach(p => {
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
            row.innerHTML = `
                <div class="sp-name">- ${sp.name}</div>
                <div class="sp-actions">
                    <button class="btn-icon allocate" title="Allocate Time" onclick="allocateTime(${sp.id}, '${sp.name}')"><i class="fa-regular fa-clock"></i></button>
                    <button class="btn-icon" title="Complete / Restore" onclick="toggleComplete(${sp.id})"><i class="fa-solid ${sp.completed ? 'fa-rotate-left' : 'fa-check'}"></i></button>
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
                <div class="sp-name">- ${sp.name}</div>
                <div class="sp-actions">
                    <button class="btn-icon edit-btn" title="Edytuj" onclick="editSubprocess(${sp.id}, '${sp.name}')"><i class="fa-solid fa-pen"></i></button>
                    <button class="btn-icon delete-btn" title="Usuń" onclick="deleteSubprocess(${sp.id})"><i class="fa-solid fa-trash"></i></button>
                </div>
            `;
            subcontainer.appendChild(row);
        });
        
        item.appendChild(header);
        item.appendChild(subcontainer);
        adminEditList.appendChild(item);
    });
}

// Core Actions
window.allocateTime = async (spId, spName) => {
    if(taskTimeSeconds === 0) {
        showToast("Zegar zadania wynosi 0. Brak czasu do alokacji.");
        return;
    }
    const timeToAllocate = taskTimeSeconds;
    try {
        await fetch(`/api/subprocesses/${spId}/allocate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ time_allocated_seconds: timeToAllocate })
        });
        showToast(`Zalokowano ${formatTime(timeToAllocate)} na ${spName}`);
        taskTimeSeconds = 0;
        taskTimeDisplay.innerText = formatTime(taskTimeSeconds);
    } catch(e) {
        showToast("Błąd podczas alokacji czasu.");
    }
};

window.toggleComplete = async (spId) => {
    await fetch(`/api/subprocesses/${spId}/toggle_complete`, { method: 'PATCH' });
    fetchProcesses();
};

// Admin Edit Actions (PUT / DELETE)
window.editProcess = async (id, oldName) => {
    const newName = prompt("Podaj nową nazwę Procesu:", oldName);
    if(newName && newName !== oldName) {
        await fetch(`/api/processes/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });
        showToast(`Zmieniono nazwę na ${newName}`);
        fetchProcessesForAdmin();
    }
};

window.deleteProcess = async (id) => {
    if(confirm("Czy na pewno chcesz usunąć ten Proces wraz z całą jego zawartością?")) {
        await fetch(`/api/processes/${id}`, { method: 'DELETE' });
        showToast("Proces usunięty");
        fetchProcessesForAdmin();
    }
};

window.editSubprocess = async (id, oldName) => {
    const newName = prompt("Podaj nową nazwę Subprocesu:", oldName);
    if(newName && newName !== oldName) {
        await fetch(`/api/subprocesses/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });
        showToast(`Zmieniono nazwę subprocesu na ${newName}`);
        fetchProcessesForAdmin();
    }
};

window.deleteSubprocess = async (id) => {
    if(confirm("Czy na pewno usunąć ten Subproces?")) {
        await fetch(`/api/subprocesses/${id}`, { method: 'DELETE' });
        showToast("Subproces usunięty");
        fetchProcessesForAdmin();
    }
};

// Admin Add Actions
document.getElementById('btnAddProcess').addEventListener('click', async () => {
    const name = document.getElementById('newProcessName').value;
    if(!name) return;
    await fetch('/api/processes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });
    document.getElementById('newProcessName').value = '';
    showToast(`Dodano proces: ${name}`);
    fetchProcessesForAdmin();
});

document.getElementById('btnAddSubprocess').addEventListener('click', async () => {
    const parentId = parentProcessSelect.value;
    const name = document.getElementById('newSubprocessName').value;
    if(!parentId || !name) return;
    await fetch('/api/subprocesses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, process_id: parseInt(parentId) })
    });
    document.getElementById('newSubprocessName').value = '';
    showToast(`Dodano subproces: ${name}`);
    fetchProcessesForAdmin();
});

// Reporting
document.getElementById('btnExportReportTxt').addEventListener('click', () => {
    window.open('/api/report/allcharges', '_blank');
});
document.getElementById('btnExportReportCsv').addEventListener('click', () => {
    window.open('/api/report/csv', '_blank');
});

// Timetable Day Navigation
document.getElementById('btnPrevDay').addEventListener('click', () => {
    currentTimetableDate.setDate(currentTimetableDate.getDate() - 1);
    renderTimetable();
});

document.getElementById('btnNextDay').addEventListener('click', () => {
    currentTimetableDate.setDate(currentTimetableDate.getDate() + 1);
    renderTimetable();
});

// Timetable Render (Grupuje po wybranym dniu)
async function renderTimetable() {
    // Ustaw display 
    const todayStr = formatDate(new Date());
    const currentStr = formatDate(currentTimetableDate);
    currentDateDisplay.innerText = currentStr === todayStr ? 'Dzisiaj' : currentStr;

    const res = await fetch('/api/processes');
    const processes = await res.json();
    const container = document.getElementById('calendarContainer');
    container.innerHTML = '';
    
    let maxTime = 1;
    let pTimes = {};
    
    processes.forEach(p => {
        pTimes[p.id] = { name: p.name, time: 0 };
        p.subprocesses.forEach(sp => {
            sp.time_entries.forEach(e => {
                // Sprawdź czy wpis należy do aktualnie przeglądanego dnia (porównując YYYY-MM-DD po UTC)
                // Zakładamy, że serwer zwraca e.start_time jako string "YYYY-MM-DDTHH:mm:SS"
                const entryDate = e.start_time.split('T')[0];
                if (entryDate === currentStr) {
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
    
    if(!hasEntries) {
        container.innerHTML += '<p style="text-align:center; color: var(--text-secondary); margin-top: 30px;">Brak wpisów dla tego dnia.</p>';
    }
}

// Initial fetch
fetchProcesses();
