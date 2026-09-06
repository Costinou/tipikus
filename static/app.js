// ===== ETAT & STOCKAGE =====
let state = { profiles: [], decks: [], last_updated: 0 };
let currentProfileId = localStorage.getItem('tipikus_current_profile') || null;
let currentDeckId = null;
let sortColumn = localStorage.getItem('tipikus_sort_column') || 'date';
let sortDirection = localStorage.getItem('tipikus_sort_direction') || 'desc';
let flashcardSession = { mots: [], index: 0, flipped: false, knownCount: 0, lastCountedIndex: -1 };

// Horodatage de début de la session "profil actif" en cours (pour le temps passé)
let profileSessionStart = null;

function loadLocal() {
  const raw = localStorage.getItem('tipikus_data');
  return raw ? JSON.parse(raw) : { profiles: [], decks: [], last_updated: 0 };
}
function saveLocal(s) {
  localStorage.setItem('tipikus_data', JSON.stringify(s));
}
function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

// ===== STATISTIQUES PAR PROFIL =====
function ensureProfileStats(profile) {
  if (!profile.stats) {
    profile.stats = { connexions: 0, temps_total_secondes: 0, cartes_vues: 0, daily: {} };
  }
  if (!profile.stats.daily) profile.stats.daily = {};
  return profile.stats;
}

function dateKey(d = new Date()) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

function ensureDailyEntry(profile, key) {
  const stats = ensureProfileStats(profile);
  if (!stats.daily[key]) stats.daily[key] = { connexions: 0, temps_secondes: 0 };
  return stats.daily[key];
}

function startProfileSession() {
  profileSessionStart = Date.now();
}

// Ajoute le temps écoulé depuis le dernier flush aux stats (globales + du jour)
// du profil actif, puis relance le chrono à partir de maintenant.
function flushProfileSessionTime() {
  if (!currentProfileId || !profileSessionStart) return;
  const elapsedSeconds = (Date.now() - profileSessionStart) / 1000;
  profileSessionStart = Date.now();
  if (elapsedSeconds <= 0) return;
  const profile = state.profiles.find(p => p.id === currentProfileId);
  if (profile) {
    ensureProfileStats(profile).temps_total_secondes += elapsedSeconds;
    ensureDailyEntry(profile, dateKey()).temps_secondes += elapsedSeconds;
  }
}

function formatDuration(totalSeconds) {
  const t = Math.round(totalSeconds || 0);
  const h = Math.floor(t / 3600);
  const m = Math.floor((t % 3600) / 60);
  const s = t % 60;
  if (h > 0) return `${h}h ${m}min`;
  if (m > 0) return `${m}min ${s}s`;
  return `${s}s`;
}

