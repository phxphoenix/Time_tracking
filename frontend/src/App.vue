<template>
  <div>
    <!-- Login Overlay -->
    <div v-if="!authToken" class="modal-overlay">
      <div class="modal-box glass" style="text-align: center;">
        <h2 style="margin-bottom: 10px;"><i class="fa-solid fa-clock" style="color: var(--accent-blue);"></i> TimeTracker <span style="color: var(--accent-blue);">Pro</span></h2>
        <p style="color: var(--text-secondary); font-size: 13.5px; margin-bottom: 22px;">
          Zaloguj się, aby rejestrować czas pracy na procesach i zadaniach
        </p>
        <div v-if="loginError" style="color: var(--accent-red); background: rgba(239,68,68,0.12); padding: 10px; border-radius: 8px; margin-bottom: 14px; font-size: 13px;">
          {{ loginError }}
        </div>
        <form @submit.prevent="handleLogin" style="display: flex; flex-direction: column; gap: 12px;">
          <input v-model="loginForm.username" type="text" placeholder="Nazwa użytkownika lub e-mail" required autocomplete="username" />
          <input v-model="loginForm.password" type="password" placeholder="Hasło" required autocomplete="current-password" />
          <button type="submit" class="btn primary" style="width: 100%; padding: 12px; margin-top: 6px;" :disabled="loginLoading">
            <i class="fa-solid fa-right-to-bracket"></i> {{ loginLoading ? 'Logowanie...' : 'Wejdź do aplikacji' }}
          </button>
        </form>
      </div>
    </div>

    <!-- Topbar -->
    <header class="topbar">
      <div style="display: flex; align-items: center; gap: 12px;">
        <button class="mobile-menu-btn" @click="mobileMenuOpen = !mobileMenuOpen">
          <i class="fa-solid fa-bars"></i>
        </button>
        <div class="logo">
          <div>TimeTracker <span>Pro</span></div>
          <span class="logo-badge">v2.0 Vue</span>
        </div>
      </div>

      <div class="timers-container">
        <div class="timer-box total-time">
          <span class="label">
            Total Time
            <button v-if="displayTotalSeconds > 0" class="timer-reset-mini" title="Zeruj Total Time" @click="resetTotalTimer">
              <i class="fa-solid fa-rotate-left"></i>
            </button>
          </span>
          <span class="time">{{ formatTime(displayTotalSeconds) }}</span>
        </div>

        <div class="timer-box task-time">
          <span class="label">
            Task Time
            <button v-if="displayTaskSeconds > 0" class="timer-reset-mini" title="Zeruj Task Time" @click="resetTaskTimer">
              <i class="fa-solid fa-rotate-left"></i>
            </button>
          </span>
          <span class="time">{{ formatTime(displayTaskSeconds) }}</span>
        </div>

        <button
          class="clock-btn"
          :class="{ running: timerState.isRunning }"
          :title="timerState.isRunning ? 'Zatrzymaj zegar (Pauza)' : 'Uruchom zegar'"
          @click="toggleClock"
        >
          <i class="fa-solid" :class="timerState.isRunning ? 'fa-pause' : 'fa-play'"></i>
        </button>
      </div>
    </header>

    <div class="main-layout">
      <!-- Sidebar -->
      <nav class="sidebar" :class="{ collapsed: sidebarCollapsed, 'mobile-open': mobileMenuOpen }">
        <ul>
          <li :class="{ active: activeView === 'tasks' }" @click="switchView('tasks')">
            <i class="fa-solid fa-list-check"></i>
            <span class="menu-text">Zadania (Tickets)</span>
          </li>
          <li :class="{ active: activeView === 'timetable' }" @click="switchView('timetable')">
            <i class="fa-solid fa-calendar-day"></i>
            <span class="menu-text">Mój Grafik</span>
          </li>
          <li :class="{ active: activeView === 'reporting' }" @click="switchView('reporting')">
            <i class="fa-solid fa-chart-pie"></i>
            <span class="menu-text">Raporty</span>
          </li>
          <li :class="{ active: activeView === 'admin' }" @click="switchView('admin')">
            <i class="fa-solid fa-sliders"></i>
            <span class="menu-text">Konfiguracja</span>
          </li>
          <li style="margin-top: auto; color: var(--accent-red);" @click="logout">
            <i class="fa-solid fa-arrow-right-from-bracket"></i>
            <span class="menu-text">Wyloguj</span>
          </li>
        </ul>
        <button class="sidebar-toggle-btn" title="Zwiń/Rozwiń panel boczny" @click="toggleSidebar">
          <i class="fa-solid fa-angles-left"></i>
        </button>
      </nav>

      <div class="sidebar-overlay" :class="{ active: mobileMenuOpen }" @click="mobileMenuOpen = false"></div>

      <!-- Main Content -->
      <main class="content-area">
        <!-- ==================== VIEW 1: TASKS ==================== -->
        <section v-if="activeView === 'tasks'">
          <div class="view-header-row">
            <div>
              <h2>Lista Zadań (Work Tickets)</h2>
              <p style="color: var(--text-secondary); font-size: 13.5px; margin-top: 4px;">
                Rozwiń wybrany Ticket, aby alokować czas z zegara <strong>Task Time</strong> na skonfigurowane podkategorie procesu.
              </p>
            </div>
            <button class="btn primary" @click="showQuickAdd = !showQuickAdd">
              <i class="fa-solid" :class="showQuickAdd ? 'fa-chevron-up' : 'fa-bolt'"></i>
              {{ showQuickAdd ? 'Ukryj formularz' : 'Nowy Ticket' }}
            </button>
          </div>

          <!-- Quick Add Ticket Card -->
          <div v-if="showQuickAdd" class="admin-card glass" style="margin-bottom: 24px; border-left: 4px solid var(--accent-blue);">
            <h3 style="margin-bottom: 12px;"><i class="fa-solid fa-plus-circle" style="color: var(--accent-blue);"></i> Szybkie Utworzenie Zadania (Ticket)</h3>
            <form class="input-group" style="flex-wrap: wrap;" @submit.prevent="handleQuickCreateTask">
              <input v-model.number="quickTaskForm.numeric_id" type="number" placeholder="Ticket ID (np. 1050)" style="width: 150px;" required />
              <input v-model="quickTaskForm.name" type="text" placeholder="Nazwa zadania / opis..." style="flex: 2; min-width: 220px;" required />
              <select v-model.number="quickTaskForm.process_id" style="flex: 1; min-width: 170px;" required>
                <option value="" disabled>Wybierz Proces...</option>
                <option v-for="p in processes" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
              <select v-model.number="quickTaskForm.user_id" style="flex: 1; min-width: 150px;">
                <option :value="null">Przypisz: Ja ({{ currentUser?.username }})</option>
                <option v-for="u in users" :key="u.id" :value="u.id">{{ u.username }}</option>
              </select>
              <button type="submit" class="btn success"><i class="fa-solid fa-check"></i> Utwórz</button>
            </form>
          </div>

          <!-- Filter & Search Toolbar -->
          <div class="toolbar-row">
            <div class="filter-tabs">
              <button class="filter-tab" :class="{ active: taskFilter === 'active' }" @click="taskFilter = 'active'">
                Aktywne ({{ activeTasksCount }})
              </button>
              <button class="filter-tab" :class="{ active: taskFilter === 'completed' }" @click="taskFilter = 'completed'">
                Ukończone ({{ completedTasksCount }})
              </button>
              <button class="filter-tab" :class="{ active: taskFilter === 'all' }" @click="taskFilter = 'all'">
                Wszystkie ({{ userTasks.length }})
              </button>
            </div>

            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
              <select v-model="taskProcessFilter" style="min-width: 170px;">
                <option value="">Wszystkie procesy</option>
                <option v-for="p in processes" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
              <div class="search-input-wrap">
                <i class="fa-solid fa-magnifying-glass"></i>
                <input v-model="taskSearch" type="text" placeholder="Szukaj po ID lub nazwie..." />
              </div>
            </div>
          </div>

          <!-- Tasks Hierarchy List -->
          <div v-if="filteredTasks.length === 0" class="admin-card glass" style="text-align: center; padding: 45px 20px; color: var(--text-secondary);">
            <i class="fa-solid fa-folder-open" style="font-size: 36px; margin-bottom: 12px; opacity: 0.5;"></i>
            <p>Brak zadań spełniających wybrane kryteria.</p>
          </div>

          <div v-else class="task-tree">
            <div
              v-for="task in filteredTasks"
              :key="task.id"
              class="task-item"
              :class="{ 'task-completed': task.completed }"
            >
              <div class="task-header" @click="toggleTaskExpand(task.id)">
                <div class="task-info">
                  <span class="task-badge">#{{ task.numeric_id }}</span>
                  <span class="task-name" :style="task.completed ? 'text-decoration: line-through; color: var(--text-secondary);' : ''">
                    {{ task.name }}
                  </span>
                  <span v-if="getProcessById(task.process_id)" class="process-pill">
                    <i class="fa-solid fa-diagram-project"></i> {{ getProcessById(task.process_id).name }}
                  </span>
                  <span v-for="u in task.users" :key="u.id" class="user-pill">
                    <i class="fa-solid fa-user" style="font-size: 9px;"></i> {{ u.username }}
                  </span>
                </div>

                <div class="task-header-right">
                  <span class="task-total-Chip" title="Łączny zarejestrowany czas na tym zadaniu">
                    <i class="fa-regular fa-clock"></i> {{ formatTime(getTaskTotalSeconds(task)) }}
                  </span>
                  <button
                    class="icon-btn"
                    :class="{ 'success-active': task.completed }"
                    :title="task.completed ? 'Oznacz Ticket jako aktywny' : 'Oznacz cały Ticket jako ukończony'"
                    @click.stop="toggleTaskComplete(task)"
                  >
                    <i class="fa-solid fa-flag-checkered"></i>
                  </button>
                  <i
                    class="fa-solid fa-chevron-down"
                    :style="{
                      transition: 'transform 0.2s',
                      transform: isTaskExpanded(task.id) ? 'rotate(180deg)' : 'rotate(0deg)',
                      color: 'var(--text-secondary)'
                    }"
                  ></i>
                </div>
              </div>

              <!-- Expanded Subprocesses -->
              <div v-if="isTaskExpanded(task.id)" class="task-content">
                <template v-if="getProcessById(task.process_id)">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.6px;">
                      Etapy procesu: <strong style="color: var(--text-primary);">{{ getProcessById(task.process_id).name }}</strong>
                    </span>
                    <span style="font-size: 12px; color: var(--text-secondary);">
                      Kliknij <i class="fa-solid fa-clock" style="color: var(--accent-blue);"></i> aby pobrać czas z licznika <strong>Task Time ({{ formatTime(displayTaskSeconds) }})</strong>
                    </span>
                  </div>

                  <div v-if="getProcessById(task.process_id).subprocesses.length === 0" style="color: var(--text-secondary); font-size: 13px; padding: 10px 0;">
                    Ten proces nie ma jeszcze zdefiniowanych subprocesów. Dodaj je w zakładce <strong>Konfiguracja</strong>.
                  </div>

                  <div v-else class="subprocess-list">
                    <div
                      v-for="sp in getProcessById(task.process_id).subprocesses"
                      :key="sp.id"
                      class="subprocess-row"
                    >
                      <div class="subprocess-left">
                        <span
                          class="subprocess-name"
                          :class="{ done: isSubprocessCompletedInTask(task, sp.id) }"
                        >
                          {{ sp.name }}
                        </span>
                        <span
                          v-if="getSubprocessSecondsInTask(task, sp.id) > 0"
                          class="sp-logged-badge"
                          title="Suma czasu zaalokowanego na ten etap w tym zadaniu"
                        >
                          <i class="fa-solid fa-stopwatch"></i> {{ formatTime(getSubprocessSecondsInTask(task, sp.id)) }}
                        </span>
                      </div>

                      <div class="subprocess-actions">
                        <button
                          class="icon-btn allocate-btn"
                          title="Zaalokuj bieżący Task Time na ten subproces (bez zatrzymywania zegara)"
                          @click="allocateFromTimer(task, sp)"
                        >
                          <i class="fa-solid fa-clock"></i>
                        </button>
                        <button
                          class="icon-btn"
                          title="Ręcznie dodaj czas do tego subprocesu"
                          @click="openManualAllocateModal(task, sp)"
                        >
                          <i class="fa-solid fa-plus"></i>
                        </button>
                        <button
                          class="icon-btn"
                          :class="{ 'success-active': isSubprocessCompletedInTask(task, sp.id) }"
                          :title="isSubprocessCompletedInTask(task, sp.id) ? 'Cofnij ukończenie etapu' : 'Oznacz etap jako ukończony w tym zadaniu'"
                          @click="toggleTaskSubprocess(task, sp.id)"
                        >
                          <i class="fa-solid fa-circle-check"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                </template>
                <div v-else style="color: var(--accent-red); font-size: 13px;">
                  Brak przypisanego procesu do tego zadania. Edytuj zadanie w zakładce Konfiguracja.
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- ==================== VIEW 2: TIMETABLE ==================== -->
        <section v-if="activeView === 'timetable'">
          <div class="view-header-row">
            <div>
              <h2>Mój Grafik Dzienny</h2>
              <p style="color: var(--text-secondary); font-size: 13.5px; margin-top: 4px;">
                Podsumowanie zarejestrowanego czasu oraz szczegółowa oś czasu z wybranego dnia.
              </p>
            </div>

            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-secondary); cursor: pointer; margin-right: 8px;">
                <input v-model="timetableAllUsers" type="checkbox" @change="fetchTimetableEntries" />
                Pokaż cały zespół
              </label>
              <button class="btn sm" @click="shiftTimetableDate(-1)"><i class="fa-solid fa-chevron-left"></i></button>
              <input v-model="timetableDateStr" type="date" style="width: 155px;" @change="fetchTimetableEntries" />
              <button class="btn sm" @click="setTimetableToday">Dzisiaj</button>
              <button class="btn sm" @click="shiftTimetableDate(1)"><i class="fa-solid fa-chevron-right"></i></button>
            </div>
          </div>

          <!-- Daily Summary Stats -->
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">Łączny czas w dniu ({{ timetableDateStr }})</div>
              <div class="stat-value" style="color: var(--accent-green);">{{ formatTime(timetableTotalSeconds) }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Liczba alokacji (wpisów)</div>
              <div class="stat-value">{{ timetableEntries.length }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Aktywne Tickety w tym dniu</div>
              <div class="stat-value" style="color: var(--accent-blue);">{{ timetableGroupedByTask.length }}</div>
            </div>
          </div>

          <!-- Grouped by Task Progress Bars -->
          <div v-if="timetableGroupedByTask.length > 0" class="admin-card glass" style="margin-bottom: 24px;">
            <h3 style="margin-bottom: 14px;"><i class="fa-solid fa-chart-bar" style="color: var(--accent-blue);"></i> Rozkład czasu na zadania</h3>
            <div style="display: flex; flex-direction: column; gap: 12px;">
              <div v-for="group in timetableGroupedByTask" :key="group.key">
                <div style="display: flex; justify-content: space-between; font-size: 13.5px; margin-bottom: 5px;">
                  <span>
                    <strong style="color: var(--accent-blue);">#{{ group.taskNumericId || 'N/A' }}</strong>
                    {{ group.taskName }}
                    <span style="color: var(--text-secondary); font-size: 12px;">({{ group.processName }})</span>
                  </span>
                  <span style="font-weight: 700; font-variant-numeric: tabular-nums;">
                    {{ formatTime(group.totalSeconds) }} ({{ group.percent }}%)
                  </span>
                </div>
                <div style="height: 10px; background: rgba(255,255,255,0.06); border-radius: 999px; overflow: hidden;">
                  <div
                    :style="{
                      width: group.percent + '%',
                      height: '100%',
                      background: 'var(--gradient-primary)',
                      borderRadius: '999px'
                    }"
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Chronological Entries List -->
          <h3 style="font-size: 16px; margin-bottom: 12px;">Szczegółowa historia wpisów</h3>
          <div v-if="timetableEntries.length === 0" class="admin-card glass" style="text-align: center; padding: 40px 20px; color: var(--text-secondary);">
            Brak zarejestrowanych wpisów czasu dla dnia {{ timetableDateStr }}.
          </div>
          <div v-else class="timeline">
            <div v-for="entry in timetableEntries" :key="entry.id" class="timeline-item">
              <div>
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 4px;">
                  <span class="task-badge">#{{ entry.task_numeric_id ?? 'N/A' }}</span>
                  <strong>{{ entry.task_name }}</strong>
                  <span class="process-pill">{{ entry.process_name }} <i class="fa-solid fa-angle-right"></i> {{ entry.subprocess_name }}</span>
                  <span class="user-pill"><i class="fa-solid fa-user"></i> {{ entry.username }}</span>
                </div>
                <div style="font-size: 12px; color: var(--text-secondary);">
                  <i class="fa-regular fa-clock"></i>
                  {{ formatDateTimeShort(entry.start_time) }} &rarr; {{ formatDateTimeShort(entry.stop_time) }}
                </div>
              </div>

              <div style="display: flex; align-items: center; gap: 14px;">
                <span style="font-weight: 700; font-size: 16px; color: var(--accent-green); font-variant-numeric: tabular-nums;">
                  {{ formatTime(entry.time_allocated_seconds) }}
                </span>
                <button class="btn sm danger" title="Usuń ten wpis czasu" @click="deleteTimeEntry(entry.id)">
                  <i class="fa-solid fa-trash"></i>
                </button>
              </div>
            </div>
          </div>
        </section>

        <!-- ==================== VIEW 3: REPORTING ==================== -->
        <section v-if="activeView === 'reporting'">
          <div class="view-header-row">
            <div>
              <h2>Raporty i Eksport Danych (AllChargesReport)</h2>
              <p style="color: var(--text-secondary); font-size: 13.5px; margin-top: 4px;">
                Przeglądaj wszystkie alokacje czasu w systemie i eksportuj je do formatu Retro TXT lub CSV.
              </p>
            </div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
              <button class="btn primary" @click="exportReport('txt')">
                <i class="fa-solid fa-file-lines"></i> Eksportuj Retro .TXT
              </button>
              <button class="btn success" @click="exportReport('csv')">
                <i class="fa-solid fa-file-csv"></i> Eksportuj .CSV
              </button>
            </div>
          </div>

          <div class="toolbar-row">
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
              <select v-model="reportUserFilter">
                <option value="">Wszyscy użytkownicy</option>
                <option v-for="u in users" :key="u.id" :value="u.username">{{ u.username }}</option>
              </select>
              <select v-model="reportProcessFilter">
                <option value="">Wszystkie procesy</option>
                <option v-for="p in processes" :key="p.id" :value="p.name">{{ p.name }}</option>
              </select>
              <input v-model="reportSearch" type="text" placeholder="Szukaj Ticketu lub subprocesu..." />
            </div>
            <div style="font-size: 14px; color: var(--text-secondary);">
              Suma dla filtra: <strong style="color: var(--accent-green); font-size: 16px;">{{ formatTime(filteredReportTotalSeconds) }}</strong>
              ({{ filteredReportEntries.length }} wpisów)
            </div>
          </div>

          <div class="data-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Ticket ID</th>
                  <th>Nazwa Zadania</th>
                  <th>Proces</th>
                  <th>Subproces</th>
                  <th>Użytkownik</th>
                  <th>Czas (HH:MM:SS)</th>
                  <th>Czas (s)</th>
                  <th>Start</th>
                  <th>Stop</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="filteredReportEntries.length === 0">
                  <td colspan="9" style="text-align: center; padding: 30px; color: var(--text-secondary);">
                    Brak wpisów spełniających kryteria raportu.
                  </td>
                </tr>
                <tr v-for="e in filteredReportEntries" :key="e.id">
                  <td><span class="task-badge">#{{ e.task_numeric_id ?? 'N/A' }}</span></td>
                  <td style="font-weight: 500;">{{ e.task_name }}</td>
                  <td>{{ e.process_name }}</td>
                  <td>{{ e.subprocess_name }}</td>
                  <td><span class="user-pill">{{ e.username }}</span></td>
                  <td style="color: var(--accent-green); font-weight: 600; font-variant-numeric: tabular-nums;">
                    {{ formatTime(e.time_allocated_seconds) }}
                  </td>
                  <td style="color: var(--text-secondary); font-variant-numeric: tabular-nums;">{{ e.time_allocated_seconds }}s</td>
                  <td style="font-size: 12px; color: var(--text-secondary);">{{ formatDateTimeFull(e.start_time) }}</td>
                  <td style="font-size: 12px; color: var(--text-secondary);">{{ formatDateTimeFull(e.stop_time) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- ==================== VIEW 4: ADMIN / KONFIGURACJA ==================== -->
        <section v-if="activeView === 'admin'">
          <div class="view-header-row">
            <div>
              <h2>Konfiguracja Procesów, Zadań i Użytkowników</h2>
              <p style="color: var(--text-secondary); font-size: 13.5px; margin-top: 4px;">
                Zarządzaj słownikiem procesów biznesowych, ich etapami (subprocesami), zadaniami oraz dostępem użytkowników.
              </p>
            </div>
          </div>

          <div class="admin-grid">
            <!-- 1. Processes -->
            <div class="admin-card">
              <h3><i class="fa-solid fa-folder-tree" style="color: var(--accent-blue);"></i> 1. Kategorie: Procesy</h3>
              <p style="font-size: 12px; color: var(--text-secondary);">Główne obszary prac (np. Pulpit Wewnętrzny, Produkcja, Sprzedaż)</p>
              <form class="input-group" @submit.prevent="handleCreateProcess">
                <input v-model="newProcessName" type="text" placeholder="Nazwa nowego procesu..." style="flex: 1;" required />
                <button type="submit" class="btn primary"><i class="fa-solid fa-plus"></i> Dodaj</button>
              </form>
            </div>

            <!-- 2. Subprocesses -->
            <div class="admin-card">
              <h3><i class="fa-solid fa-tags" style="color: var(--accent-purple);"></i> 2. Etapy: Subprocesy</h3>
              <p style="font-size: 12px; color: var(--text-secondary);">Podkategorie czasu w procesie (np. Analiza, Development, Testy)</p>
              <form class="input-group" style="flex-wrap: wrap;" @submit.prevent="handleCreateSubprocess">
                <select v-model.number="newSubprocess.process_id" style="flex: 1; min-width: 140px;" required>
                  <option value="" disabled>Wybierz Proces...</option>
                  <option v-for="p in processes" :key="p.id" :value="p.id">{{ p.name }}</option>
                </select>
                <input v-model="newSubprocess.name" type="text" placeholder="Nazwa subprocesu..." style="flex: 1; min-width: 140px;" required />
                <button type="submit" class="btn primary"><i class="fa-solid fa-plus"></i> Dodaj</button>
              </form>
            </div>

            <!-- 3. Tasks -->
            <div class="admin-card">
              <h3><i class="fa-solid fa-ticket" style="color: var(--accent-green);"></i> 3. Utwórz Zadanie (Ticket)</h3>
              <p style="font-size: 12px; color: var(--text-secondary);">Zdefiniuj Ticket i przypisz mu odpowiedni proces.</p>
              <form class="input-group" style="flex-wrap: wrap;" @submit.prevent="handleAdminCreateTask">
                <input v-model.number="adminTaskForm.numeric_id" type="number" placeholder="ID (np. 2001)" style="width: 110px;" required />
                <input v-model="adminTaskForm.name" type="text" placeholder="Nazwa zadania..." style="flex: 1; min-width: 150px;" required />
                <select v-model.number="adminTaskForm.process_id" style="width: 100%;" required>
                  <option value="" disabled>Wybierz Proces...</option>
                  <option v-for="p in processes" :key="p.id" :value="p.id">{{ p.name }}</option>
                </select>
                <button type="submit" class="btn success" style="width: 100%;"><i class="fa-solid fa-plus"></i> Utwórz Ticket</button>
              </form>
            </div>

            <!-- 4. Users -->
            <div class="admin-card">
              <h3><i class="fa-solid fa-users" style="color: var(--accent-amber);"></i> 4. Użytkownicy Systemu</h3>
              <p style="font-size: 12px; color: var(--text-secondary);">Dodaj konto pracownika lub zmień jego hasło.</p>
              <form class="input-group" style="flex-wrap: wrap;" @submit.prevent="handleCreateUser">
                <input v-model="newUserForm.username" type="text" placeholder="Login" style="flex: 1; min-width: 100px;" required />
                <input v-model="newUserForm.email" type="email" placeholder="E-mail (opcjonalny)" style="flex: 1; min-width: 130px;" />
                <input v-model="newUserForm.password" type="password" placeholder="Hasło" style="flex: 1; min-width: 100px;" required />
                <button type="submit" class="btn primary"><i class="fa-solid fa-user-plus"></i></button>
              </form>

              <div style="margin-top: 14px; max-height: 170px; overflow-y: auto;">
                <div
                  v-for="u in users"
                  :key="u.id"
                  style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 13px;"
                >
                  <span><strong>{{ u.username }}</strong> <span style="color: var(--text-secondary); font-size: 11px;">(ID: {{ u.id }})</span></span>
                  <div style="display: flex; gap: 6px;">
                    <button class="btn sm" title="Zmień hasło" @click="openPasswordModal(u)"><i class="fa-solid fa-key"></i></button>
                    <button v-if="u.id !== currentUser?.id" class="btn sm danger" title="Usuń użytkownika" @click="handleDeleteUser(u)">
                      <i class="fa-solid fa-trash"></i>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Processes & Subprocesses Structure Editor -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; margin-top: 28px;">
            <div class="admin-card">
              <h3 style="margin-bottom: 14px;"><i class="fa-solid fa-sitemap"></i> Słownik Procesów i Subprocesów</h3>
              <div v-for="p in processes" :key="p.id" style="margin-bottom: 14px; border: 1px solid var(--border-color); border-radius: 10px; overflow: hidden;">
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.04); padding: 10px 14px;">
                  <strong><i class="fa-solid fa-folder" style="color: var(--accent-blue); margin-right: 6px;"></i> {{ p.name }}</strong>
                  <div style="display: flex; gap: 6px;">
                    <button class="btn sm" title="Zmień nazwę procesu" @click="openRenameModal('process', p)"><i class="fa-solid fa-pen"></i></button>
                    <button class="btn sm danger" title="Usuń proces" @click="handleDeleteProcess(p)"><i class="fa-solid fa-trash"></i></button>
                  </div>
                </div>
                <div style="padding: 8px 14px;">
                  <div v-if="p.subprocesses.length === 0" style="font-size: 12px; color: var(--text-secondary); padding: 4px 0;">
                    Brak subprocesów
                  </div>
                  <div
                    v-for="sp in p.subprocesses"
                    :key="sp.id"
                    style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 13px;"
                  >
                    <span><i class="fa-solid fa-tag" style="color: var(--text-secondary); font-size: 11px; margin-right: 6px;"></i> {{ sp.name }}</span>
                    <div style="display: flex; gap: 6px;">
                      <button class="btn sm" title="Zmień nazwę subprocesu" @click="openRenameModal('subprocess', sp)"><i class="fa-solid fa-pen"></i></button>
                      <button class="btn sm danger" title="Usuń subproces" @click="handleDeleteSubprocess(sp)"><i class="fa-solid fa-trash"></i></button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- All Tasks Management -->
            <div class="admin-card">
              <h3 style="margin-bottom: 14px;"><i class="fa-solid fa-list-check"></i> Wszystkie Zadania (Tickets) w Systemie</h3>
              <div v-if="allTasks.length === 0" style="color: var(--text-secondary); font-size: 13px;">Brak zadań.</div>
              <div
                v-for="t in allTasks"
                :key="t.id"
                style="padding: 12px; border: 1px solid var(--border-color); border-radius: 10px; margin-bottom: 10px; background: rgba(255,255,255,0.02);"
              >
                <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap;">
                  <div>
                    <span class="task-badge">#{{ t.numeric_id }}</span>
                    <strong style="margin-left: 8px;">{{ t.name }}</strong>
                    <span v-if="getProcessById(t.process_id)" class="process-pill" style="margin-left: 8px;">
                      {{ getProcessById(t.process_id).name }}
                    </span>
                  </div>
                  <div style="display: flex; gap: 6px;">
                    <button class="btn sm primary" title="Przypisz / Edytuj użytkowników" @click="openAssignModal(t)">
                      <i class="fa-solid fa-user-check"></i> Użytkownicy
                    </button>
                    <button class="btn sm" title="Edytuj Ticket" @click="openEditTaskModal(t)">
                      <i class="fa-solid fa-pen"></i>
                    </button>
                    <button class="btn sm" :class="{ success: t.completed }" title="Przełącz status ukończenia" @click="toggleTaskComplete(t)">
                      <i class="fa-solid fa-check"></i>
                    </button>
                    <button class="btn sm danger" title="Usuń Ticket" @click="handleDeleteTask(t)">
                      <i class="fa-solid fa-trash"></i>
                    </button>
                  </div>
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
                  Przypisani:
                  <span v-if="t.users.length === 0" style="color: var(--accent-red);">Brak przypisanych osób</span>
                  <span v-for="u in t.users" :key="u.id" class="user-pill" style="margin-right: 4px;">{{ u.username }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <!-- Footer -->
      <footer class="app-footer" :class="{ collapsed: sidebarCollapsed }">
        <div>
          Zalogowany jako: <strong style="color: var(--text-primary);">{{ currentUser?.username || '...' }}</strong>
        </div>
        <div>
          TimeTracker Pro | Reaktywny Frontend <strong>Vue 3 + FastAPI</strong>
        </div>
      </footer>
    </div>

    <!-- ==================== MODALS ==================== -->

    <!-- Manual Time Allocation Modal -->
    <div v-if="manualModal.open" class="modal-overlay" @click.self="manualModal.open = false">
      <div class="modal-box glass">
        <h3 style="margin-bottom: 8px;"><i class="fa-solid fa-stopwatch" style="color: var(--accent-blue);"></i> Ręczna alokacja czasu</h3>
        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
          Zadanie: <strong>#{{ manualModal.task?.numeric_id }} {{ manualModal.task?.name }}</strong><br />
          Etap: <strong>{{ manualModal.subprocess?.name }}</strong>
        </p>
        <form @submit.prevent="submitManualAllocation">
          <div style="display: flex; gap: 10px; margin-bottom: 16px;">
            <div style="flex: 1;">
              <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Minuty</label>
              <input v-model.number="manualModal.minutes" type="number" min="0" style="width: 100%;" />
            </div>
            <div style="flex: 1;">
              <label style="font-size: 12px; color: var(--text-secondary); display: block; margin-bottom: 4px;">Sekundy</label>
              <input v-model.number="manualModal.seconds" type="number" min="0" max="59" style="width: 100%;" />
            </div>
          </div>
          <div style="display: flex; gap: 10px;">
            <button type="submit" class="btn success" style="flex: 1;">Zapisz czas</button>
            <button type="button" class="btn" style="flex: 1;" @click="manualModal.open = false">Anuluj</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Assign Users Modal -->
    <div v-if="assignModal.open" class="modal-overlay" @click.self="assignModal.open = false">
      <div class="modal-box glass">
        <h3 style="margin-bottom: 8px;"><i class="fa-solid fa-user-check" style="color: var(--accent-blue);"></i> Przypisani użytkownicy</h3>
        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
          Ticket: <strong>#{{ assignModal.task?.numeric_id }} {{ assignModal.task?.name }}</strong>
        </p>
        <div style="display: flex; flex-direction: column; gap: 8px; max-height: 240px; overflow-y: auto; margin-bottom: 18px;">
          <label
            v-for="u in users"
            :key="u.id"
            style="display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: rgba(255,255,255,0.04); border-radius: 8px; cursor: pointer;"
          >
            <input v-model="assignModal.selectedUserIds" type="checkbox" :value="u.id" />
            <span>{{ u.username }} <span style="color: var(--text-secondary); font-size: 12px;">({{ u.email }})</span></span>
          </label>
        </div>
        <div style="display: flex; gap: 10px;">
          <button class="btn primary" style="flex: 1;" @click="saveAssignedUsers">Zapisz przypisania</button>
          <button class="btn" style="flex: 1;" @click="assignModal.open = false">Anuluj</button>
        </div>
      </div>
    </div>

    <!-- Edit Task Modal -->
    <div v-if="editTaskModal.open" class="modal-overlay" @click.self="editTaskModal.open = false">
      <div class="modal-box glass">
        <h3 style="margin-bottom: 14px;"><i class="fa-solid fa-pen" style="color: var(--accent-blue);"></i> Edycja Zadania (Ticket)</h3>
        <form style="display: flex; flex-direction: column; gap: 12px;" @submit.prevent="saveEditedTask">
          <div>
            <label style="font-size: 12px; color: var(--text-secondary);">Ticket ID</label>
            <input v-model.number="editTaskModal.numeric_id" type="number" style="width: 100%; margin-top: 4px;" required />
          </div>
          <div>
            <label style="font-size: 12px; color: var(--text-secondary);">Nazwa zadania</label>
            <input v-model="editTaskModal.name" type="text" style="width: 100%; margin-top: 4px;" required />
          </div>
          <div>
            <label style="font-size: 12px; color: var(--text-secondary);">Przypisany Proces</label>
            <select v-model.number="editTaskModal.process_id" style="width: 100%; margin-top: 4px;" required>
              <option v-for="p in processes" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
          <div style="display: flex; gap: 10px; margin-top: 6px;">
            <button type="submit" class="btn primary" style="flex: 1;">Zapisz zmiany</button>
            <button type="button" class="btn" style="flex: 1;" @click="editTaskModal.open = false">Anuluj</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Rename Process / Subprocess Modal -->
    <div v-if="renameModal.open" class="modal-overlay" @click.self="renameModal.open = false">
      <div class="modal-box glass">
        <h3 style="margin-bottom: 14px;">Zmień nazwę</h3>
        <form @submit.prevent="submitRename">
          <input v-model="renameModal.name" type="text" style="width: 100%; margin-bottom: 16px;" required />
          <div style="display: flex; gap: 10px;">
            <button type="submit" class="btn primary" style="flex: 1;">Zapisz</button>
            <button type="button" class="btn" style="flex: 1;" @click="renameModal.open = false">Anuluj</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Change Password Modal -->
    <div v-if="passwordModal.open" class="modal-overlay" @click.self="passwordModal.open = false">
      <div class="modal-box glass">
        <h3 style="margin-bottom: 10px;">Zmień hasło: {{ passwordModal.user?.username }}</h3>
        <form @submit.prevent="submitPasswordChange">
          <input v-model="passwordModal.password" type="password" placeholder="Nowe hasło..." style="width: 100%; margin-bottom: 16px;" required />
          <div style="display: flex; gap: 10px;">
            <button type="submit" class="btn primary" style="flex: 1;">Zmień hasło</button>
            <button type="button" class="btn" style="flex: 1;" @click="passwordModal.open = false">Anuluj</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Toasts -->
    <div class="toast-container">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">
        <i class="fa-solid" :class="t.type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-check'"></i>
        <span>{{ t.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'

// ==================== AUTH & CORE STATE ====================
const authToken = ref(localStorage.getItem('timeTrackerToken') || '')
const currentUser = ref(null)
const loginForm = reactive({ username: '', password: '' })
const loginError = ref('')
const loginLoading = ref(false)

const activeView = ref('tasks')
const sidebarCollapsed = ref(localStorage.getItem('sidebarCollapsed') === 'true')
const mobileMenuOpen = ref(false)

// ==================== DATA COLLECTIONS ====================
const processes = ref([])
const userTasks = ref([])
const allTasks = ref([])
const users = ref([])
const timetableEntries = ref([])
const allReportEntries = ref([])

// Expanded tasks persisted in localStorage
const savedExpanded = JSON.parse(localStorage.getItem('expandedTaskIds') || '[]')
const expandedTaskIds = reactive(new Set(savedExpanded))

// ==================== PERSISTENT TIMESTAMP TIMER ====================
const TIMER_STORAGE_KEY = 'timeTrackerTimerState_v2'
const savedTimer = JSON.parse(localStorage.getItem(TIMER_STORAGE_KEY) || 'null')

const timerState = reactive({
  isRunning: savedTimer?.isRunning || false,
  lastStartTimestamp: savedTimer?.lastStartTimestamp || null,
  accumulatedTotalSeconds: savedTimer?.accumulatedTotalSeconds || 0,
  accumulatedTaskSeconds: savedTimer?.accumulatedTaskSeconds || 0
})

const nowTick = ref(Date.now())
let tickInterval = null

function saveTimerState() {
  localStorage.setItem(TIMER_STORAGE_KEY, JSON.stringify({
    isRunning: timerState.isRunning,
    lastStartTimestamp: timerState.lastStartTimestamp,
    accumulatedTotalSeconds: timerState.accumulatedTotalSeconds,
    accumulatedTaskSeconds: timerState.accumulatedTaskSeconds
  }))
}

const elapsedSinceStart = computed(() => {
  if (!timerState.isRunning || !timerState.lastStartTimestamp) return 0
  return Math.max(0, Math.floor((nowTick.value - timerState.lastStartTimestamp) / 1000))
})

const displayTotalSeconds = computed(() => {
  return timerState.accumulatedTotalSeconds + elapsedSinceStart.value
})

const displayTaskSeconds = computed(() => {
  return timerState.accumulatedTaskSeconds + elapsedSinceStart.value
})

function toggleClock() {
  const now = Date.now()
  nowTick.value = now
  if (timerState.isRunning) {
    // Pause: commit elapsed seconds into accumulated counters
    const delta = Math.max(0, Math.floor((now - timerState.lastStartTimestamp) / 1000))
    timerState.accumulatedTotalSeconds += delta
    timerState.accumulatedTaskSeconds += delta
    timerState.isRunning = false
    timerState.lastStartTimestamp = null
    saveTimerState()
    showToast('Zegar zatrzymany. Możesz zaalokować naliczony Task Time na wybrany etap.')
  } else {
    timerState.isRunning = true
    timerState.lastStartTimestamp = now
    saveTimerState()
    showToast('Zegar uruchomiony!')
  }
}

function consumeTaskTimerSeconds() {
  const now = Date.now()
  nowTick.value = now
  if (timerState.isRunning && timerState.lastStartTimestamp) {
    const delta = Math.max(0, Math.floor((now - timerState.lastStartTimestamp) / 1000))
    timerState.accumulatedTotalSeconds += delta
    const totalTaskSec = timerState.accumulatedTaskSeconds + delta
    // Reset only task timer while keeping total timer running seamlessly
    timerState.accumulatedTaskSeconds = 0
    timerState.lastStartTimestamp = now
    saveTimerState()
    return totalTaskSec
  } else {
    const totalTaskSec = timerState.accumulatedTaskSeconds
    timerState.accumulatedTaskSeconds = 0
    saveTimerState()
    return totalTaskSec
  }
}

function resetTaskTimer() {
  const now = Date.now()
  nowTick.value = now
  if (timerState.isRunning && timerState.lastStartTimestamp) {
    const delta = Math.max(0, Math.floor((now - timerState.lastStartTimestamp) / 1000))
    timerState.accumulatedTotalSeconds += delta
    timerState.lastStartTimestamp = now
  }
  timerState.accumulatedTaskSeconds = 0
  saveTimerState()
  showToast('Wyzerowano licznik Task Time')
}

function resetTotalTimer() {
  const now = Date.now()
  nowTick.value = now
  if (timerState.isRunning) {
    timerState.lastStartTimestamp = now
  }
  timerState.accumulatedTotalSeconds = 0
  timerState.accumulatedTaskSeconds = 0
  saveTimerState()
  showToast('Wyzerowano oba liczniki czasu')
}

// ==================== API HELPER ====================
async function apiFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (authToken.value) {
    headers['Authorization'] = `Bearer ${authToken.value}`
  }
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  const response = await fetch(url, { ...options, headers })
  if (response.status === 401) {
    logout()
    throw new Error('Sesja wygasła. Zaloguj się ponownie.')
  }
  if (!response.ok) {
    let errDetail = 'Wystąpił błąd zapytania'
    try {
      const errData = await response.json()
      errDetail = errData.detail || errDetail
    } catch (_) {}
    throw new Error(errDetail)
  }
  return response.json()
}

// ==================== AUTH ACTIONS ====================
async function handleLogin() {
  loginError.value = ''
  loginLoading.value = true
  try {
    const formData = new FormData()
    formData.append('username', loginForm.username)
    formData.append('password', loginForm.password)
    const res = await fetch('/api/auth/token', { method: 'POST', body: formData })
    const data = await res.json()
    if (!res.ok) {
      loginError.value = data.detail || 'Nieprawidłowy login lub hasło'
      return
    }
    authToken.value = data.access_token
    localStorage.setItem('timeTrackerToken', data.access_token)
    loginForm.password = ''
    await initAppData()
    showToast('Zalogowano pomyślnie!', 'success')
  } catch (err) {
    loginError.value = 'Brak połączenia z serwerem API'
  } finally {
    loginLoading.value = false
  }
}

function logout() {
  authToken.value = ''
  currentUser.value = null
  localStorage.removeItem('timeTrackerToken')
}

// ==================== INITIALIZATION & DATA FETCHING ====================
async function initAppData() {
  if (!authToken.value) return
  try {
    currentUser.value = await apiFetch('/api/me')
    await Promise.all([
      fetchProcessesAndTasks(),
      fetchUsers(),
      fetchTimetableEntries(),
      fetchReportEntries()
    ])
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function fetchProcessesAndTasks() {
  const [procData, myTasksData, allTasksData] = await Promise.all([
    apiFetch('/api/processes'),
    apiFetch('/api/tasks'),
    apiFetch('/api/tasks?all_data=true')
  ])
  processes.value = procData
  userTasks.value = myTasksData
  allTasks.value = allTasksData

  // Auto-expand first task if none expanded yet
  if (expandedTaskIds.size === 0 && myTasksData.length > 0) {
    expandedTaskIds.add(myTasksData[0].id)
    saveExpandedTasks()
  }
}

async function fetchUsers() {
  users.value = await apiFetch('/api/users')
}

// ==================== TASKS & ALLOCATION LOGIC ====================
const showQuickAdd = ref(false)
const quickTaskForm = reactive({ numeric_id: null, name: '', process_id: '', user_id: null })
const taskFilter = ref('active')
const taskProcessFilter = ref('')
const taskSearch = ref('')

const activeTasksCount = computed(() => userTasks.value.filter(t => !t.completed).length)
const completedTasksCount = computed(() => userTasks.value.filter(t => t.completed).length)

const filteredTasks = computed(() => {
  return userTasks.value.filter(t => {
    if (taskFilter.value === 'active' && t.completed) return false
    if (taskFilter.value === 'completed' && !t.completed) return false
    if (taskProcessFilter.value && t.process_id !== Number(taskProcessFilter.value)) return false
    if (taskSearch.value.trim()) {
      const q = taskSearch.value.trim().toLowerCase()
      const matchId = String(t.numeric_id).includes(q)
      const matchName = t.name.toLowerCase().includes(q)
      if (!matchId && !matchName) return false
    }
    return true
  })
})

function getProcessById(processId) {
  return processes.value.find(p => p.id === processId)
}

function isTaskExpanded(taskId) {
  return expandedTaskIds.has(taskId)
}

function toggleTaskExpand(taskId) {
  if (expandedTaskIds.has(taskId)) {
    expandedTaskIds.delete(taskId)
  } else {
    expandedTaskIds.add(taskId)
  }
  saveExpandedTasks()
}

function saveExpandedTasks() {
  localStorage.setItem('expandedTaskIds', JSON.stringify([...expandedTaskIds]))
}

function getTaskTotalSeconds(task) {
  if (!task.time_entries) return 0
  return task.time_entries.reduce((acc, e) => acc + (e.time_allocated_seconds || 0), 0)
}

function getSubprocessSecondsInTask(task, subprocessId) {
  if (!task.time_entries) return 0
  return task.time_entries
    .filter(e => e.subprocess_id === subprocessId)
    .reduce((acc, e) => acc + (e.time_allocated_seconds || 0), 0)
}

function isSubprocessCompletedInTask(task, subprocessId) {
  return Array.isArray(task.completed_subprocess_ids) && task.completed_subprocess_ids.includes(subprocessId)
}

async function allocateFromTimer(task, subprocess) {
  const currentSec = displayTaskSeconds.value
  if (currentSec <= 0) {
    showToast('Zegar Task Time wynosi 00:00:00! Uruchom zegar lub użyj przycisku [+] do ręcznego wpisu.', 'error')
    return
  }

  const secondsToAllocate = consumeTaskTimerSeconds()
  try {
    await apiFetch('/api/allocate', {
      method: 'POST',
      body: JSON.stringify({
        task_id: task.id,
        subprocess_id: subprocess.id,
        time_allocated_seconds: secondsToAllocate
      })
    })
    showToast(`Zaalokowano ${formatTime(secondsToAllocate)} na #${task.numeric_id} -> ${subprocess.name}`, 'success')
    await Promise.all([
      fetchProcessesAndTasks(),
      fetchTimetableEntries(),
      fetchReportEntries()
    ])
  } catch (err) {
    showToast(err.message, 'error')
  }
}

// Manual Allocation Modal
const manualModal = reactive({
  open: false,
  task: null,
  subprocess: null,
  minutes: 15,
  seconds: 0
})

function openManualAllocateModal(task, subprocess) {
  manualModal.task = task
  manualModal.subprocess = subprocess
  manualModal.minutes = 15
  manualModal.seconds = 0
  manualModal.open = true
}

async function submitManualAllocation() {
  const totalSec = (Number(manualModal.minutes) || 0) * 60 + (Number(manualModal.seconds) || 0)
  if (totalSec <= 0) {
    showToast('Podaj czas większy od 0 sekund', 'error')
    return
  }
  try {
    await apiFetch('/api/allocate', {
      method: 'POST',
      body: JSON.stringify({
        task_id: manualModal.task.id,
        subprocess_id: manualModal.subprocess.id,
        time_allocated_seconds: totalSec
      })
    })
    manualModal.open = false
    showToast(`Dodano ręcznie ${formatTime(totalSec)} na ${manualModal.subprocess.name}`, 'success')
    await Promise.all([
      fetchProcessesAndTasks(),
      fetchTimetableEntries(),
      fetchReportEntries()
    ])
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function toggleTaskSubprocess(task, subprocessId) {
  try {
    await apiFetch(`/api/tasks/${task.id}/subprocesses/${subprocessId}/toggle_complete`, {
      method: 'PATCH'
    })
    await fetchProcessesAndTasks()
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function toggleTaskComplete(task) {
  try {
    await apiFetch(`/api/tasks/${task.id}/toggle_complete`, { method: 'PATCH' })
    await fetchProcessesAndTasks()
    showToast(`Zmieniono status zadania #${task.numeric_id}`, 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function handleQuickCreateTask() {
  try {
    const created = await apiFetch('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({
        numeric_id: Number(quickTaskForm.numeric_id),
        name: quickTaskForm.name.trim(),
        process_id: Number(quickTaskForm.process_id),
        user_ids: quickTaskForm.user_id ? [Number(quickTaskForm.user_id)] : []
      })
    })
    expandedTaskIds.add(created.id)
    saveExpandedTasks()
    quickTaskForm.numeric_id = null
    quickTaskForm.name = ''
    showQuickAdd.value = false
    await fetchProcessesAndTasks()
    showToast(`Utworzono Ticket #${created.numeric_id}`, 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

// ==================== TIMETABLE LOGIC ====================
function getTodayDateString() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const timetableDateStr = ref(getTodayDateString())
const timetableAllUsers = ref(false)

async function fetchTimetableEntries() {
  if (!authToken.value) return
  try {
    const params = new URLSearchParams({
      date_str: timetableDateStr.value,
      all_users: String(timetableAllUsers.value)
    })
    timetableEntries.value = await apiFetch(`/api/time-entries?${params.toString()}`)
  } catch (err) {
    showToast(err.message, 'error')
  }
}

function shiftTimetableDate(days) {
  const parts = timetableDateStr.value.split('-').map(Number)
  const dt = new Date(parts[0], parts[1] - 1, parts[2])
  dt.setDate(dt.getDate() + days)
  const y = dt.getFullYear()
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const d = String(dt.getDate()).padStart(2, '0')
  timetableDateStr.value = `${y}-${m}-${d}`
  fetchTimetableEntries()
}

function setTimetableToday() {
  timetableDateStr.value = getTodayDateString()
  fetchTimetableEntries()
}

const timetableTotalSeconds = computed(() => {
  return timetableEntries.value.reduce((acc, e) => acc + e.time_allocated_seconds, 0)
})

const timetableGroupedByTask = computed(() => {
  const map = new Map()
  const total = timetableTotalSeconds.value || 1
  for (const e of timetableEntries.value) {
    const key = e.task_id || e.task_name
    if (!map.has(key)) {
      map.set(key, {
        key,
        taskNumericId: e.task_numeric_id,
        taskName: e.task_name,
        processName: e.process_name,
        totalSeconds: 0,
        percent: 0
      })
    }
    map.get(key).totalSeconds += e.time_allocated_seconds
  }
  const list = Array.from(map.values()).sort((a, b) => b.totalSeconds - a.totalSeconds)
  list.forEach(item => {
    item.percent = Math.round((item.totalSeconds / total) * 100)
  })
  return list
})

async function deleteTimeEntry(entryId) {
  if (!confirm('Czy na pewno chcesz usunąć ten wpis czasu?')) return
  try {
    await apiFetch(`/api/time-entries/${entryId}`, { method: 'DELETE' })
    showToast('Wpis czasu został usunięty', 'success')
    await Promise.all([
      fetchProcessesAndTasks(),
      fetchTimetableEntries(),
      fetchReportEntries()
    ])
  } catch (err) {
    showToast(err.message, 'error')
  }
}

// ==================== REPORTING LOGIC ====================
const reportUserFilter = ref('')
const reportProcessFilter = ref('')
const reportSearch = ref('')

async function fetchReportEntries() {
  if (!authToken.value) return
  try {
    allReportEntries.value = await apiFetch('/api/time-entries?all_users=true')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

const filteredReportEntries = computed(() => {
  return allReportEntries.value.filter(e => {
    if (reportUserFilter.value && e.username !== reportUserFilter.value) return false
    if (reportProcessFilter.value && e.process_name !== reportProcessFilter.value) return false
    if (reportSearch.value.trim()) {
      const q = reportSearch.value.trim().toLowerCase()
      const matchTask = e.task_name.toLowerCase().includes(q) || String(e.task_numeric_id || '').includes(q)
      const matchSp = e.subprocess_name.toLowerCase().includes(q)
      if (!matchTask && !matchSp) return false
    }
    return true
  })
})

const filteredReportTotalSeconds = computed(() => {
  return filteredReportEntries.value.reduce((acc, e) => acc + e.time_allocated_seconds, 0)
})

function exportReport(format) {
  if (format === 'txt') {
    window.open(`/api/report/allcharges?token=${authToken.value}`, '_blank')
  } else {
    window.open(`/api/report/csv?token=${authToken.value}`, '_blank')
  }
}

// ==================== ADMIN / CONFIGURATION ACTIONS ====================
const newProcessName = ref('')
const newSubprocess = reactive({ process_id: '', name: '' })
const adminTaskForm = reactive({ numeric_id: null, name: '', process_id: '' })
const newUserForm = reactive({ username: '', email: '', password: '' })

async function handleCreateProcess() {
  if (!newProcessName.value.trim()) return
  try {
    await apiFetch('/api/processes', {
      method: 'POST',
      body: JSON.stringify({ name: newProcessName.value.trim() })
    })
    newProcessName.value = ''
    await fetchProcessesAndTasks()
    showToast('Dodano nowy proces', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function handleDeleteProcess(p) {
  if (!confirm(`Czy na pewno usunąć proces "${p.name}" wraz z jego subprocesami?`)) return
  try {
    await apiFetch(`/api/processes/${p.id}`, { method: 'DELETE' })
    await fetchProcessesAndTasks()
    showToast('Proces został usunięty', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function handleCreateSubprocess() {
  if (!newSubprocess.process_id || !newSubprocess.name.trim()) return
  try {
    await apiFetch('/api/subprocesses', {
      method: 'POST',
      body: JSON.stringify({
        process_id: Number(newSubprocess.process_id),
        name: newSubprocess.name.trim()
      })
    })
    newSubprocess.name = ''
    await fetchProcessesAndTasks()
    showToast('Dodano nowy subproces (etap)', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function handleDeleteSubprocess(sp) {
  if (!confirm(`Usunąć subproces "${sp.name}"?`)) return
  try {
    await apiFetch(`/api/subprocesses/${sp.id}`, { method: 'DELETE' })
    await fetchProcessesAndTasks()
    showToast('Subproces został usunięty', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function handleAdminCreateTask() {
  try {
    const created = await apiFetch('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({
        numeric_id: Number(adminTaskForm.numeric_id),
        name: adminTaskForm.name.trim(),
        process_id: Number(adminTaskForm.process_id)
      })
    })
    adminTaskForm.numeric_id = null
    adminTaskForm.name = ''
    expandedTaskIds.add(created.id)
    saveExpandedTasks()
    await fetchProcessesAndTasks()
    showToast(`Utworzono Ticket #${created.numeric_id}`, 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function handleDeleteTask(task) {
  if (!confirm(`Czy na pewno usunąć Ticket #${task.numeric_id}: "${task.name}"?`)) return
  try {
    await apiFetch(`/api/tasks/${task.id}`, { method: 'DELETE' })
    await Promise.all([fetchProcessesAndTasks(), fetchTimetableEntries(), fetchReportEntries()])
    showToast('Ticket został usunięty', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function handleCreateUser() {
  try {
    await apiFetch('/api/users', {
      method: 'POST',
      body: JSON.stringify({
        username: newUserForm.username.trim(),
        email: newUserForm.email.trim(),
        password: newUserForm.password
      })
    })
    newUserForm.username = ''
    newUserForm.email = ''
    newUserForm.password = ''
    await fetchUsers()
    showToast('Dodano nowego użytkownika', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function handleDeleteUser(u) {
  if (!confirm(`Usunąć trwale użytkownika "${u.username}"?`)) return
  try {
    await apiFetch(`/api/users/${u.id}`, { method: 'DELETE' })
    await fetchUsers()
    showToast('Użytkownik usunięty', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

// Modals in Admin
const assignModal = reactive({ open: false, task: null, selectedUserIds: [] })
function openAssignModal(task) {
  assignModal.task = task
  assignModal.selectedUserIds = task.users.map(u => u.id)
  assignModal.open = true
}
async function saveAssignedUsers() {
  try {
    await apiFetch(`/api/tasks/${assignModal.task.id}`, {
      method: 'PUT',
      body: JSON.stringify({ user_ids: assignModal.selectedUserIds })
    })
    assignModal.open = false
    await fetchProcessesAndTasks()
    showToast('Zaktualizowano przypisanych użytkowników', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

const editTaskModal = reactive({ open: false, id: null, numeric_id: null, name: '', process_id: null })
function openEditTaskModal(task) {
  editTaskModal.id = task.id
  editTaskModal.numeric_id = task.numeric_id
  editTaskModal.name = task.name
  editTaskModal.process_id = task.process_id
  editTaskModal.open = true
}
async function saveEditedTask() {
  try {
    await apiFetch(`/api/tasks/${editTaskModal.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        numeric_id: Number(editTaskModal.numeric_id),
        name: editTaskModal.name.trim(),
        process_id: Number(editTaskModal.process_id)
      })
    })
    editTaskModal.open = false
    await Promise.all([fetchProcessesAndTasks(), fetchTimetableEntries(), fetchReportEntries()])
    showToast('Zapisano zmiany w zadaniu', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

const renameModal = reactive({ open: false, type: '', id: null, name: '' })
function openRenameModal(type, item) {
  renameModal.type = type
  renameModal.id = item.id
  renameModal.name = item.name
  renameModal.open = true
}
async function submitRename() {
  try {
    const endpoint = renameModal.type === 'process'
      ? `/api/processes/${renameModal.id}`
      : `/api/subprocesses/${renameModal.id}`
    await apiFetch(endpoint, {
      method: 'PUT',
      body: JSON.stringify({ name: renameModal.name.trim() })
    })
    renameModal.open = false
    await Promise.all([fetchProcessesAndTasks(), fetchTimetableEntries(), fetchReportEntries()])
    showToast('Zmieniono nazwę', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

const passwordModal = reactive({ open: false, user: null, password: '' })
function openPasswordModal(u) {
  passwordModal.user = u
  passwordModal.password = ''
  passwordModal.open = true
}
async function submitPasswordChange() {
  try {
    await apiFetch(`/api/users/${passwordModal.user.id}`, {
      method: 'PUT',
      body: JSON.stringify({ password: passwordModal.password })
    })
    passwordModal.open = false
    showToast('Hasło zostało zmienione', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

// ==================== NAVIGATION & UI UTILS ====================
function switchView(view) {
  activeView.value = view
  mobileMenuOpen.value = false
  if (view === 'timetable') fetchTimetableEntries()
  if (view === 'reporting') fetchReportEntries()
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebarCollapsed', String(sidebarCollapsed.value))
}

function formatTime(seconds) {
  const s = Math.max(0, Math.floor(seconds || 0))
  const hrs = Math.floor(s / 3600)
  const mins = Math.floor((s % 3600) / 60)
  const secs = s % 60
  return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

function formatDateTimeShort(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatDateTimeFull(isoStr) {
  if (!isoStr) return ''
  return isoStr.replace('T', ' ').slice(0, 19)
}

const toasts = ref([])
let toastIdCounter = 1
function showToast(message, type = 'info') {
  const id = toastIdCounter++
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 3500)
}

// ==================== LIFECYCLE ====================
onMounted(() => {
  tickInterval = setInterval(() => {
    nowTick.value = Date.now()
  }, 500)

  if (authToken.value) {
    initAppData()
  }
})

onUnmounted(() => {
  if (tickInterval) clearInterval(tickInterval)
})
</script>
