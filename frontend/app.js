// MeetingNote 화면 스크립트. 상태는 모듈 변수에 두고 DOM 을 직접 갱신한다 (03-design 6행)
'use strict';

// ---------- 상수 ----------
const MAX_UPLOAD_BYTES = 25 * 1024 * 1024; // 02-specs 9절
const AUDIO_EXTENSIONS = ['.mp3', '.wav'];
const THEME_KEY = 'theme';
const DELETE_CONFIRM_MS = 4000;

// 탭 버튼 · 결과 칸 등에서 함께 쓰는 클래스 묶음
const TAB_ACTIVE = ['bg-white', 'shadow-sm', 'text-zinc-900', 'dark:bg-zinc-600', 'dark:text-white'];
const TAB_IDLE = ['text-zinc-500', 'hover:text-zinc-800', 'dark:text-zinc-400', 'dark:hover:text-zinc-200'];
const DELETE_IDLE = ['bg-white', 'text-red-600', 'ring-black/10', 'hover:bg-red-50', 'dark:bg-zinc-800', 'dark:text-red-400', 'dark:ring-white/10', 'dark:hover:bg-red-950/40'];
const DELETE_ARMED = ['bg-red-600', 'text-white', 'ring-red-600', 'hover:bg-red-700'];
const MUTED = 'text-zinc-500 dark:text-zinc-400';
const ERROR = 'text-red-600 dark:text-red-400';
const SUCCESS = 'text-green-600 dark:text-green-400';

// ---------- 상태 ----------
let currentView = 'notes';
let currentNote = null; // 상세 창에 열린 회의록 (body 포함)
let notesRequestSeq = 0; // 검색을 빠르게 칠 때 늦게 온 옛 응답을 버리기 위한 번호
let deleteArmed = false;
let deleteTimer = null;

// ---------- 요소 ----------
const $ = (id) => document.getElementById(id);
const el = {
  q: $('q'), from: $('from'), to: $('to'), cards: $('cards'), notesStatus: $('notesStatus'),
  createForm: $('createForm'), title: $('title'), metAt: $('metAt'), attendees: $('attendees'),
  file: $('file'), body: $('body'), btnUp: $('btnUp'), upStatus: $('upStatus'),
  btnSave: $('btnSave'), saveStatus: $('saveStatus'), result: $('result'),
  todoBody: $('todoBody'),
  modal: $('modal'), mHeading: $('mHeading'), mMeta: $('mMeta'), btnClose: $('btnClose'),
  mSummary: $('mSummary'), mDecisions: $('mDecisions'), mTodos: $('mTodos'),
  mBodyWrap: $('mBodyWrap'), mBody: $('mBody'), mTitle: $('mTitle'),
  btnRename: $('btnRename'), btnDelete: $('btnDelete'), mStatus: $('mStatus'),
  btnTheme: $('btnTheme'),
};

// ---------- 공통 도우미 ----------

// 요소를 만든다. 서버 글은 textContent 로만 넣어 XSS 를 막는다
function h(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function setStatus(node, message, tone) {
  node.textContent = message || '';
  node.className = node.className.split(' ').filter((c) => !/^(dark:)?text-(zinc|red|green)-/.test(c)).join(' ');
  node.classList.add(...(tone || MUTED).split(' '));
}

// API 실패를 상태 코드와 함께 던진다
class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (err) {
    throw new ApiError(0, '서버에 연결할 수 없어요. 서버가 켜져 있는지 확인해 주세요.');
  }
  if (!response.ok) throw new ApiError(response.status, `요청 실패 (${response.status})`);
  if (response.status === 204) return null;
  return response.json();
}

function jsonOptions(method, payload) {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) };
}

// 줄바꿈으로 나뉜 세 갈래 값을 줄 배열로
function splitLines(text) {
  return (text || '').split('\n').map((line) => line.trim()).filter(Boolean);
}

// 할 일 한 줄 「내용 | 담당자 | 기한」 을 나눈다
function parseTodo(line) {
  const [what = '', who = '', when = ''] = line.split('|').map((part) => part.trim());
  return { what, who, when };
}

// ---------- 시각 변환 (02-specs 3절) ----------

const pad = (n) => String(n).padStart(2, '0');

// datetime-local 값(로컬) → UTC ISO
function localInputToUtcIso(value) {
  return new Date(value).toISOString();
}