function renderKpiTable() {
  const tbody = document.getElementById('kpi-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  state.profiles.forEach(p => {
    const stats = p.stats || { connexions: 0, temps_total_secondes: 0, cartes_vues: 0 };
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${p.nom}</td>
      <td>${stats.connexions}</td>
      <td>${formatDuration(stats.temps_total_secondes)}</td>
      <td>${stats.cartes_vues}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ===== HEATMAPS D'ACTIVITE (style GitHub) =====
function buildHeatmap(profile) {
  const block = document.createElement('div');
  block.className = 'heatmap-block';

  const title = document.createElement('div');
  title.className = 'heatmap-title';
  title.textContent = profile.nom;
  block.appendChild(title);

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const DAYS_RANGE = 182; // ~ 6 mois
  const start = new Date(today);
  start.setDate(start.getDate() - (DAYS_RANGE - 1));
  start.setDate(start.getDate() - start.getDay()); // recule jusqu'au dimanche précédent

  const totalDays = Math.round((today - start) / 86400000) + 1;
  const weeks = Math.ceil(totalDays / 7);
  const daily = (profile.stats && profile.stats.daily) || {};

  const body = document.createElement('div');
  body.className = 'heatmap-body';

  // Labels des jours (Lun / Mer / Ven), une ligne vide entre chaque pour éviter la surcharge
  const dayLabels = document.createElement('div');
  dayLabels.className = 'heatmap-daylabels';
  ['', 'Lun', '', 'Mer', '', 'Ven', ''].forEach(name => {
    const span = document.createElement('span');
    span.textContent = name;
    dayLabels.appendChild(span);
  });
  body.appendChild(dayLabels);

  // Mois + grille dans un même conteneur scrollable pour qu'ils défilent ensemble
  const scroll = document.createElement('div');
  scroll.className = 'heatmap-scroll';

  const monthsRow = document.createElement('div');
  monthsRow.className = 'heatmap-months';

  const grid = document.createElement('div');
  grid.className = 'heatmap-grid';

  let prevMonth = -1;
  for (let col = 0; col < weeks; col++) {
    const colStartDate = new Date(start);
    colStartDate.setDate(start.getDate() + col * 7);

    const monthLabel = document.createElement('span');
    if (colStartDate.getMonth() !== prevMonth) {
      monthLabel.textContent = colStartDate.toLocaleDateString('fr-FR', { month: 'short' });
      prevMonth = colStartDate.getMonth();
    }
    monthsRow.appendChild(monthLabel);

    for (let row = 0; row < 7; row++) {
      const dayOffset = col * 7 + row;
      const cellDate = new Date(start);
      cellDate.setDate(start.getDate() + dayOffset);

      const cell = document.createElement('div');
      cell.className = 'heatmap-cell';

      if (cellDate > today) {
        cell.classList.add('future');
      } else {
        const key = dateKey(cellDate);
        const entry = daily[key];
        const connecte = entry && entry.connexions > 0;
        if (!connecte) {
          cell.classList.add('level-0');
        } else if (entry.temps_secondes >= 600) {
          cell.classList.add('level-2');
        } else {
          cell.classList.add('level-1');
        }
        const dateLabel = cellDate.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
        const dureeLabel = entry ? formatDuration(entry.temps_secondes) : '0s';
        cell.title = `${dateLabel} — ${dureeLabel}`;
      }
      grid.appendChild(cell);
    }
  }

  scroll.appendChild(monthsRow);
  scroll.appendChild(grid);
  body.appendChild(scroll);
  block.appendChild(body);

  return block;
}

function renderHeatmaps() {
  const container = document.getElementById('heatmaps-container');
  if (!container) return;
  container.innerHTML = '';
  state.profiles.forEach(p => {
    container.appendChild(buildHeatmap(p));
  });
}

// ===== SYNC =====
async function syncWithServer() {
  const local = loadLocal();
  try {
    const res = await fetch('/api/data', { cache: 'no-store' });
    if (!res.ok) throw new Error('offline');
    const server = await res.json();
    if (server.last_updated > local.last_updated) {
      state = server;
    } else {
      state = local;
      if (local.last_updated > 0) pushToServer(state, false);
    }
    setOnlineStatus(true);
  } catch (e) {
    state = local;
    setOnlineStatus(false);
  }
  saveLocal(state);
  render();
}

async function pushToServer(newState, updateTimestamp = true) {
  if (updateTimestamp) newState.last_updated = Date.now();
  saveLocal(newState);
  try {
    const res = await fetch('/api/data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newState)
    });
    if (!res.ok) throw new Error('fail');
    const data = await res.json();
    newState.last_updated = data.last_updated;
    saveLocal(newState);
    setOnlineStatus(true);
  } catch (e) {
    setOnlineStatus(false);
  }
}

function mutate(fn) {
  fn(state);
  pushToServer(state);
  render();
}

// Redirige vers la fonction de rendu de la vue actuellement affichée
function render() {
  if (!document.getElementById('view-profiles').classList.contains('hidden')) {
    renderProfiles();
  } else if (!document.getElementById('view-decks').classList.contains('hidden')) {
    renderDecks();
  } else if (!document.getElementById('view-deck-edit').classList.contains('hidden')) {
    renderDeckEdit();
  } else if (!document.getElementById('view-flashcards').classList.contains('hidden')) {
    renderFlashcard();
  }
}

function setOnlineStatus(online) {
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  dot.classList.toggle('offline', !online);
  text.textContent = online ? 'En ligne' : 'Hors ligne (données locales)';
}

window.addEventListener('online', syncWithServer);
window.addEventListener('offline', () => setOnlineStatus(false));

// Flush périodique pour ne pas perdre trop de temps en cas de fermeture brutale
setInterval(() => {
  if (profileSessionStart) {
    flushProfileSessionTime();
    pushToServer(state);
  }
}, 30000);

// L'app passe en arrière-plan : on fige le temps compté, on ignore la durée
// passée en arrière-plan quand on revient.
document.addEventListener('visibilitychange', () => {
  if (!currentProfileId) return;
  if (document.hidden) {
    flushProfileSessionTime();
    pushToServer(state);
  } else if (profileSessionStart) {
    profileSessionStart = Date.now();
  }
});

// Fermeture de l'onglet / rechargement : sauvegarde locale immédiate
window.addEventListener('pagehide', () => {
  if (profileSessionStart) {
    flushProfileSessionTime();
    state.last_updated = Date.now();
    saveLocal(state);
  }
});

// ===== NAVIGATION =====
function showView(id) {
  document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
}

// ===== VUE PROFILS =====
function renderProfiles() {
  const list = document.getElementById('profiles-list');
  list.innerHTML = '';
  state.profiles.forEach(p => {
    const div = document.createElement('div');
    div.className = 'card-item';
    const nbDecks = state.decks.filter(d => d.profile_id === p.id).length;
    div.innerHTML = `<div><strong>${p.nom}</strong><div class="meta">${nbDecks} deck(s)</div></div>`;
    div.onclick = () => selectProfile(p.id);
    const del = document.createElement('button');
    del.className = 'del-btn'; del.textContent = '🗑';
    del.onclick = (e) => { e.stopPropagation(); deleteProfile(p.id); };
    div.appendChild(del);
    list.appendChild(div);
  });
  renderKpiTable();
  renderHeatmaps();
}

function selectProfile(id) {
  currentProfileId = id;
  localStorage.setItem('tipikus_current_profile', id);
  startProfileSession();
  renderDecks();
  showView('view-decks');
}

function deleteProfile(id) {
  if (!confirm('Supprimer ce profil et tous ses decks ?')) return;
  mutate(s => {
    s.decks = s.decks.filter(d => d.profile_id !== id);
    s.profiles = s.profiles.filter(p => p.id !== id);
  });
}

// ===== VUE DECKS =====
function sortDecks(decks, column, direction) {
  const arr = [...decks];
  let cmp;
  switch (column) {
    case 'nom':
      cmp = (a, b) => a.nom.localeCompare(b.nom);
      break;
    case 'mots':
      cmp = (a, b) => a.mots.length - b.mots.length;
      break;
    case 'date':
    default:
      cmp = (a, b) => (a.created_at || 0) - (b.created_at || 0);
      break;
  }
  arr.sort(cmp);
  if (direction === 'desc') arr.reverse();
  return arr;
}

function formatDate(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

function updateSortHeaders() {
  document.querySelectorAll('#view-decks th[data-sort]').forEach(th => {
    const arrow = th.querySelector('.sort-arrow');
    if (th.dataset.sort === sortColumn) {
      arrow.textContent = sortDirection === 'asc' ? '▲' : '▼';
      th.classList.add('sorted');
    } else {
      arrow.textContent = '';
      th.classList.remove('sorted');
    }
  });
}

function deleteDeck(id) {
  if (!confirm('Supprimer ce deck ?')) return;
  mutate(s => { s.decks = s.decks.filter(d => d.id !== id); });
}

function renderDecks() {
  const profile = state.profiles.find(p => p.id === currentProfileId);
  document.getElementById('current-profile-name').textContent = profile ? profile.nom : 'Decks';

  updateSortHeaders();

  const tbody = document.getElementById('decks-tbody');
  tbody.innerHTML = '';
  const filtered = state.decks.filter(d => d.profile_id === currentProfileId);
  const sorted = sortDecks(filtered, sortColumn, sortDirection);

  sorted.forEach(d => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${d.nom}</td>
      <td>${formatDate(d.created_at)}</td>
      <td>${d.mots.length}</td>
      <td><button class="del-btn">🗑</button></td>
    `;
    tr.onclick = (e) => {
      if (e.target.closest('.del-btn')) return;
      openDeck(d.id);
    };
    tr.querySelector('.del-btn').onclick = (e) => {
      e.stopPropagation();
      deleteDeck(d.id);
    };
    tbody.appendChild(tr);
  });
}

document.querySelectorAll('#view-decks th[data-sort]').forEach(th => {
  th.onclick = () => {
    const col = th.dataset.sort;
    if (sortColumn === col) {
      sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      sortColumn = col;
      sortDirection = col === 'nom' ? 'asc' : 'desc';
    }
    localStorage.setItem('tipikus_sort_column', sortColumn);
    localStorage.setItem('tipikus_sort_direction', sortDirection);
    renderDecks();
  };
});

function openDeck(id) {
  currentDeckId = id;
  renderDeckEdit();
  showView('view-deck-edit');
}

// ===== VUE EDITION DECK =====
function renderDeckEdit() {
  const deck = state.decks.find(d => d.id === currentDeckId);
  document.getElementById('edit-deck-name').textContent = deck.nom;
  const list = document.getElementById('mots-list');
  list.innerHTML = '';
  deck.mots.forEach((m, i) => {
    const div = document.createElement('div');
    div.className = 'card-item';
    div.innerHTML = `<div><strong>${m.fr}</strong><div class="meta">${m.trad}</div></div>`;
    const del = document.createElement('button');
    del.className = 'del-btn'; del.textContent = '🗑';
    del.onclick = () => mutate(s => {
      const d = s.decks.find(dd => dd.id === currentDeckId);
      d.mots.splice(i, 1);
      renderDeckEdit();
    });
    div.appendChild(del);
    list.appendChild(div);
  });
}

document.getElementById('form-add-mot').onsubmit = (e) => {
  e.preventDefault();
  const fr = document.getElementById('input-mot-fr').value.trim();
  const trad = document.getElementById('input-mot-trad').value.trim();
  if (!fr || !trad) return;
  mutate(s => {
    const d = s.decks.find(dd => dd.id === currentDeckId);
    d.mots.push({ fr, trad });
  });
  document.getElementById('input-mot-fr').value = '';
  document.getElementById('input-mot-trad').value = '';
  renderDeckEdit();
};

document.getElementById('btn-delete-deck').onclick = () => {
  deleteDeck(currentDeckId);
  renderDecks();
  showView('view-decks');
};

// ===== FLASHCARDS =====
document.getElementById('btn-start-flashcards').onclick = () => {
  const deck = state.decks.find(d => d.id === currentDeckId);
  flashcardSession = {
    mots: [...deck.mots].sort(() => Math.random() - 0.5),
    index: 0,
    flipped: false,
    knownCount: 0,
    lastCountedIndex: -1
  };
  showView('view-flashcards');
  renderFlashcard();
};

function countCardAsSeen() {
  if (flashcardSession.index === flashcardSession.lastCountedIndex) return;
  if (flashcardSession.index >= flashcardSession.mots.length) return;
  flashcardSession.lastCountedIndex = flashcardSession.index;
  const profile = state.profiles.find(p => p.id === currentProfileId);
  if (profile) {
    ensureProfileStats(profile).cartes_vues += 1;
    pushToServer(state);
  }
}

function renderFlashcard() {
  const empty = document.getElementById('flashcard-empty');
  const zone = document.getElementById('flashcard-zone');
  const done = document.getElementById('flashcard-done');
  empty.classList.add('hidden'); zone.classList.add('hidden'); done.classList.add('hidden');

  if (flashcardSession.mots.length === 0) {
    empty.classList.remove('hidden');
    return;
  }
  if (flashcardSession.index >= flashcardSession.mots.length) {
    done.classList.remove('hidden');
    document.getElementById('flashcard-summary').textContent =
      `${flashcardSession.knownCount} / ${flashcardSession.mots.length} mots connus`;
    return;
  }
  zone.classList.remove('hidden');
  countCardAsSeen();
  const mot = flashcardSession.mots[flashcardSession.index];
  document.getElementById('flashcard-front').textContent = flashcardSession.flipped ? mot.trad : mot.fr;
  document.getElementById('flashcard-actions').classList.toggle('hidden', !flashcardSession.flipped);
  document.getElementById('flashcard-progress').textContent =
    `${flashcardSession.index + 1} / ${flashcardSession.mots.length}`;
}

document.getElementById('flashcard').onclick = () => {
  flashcardSession.flipped = !flashcardSession.flipped;
  renderFlashcard();
};

function nextCard(known) {
  if (known) flashcardSession.knownCount++;
  flashcardSession.index++;
  flashcardSession.flipped = false;
  renderFlashcard();
}
document.getElementById('btn-know-yes').onclick = () => nextCard(true);
document.getElementById('btn-know-no').onclick = () => nextCard(false);
document.getElementById('btn-restart-flashcards').onclick = () => {
  document.getElementById('btn-start-flashcards').click();
};

// ===== NAVIGATION BOUTONS =====
document.getElementById('btn-back-profiles').onclick = () => {
  flushProfileSessionTime();
  pushToServer(state);
  profileSessionStart = null;
  renderProfiles();
  showView('view-profiles');
};
document.getElementById('btn-switch-profile').onclick = () => {
  flushProfileSessionTime();
  pushToServer(state);
  profileSessionStart = null;
  renderProfiles();
  showView('view-profiles');
};
document.getElementById('btn-back-decks').onclick = () => { renderDecks(); showView('view-decks'); };
document.getElementById('btn-back-deck-edit').onclick = () => { renderDeckEdit(); showView('view-deck-edit'); };

// ===== MODALE (nouveau profil / nouveau deck) =====
let modalMode = null;
function openModal(mode) {
  modalMode = mode;
  const overlay = document.getElementById('modal-overlay');
  document.getElementById('modal-input').value = '';
  if (mode === 'profile') {
    document.getElementById('modal-title').textContent = 'Nouveau profil';
    document.getElementById('modal-input').placeholder = 'Nom du profil';
  } else if (mode === 'deck') {
    document.getElementById('modal-title').textContent = 'Nouveau deck';
    document.getElementById('modal-input').placeholder = 'Nom du deck';
  }
  overlay.classList.remove('hidden');
}
document.getElementById('btn-new-profile').onclick = () => openModal('profile');
document.getElementById('btn-new-deck').onclick = () => openModal('deck');
document.getElementById('modal-cancel').onclick = () => document.getElementById('modal-overlay').classList.add('hidden');
document.getElementById('modal-confirm').onclick = () => {
  const val = document.getElementById('modal-input').value.trim();
  if (!val) return;
  if (modalMode === 'profile') {
    mutate(s => s.profiles.push({ id: uid(), nom: val, stats: { connexions: 0, temps_total_secondes: 0, cartes_vues: 0 } }));
    renderProfiles();
  } else if (modalMode === 'deck') {
    mutate(s => s.decks.push({ id: uid(), profile_id: currentProfileId, nom: val, created_at: Date.now(), mots: [] }));
    renderDecks();
  }
  document.getElementById('modal-overlay').classList.add('hidden');
};

// ===== INIT =====
async function init() {
  await syncWithServer();
  renderProfiles();

  if (currentProfileId && state.profiles.find(p => p.id === currentProfileId)) {
    // L'app démarre/recharge alors qu'un profil était déjà actif : ça compte
    // comme une connexion, et le chrono de temps passé redémarre.
    const profile = state.profiles.find(p => p.id === currentProfileId);
    ensureProfileStats(profile).connexions += 1;
    ensureDailyEntry(profile, dateKey()).connexions += 1;
    pushToServer(state);
    startProfileSession();
    renderDecks();
    showView('view-decks');
  } else {
    showView('view-profiles');
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js').catch(console.error);
  }
}
init();