// Date → datetime-local 값 (로컬)
function toLocalInputValue(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// 서버 UTC ISO → 로컬 표시 "2026-11-12 16:00"
function formatLocal(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso || '';
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function metaLine(note) {
  const attendees = (note.attendees || '').trim();
  return attendees ? `${formatLocal(note.met_at)} · ${attendees}` : formatLocal(note.met_at);
}

// ---------- 테마 ----------

function readSavedTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch (err) {
    return null;
  }
}

function applyTheme(isDark) {
  document.documentElement.classList.toggle('dark', isDark);
  el.btnTheme.setAttribute('aria-pressed', String(isDark));
}

function toggleTheme() {
  const isDark = !document.documentElement.classList.contains('dark');
  applyTheme(isDark);
  try {
    localStorage.setItem(THEME_KEY, isDark ? 'dark' : 'light');
  } catch (err) {
    // 저장소를 못 쓰는 환경이면 이번 화면에서만 바꾼다
  }
}

function initTheme() {
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  const saved = readSavedTheme();
  applyTheme(saved ? saved === 'dark' : media.matches);
  // 직접 고른 적이 없으면 시스템 설정 변경을 따라간다
  media.addEventListener('change', (event) => {
    if (!readSavedTheme()) applyTheme(event.matches);
  });
  el.btnTheme.addEventListener('click', toggleTheme);
}

// ---------- 탭 ----------

function showView(view) {
  currentView = view;
  document.querySelectorAll('[data-view-panel]').forEach((panel) => {
    panel.classList.toggle('hidden', panel.dataset.viewPanel !== view);
  });
  document.querySelectorAll('.tab').forEach((tab) => {
    const active = tab.dataset.view === view;
    tab.classList.remove(...(active ? TAB_IDLE : TAB_ACTIVE));
    tab.classList.add(...(active ? TAB_ACTIVE : TAB_IDLE));
    tab.setAttribute('aria-current', active ? 'page' : 'false');
  });
  if (view === 'notes') loadNotes();
  if (view === 'todos') loadTodos();
  if (view === 'create' && !el.metAt.value) el.metAt.value = toLocalInputValue(new Date());
}

// ---------- 화면 1: 목록 ----------

function buildNotesQuery() {
  const params = new URLSearchParams();
  const q = el.q.value.trim();
  if (q) params.set('q', q);
  if (el.from.value) params.set('from', el.from.value);
  if (el.to.value) params.set('to', el.to.value);
  const query = params.toString();
  return query ? `/api/notes?${query}` : '/api/notes';
}

async function loadNotes() {
  const seq = ++notesRequestSeq;
  try {
    const notes = await api(buildNotesQuery());
    if (seq !== notesRequestSeq) return;
    renderCards(notes);
  } catch (err) {
    if (seq !== notesRequestSeq) return;
    el.cards.replaceChildren();
    showNotesStatus(err.status === 400 ? '날짜 형식을 확인해 주세요.' : err.message, ERROR);
  }
}

function showNotesStatus(message, tone) {
  el.notesStatus.classList.toggle('hidden', !message);
  setStatus(el.notesStatus, message, tone);
}

function renderCards(notes) {
  const searching = Boolean(el.q.value.trim() || el.from.value || el.to.value);
  if (!notes.length) {
    el.cards.replaceChildren();
    showNotesStatus(searching ? '검색 결과가 없어요.' : '아직 회의록이 없어요. 「넣기」에서 첫 회의록을 만들어 보세요.');
    return;
  }
  showNotesStatus('');
  el.cards.replaceChildren(...notes.map(buildCard));
}

function buildCard(note) {
  const card = h('button', 'group min-w-0 rounded-2xl bg-white/70 p-4 text-left shadow-sm ring-1 ring-black/5 backdrop-blur-xl transition hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus-visible:ring-4 focus-visible:ring-accent/30 dark:bg-white/5 dark:ring-white/10 dark:hover:bg-white/10');
  card.type = 'button';
  card.dataset.id = String(note.id);
  card.append(
    h('h3', 'break-words font-semibold tracking-tight', note.title),
    h('p', `mt-1 break-words text-sm ${MUTED}`, metaLine(note)),
  );
  const firstLine = splitLines(note.summary)[0];
  card.append(h('p', `mt-2 line-clamp-2 break-words text-sm ${firstLine ? 'text-zinc-700 dark:text-zinc-300' : 'italic text-zinc-400'}`, firstLine || '요약 없음'));
  card.addEventListener('click', () => openModal(note.id));
  return card;
}

// ---------- 화면 2: 넣기 ----------

function fileExtension(name) {
  const dot = name.lastIndexOf('.');
  return dot < 0 ? '' : name.slice(dot).toLowerCase();
}

// 업로드 실패 코드를 사용자 말로 바꾼다
function uploadErrorMessage(status) {
  switch (status) {
    case 415: return 'mp3 또는 wav 파일만 받아쓸 수 있어요.';
    case 413: return '25MB 이하 파일만 올릴 수 있어요.';
    case 502: return '받아쓰기 서비스가 응답하지 않았어요. 잠시 뒤 다시 시도해 주세요.';
    case 0: return '서버에 연결할 수 없어요. 서버가 켜져 있는지 확인해 주세요.';
    default: return `받아쓰기에 실패했어요. (오류 ${status})`;
  }
}

async function uploadAudio() {
  const file = el.file.files[0];
  if (!file) {
    setStatus(el.upStatus, '먼저 녹취 파일을 골라 주세요.', ERROR);
    return;
  }
  // 서버에 보내기 전에 형식 · 크기를 먼저 본다
  if (!AUDIO_EXTENSIONS.includes(fileExtension(file.name))) {
    setStatus(el.upStatus, uploadErrorMessage(415), ERROR);
    return;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    setStatus(el.upStatus, uploadErrorMessage(413), ERROR);
    return;
  }

  const form = new FormData();
  form.append('file', file);
  el.btnUp.disabled = true;
  setStatus(el.upStatus, '받아쓰는 중이에요… 파일 길이에 따라 시간이 걸릴 수 있어요.');
  try {
    const data = await api('/api/upload', { method: 'POST', body: form });
    el.body.value = data.text || '';
    setStatus(el.upStatus, data.text ? '받아쓰기를 마쳤어요. 본문을 확인한 뒤 「정리하기」를 눌러 주세요.' : '받아쓴 내용이 비어 있어요.', data.text ? SUCCESS : ERROR);
  } catch (err) {
    setStatus(el.upStatus, uploadErrorMessage(err.status), ERROR);
  } finally {
    el.btnUp.disabled = false;
  }
}

async function saveNote(event) {
  event.preventDefault();
  const title = el.title.value.trim();
  const body = el.body.value.trim();
  const missing = [];
  if (!title) missing.push('제목');
  if (!el.metAt.value) missing.push('일시');
  if (!body) missing.push('본문');
  if (missing.length) {
    setStatus(el.saveStatus, `${missing.join(' · ')}을(를) 채워 주세요.`, ERROR);
    return;
  }

  const payload = {
    title,
    met_at: localInputToUtcIso(el.metAt.value),
    attendees: el.attendees.value.trim(),
    body,
  };
  el.btnSave.disabled = true;
  setStatus(el.saveStatus, '정리하는 중이에요…');
  try {
    const note = await api('/api/notes', jsonOptions('POST', payload));
    renderResult(note);
    setStatus(el.saveStatus, '저장했어요. 「목록」에서 다시 볼 수 있어요.', SUCCESS);
    // 같은 내용을 두 번 저장하지 않게 폼을 비운다 (일시는 둔다)
    el.title.value = '';
    el.attendees.value = '';
    el.body.value = '';
    el.file.value = '';
    setStatus(el.upStatus, '');
  } catch (err) {
    const message = err.status === 400 ? '입력값을 확인해 주세요. 제목 · 일시 · 본문은 꼭 필요해요.' : err.status ? `저장하지 못했어요. (오류 ${err.status})` : err.message;
    setStatus(el.saveStatus, message, ERROR);
  } finally {
    el.btnSave.disabled = false;
  }
}

// 한 칸(요약 · 결정사항 · 할 일)을 만든다
function buildResultBox(label, hint, items) {
  const box = h('section', 'min-w-0 rounded-2xl bg-white/70 p-4 shadow-sm ring-1 ring-black/5 backdrop-blur-xl dark:bg-white/5 dark:ring-white/10');
  const head = h('div', 'mb-2 flex items-baseline justify-between gap-2');
  head.append(h('h3', 'font-semibold tracking-tight', label), h('span', 'text-xs text-zinc-400', hint));
  box.append(head);
  if (items === null) {
    box.append(h('p', 'text-sm text-zinc-400', '정리하면 여기에 표시돼요.'));
  } else if (!items.length) {
    box.append(h('p', 'text-sm text-zinc-400', '없음'));
  } else {
    const list = h('ul', 'space-y-1.5 text-sm');
    items.forEach((item) => list.append(item));
    box.append(list);
  }
  return box;
}

function textItems(text) {
  return splitLines(text).map((line) => {
    const li = h('li', 'flex gap-2 break-words');
    li.append(h('span', 'select-none text-zinc-400', '•'), h('span', 'min-w-0', line));
    return li;
  });
}

function todoItems(text) {
  return splitLines(text).map((line) => {
    const todo = parseTodo(line);
    const li = h('li', 'flex gap-2 break-words');
    const content = h('span', 'min-w-0');
    content.append(h('span', '', todo.what));
    const extra = [todo.who, todo.when].filter(Boolean).join(' · ');
    if (extra) content.append(h('span', `ml-1 text-xs ${MUTED}`, `(${extra})`));
    li.append(h('span', 'select-none text-zinc-400', '☐'), content);
    return li;
  });
}

// note 가 null 이면 빈 세 칸을 보인다
function renderResult(note) {
  const boxes = h('div', 'grid grid-cols-1 gap-3 md:grid-cols-3');
  const failed = note && !splitLines(note.summary).length && !splitLines(note.decisions).length && !splitLines(note.todos).length;
  boxes.append(
    buildResultBox('요약', '3~5줄', note ? textItems(note.summary) : null),
    buildResultBox('결정사항', '합의가 끝난 것만', note ? textItems(note.decisions) : null),
    buildResultBox('할 일', '담당자 · 기한 포함', note ? todoItems(note.todos) : null),
  );
  const nodes = [];
  // 02-specs 7절: 세 칸이 모두 비면 구분 실패로 표시한다
  if (failed) {
    const banner = h('div', 'mb-3 rounded-xl bg-amber-100/80 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-300/60 dark:bg-amber-900/30 dark:text-amber-200 dark:ring-amber-700/50');
    banner.append(h('strong', 'font-semibold', '구분 실패'), document.createTextNode(' - 본문은 저장됐지만 요약 · 결정사항 · 할 일로 나누지 못했어요. 본문이 너무 짧거나 회의 내용이 아닐 수 있어요.'));
    nodes.push(banner);
  }
  nodes.push(boxes);
  el.result.replaceChildren(...nodes);
}

// ---------- 화면 3: 상세 창 ----------

function fillList(list, items, emptyText) {
  list.replaceChildren(...(items.length ? items : [h('li', 'text-sm text-zinc-400', emptyText)]));
}

function renderModal(note) {
  el.mHeading.textContent = note.title;
  el.mMeta.textContent = metaLine(note);
  const failed = !splitLines(note.summary).length && !splitLines(note.decisions).length && !splitLines(note.todos).length;
  const emptyText = failed ? '구분 실패' : '없음';
  fillList(el.mSummary, textItems(note.summary), emptyText);
  fillList(el.mDecisions, textItems(note.decisions), emptyText);
  fillList(el.mTodos, todoItems(note.todos), emptyText);
  el.mBody.textContent = note.body || '';
  el.mTitle.value = note.title;
}

async function openModal(id) {
  resetDeleteButton();
  setStatus(el.mStatus, '');
  el.mBodyWrap.open = false;
  try {
    currentNote = await api(`/api/notes/${encodeURIComponent(id)}`);
  } catch (err) {
    currentNote = null;
    if (err.status === 404) {
      showNotesStatus('이미 삭제된 회의록이에요.', ERROR);
      refreshCurrentView();
    } else {
      showNotesStatus(err.message, ERROR);
    }
    return;
  }
  renderModal(currentNote);
  el.modal.classList.remove('hidden');
  el.modal.classList.add('flex');
  document.body.classList.add('overflow-hidden');
  el.btnClose.focus();
}

function closeModal() {
  el.modal.classList.add('hidden');
  el.modal.classList.remove('flex');
  document.body.classList.remove('overflow-hidden');
  currentNote = null;
  resetDeleteButton();
}

function isModalOpen() {
  return !el.modal.classList.contains('hidden');
}

async function renameNote() {
  if (!currentNote) return;
  const title = el.mTitle.value.trim();
  if (!title) {
    setStatus(el.mStatus, '제목을 입력해 주세요.', ERROR);
    return;
  }
  if (title === currentNote.title) {
    setStatus(el.mStatus, '바뀐 내용이 없어요.');
    return;
  }
  // PUT 은 전 필드를 받으므로 나머지는 그대로 보낸다 (02-specs 9절)
  const payload = { title, met_at: currentNote.met_at, attendees: currentNote.attendees || '', body: currentNote.body };
  el.btnRename.disabled = true;
  try {
    currentNote = await api(`/api/notes/${currentNote.id}`, jsonOptions('PUT', payload));
    renderModal(currentNote);
    setStatus(el.mStatus, '제목을 고쳤어요.', SUCCESS);
    refreshCurrentView();
  } catch (err) {
    setStatus(el.mStatus, err.status === 404 ? '이미 삭제된 회의록이에요.' : `고치지 못했어요. (${err.status || err.message})`, ERROR);
  } finally {
    el.btnRename.disabled = false;
  }
}

function resetDeleteButton() {
  deleteArmed = false;
  clearTimeout(deleteTimer);
  el.btnDelete.textContent = '삭제';
  el.btnDelete.classList.remove(...DELETE_ARMED);
  el.btnDelete.classList.add(...DELETE_IDLE);
}

// 삭제는 두 번 눌러야 한다. 첫 번째는 확인 상태로만 바꾼다
async function deleteNote() {
  if (!currentNote) return;
  if (!deleteArmed) {
    deleteArmed = true;
    el.btnDelete.textContent = '한 번 더 누르면 삭제';
    el.btnDelete.classList.remove(...DELETE_IDLE);
    el.btnDelete.classList.add(...DELETE_ARMED);
    deleteTimer = setTimeout(resetDeleteButton, DELETE_CONFIRM_MS);
    return;
  }
  clearTimeout(deleteTimer);
  el.btnDelete.disabled = true;
  try {
    await api(`/api/notes/${currentNote.id}`, { method: 'DELETE' });
    closeModal();
    refreshCurrentView();
  } catch (err) {
    if (err.status === 404) {
      closeModal();
      refreshCurrentView();
    } else {
      setStatus(el.mStatus, `삭제하지 못했어요. (${err.status || err.message})`, ERROR);
      resetDeleteButton();
    }
  } finally {
    el.btnDelete.disabled = false;
  }
}

// ---------- 화면 4: 할 일 ----------

function todoMessageRow(message, tone) {
  const tr = h('tr');
  const td = h('td', `px-4 py-8 text-center ${tone || MUTED}`, message);
  td.colSpan = 4;
  tr.append(td);
  return tr;
}

async function loadTodos() {
  try {
    const todos = await api('/api/todos');
    if (!todos.length) {
      el.todoBody.replaceChildren(todoMessageRow('할 일이 없어요.'));
      return;
    }
    el.todoBody.replaceChildren(...todos.map(buildTodoRow));
  } catch (err) {
    el.todoBody.replaceChildren(todoMessageRow(err.status ? `할 일을 불러오지 못했어요. (오류 ${err.status})` : err.message, ERROR));
  }
}

function buildTodoRow(todo) {
  const tr = h('tr', 'align-top transition hover:bg-black/[0.02] dark:hover:bg-white/5');
  tr.append(
    h('td', 'px-4 py-3', todo.what),
    h('td', 'whitespace-nowrap px-4 py-3', todo.who),
    h('td', 'whitespace-nowrap px-4 py-3', todo.when),
  );
  // 회의 이름을 누르면 그 회의 상세 창을 연다
  const meetingCell = h('td', 'px-4 py-3');
  const link = h('button', 'text-left text-accent hover:underline dark:text-accent-dark', todo.note_title);
  link.type = 'button';
  link.addEventListener('click', () => openModal(todo.note_id));
  meetingCell.append(link);
  tr.append(meetingCell);
  return tr;
}

function refreshCurrentView() {
  if (currentView === 'notes') loadNotes();
  if (currentView === 'todos') loadTodos();
}

// ---------- 시작 ----------

function bindEvents() {
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => showView(tab.dataset.view));
  });
  // 검색은 입력할 때마다 다시 부른다
  [el.q, el.from, el.to].forEach((input) => input.addEventListener('input', loadNotes));
  el.btnUp.addEventListener('click', uploadAudio);
  el.file.addEventListener('change', () => setStatus(el.upStatus, el.file.files[0] ? `${el.file.files[0].name} - 「받아쓰기」를 눌러 주세요.` : ''));
  el.createForm.addEventListener('submit', saveNote);
  el.btnClose.addEventListener('click', closeModal);
  // 어두운 바깥(겹침 창 자신)을 누를 때만 닫는다
  el.modal.addEventListener('click', (event) => {
    if (event.target === el.modal) closeModal();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isModalOpen()) closeModal();
  });
  el.btnRename.addEventListener('click', renameNote);
  el.mTitle.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') renameNote();
  });
  el.btnDelete.addEventListener('click', deleteNote);
}

initTheme();
bindEvents();
renderResult(null);
resetDeleteButton();
showView('notes');
