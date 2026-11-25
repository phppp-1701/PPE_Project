/* ==========================================================================
   PPE MONITOR — MODULE 1: GIÁM SÁT TRỰC TIẾP & TRUNG TÂM PHÁT HIỆN (ADMIN)
   Đa camera: người dùng tick chọn camera nào được theo dõi, mỗi camera một tile.
   ========================================================================== */

import {
  API_BASE,
  PPE_KEYS,
  PPE_META,
  apiGet,
  apiSend,
  fmtSeconds,
  fmtTimeShort,
  hasDesktopBridge,
  playAlertBeep,
  showToast,
} from './api.js';

export const monitorState = {
  sourceMode: 'camera',          // 'camera' | 'file' (chế độ nguồn đang hiển thị trên thanh công cụ)
  selectedFilePath: '',
  playbackMode: 'realtime',
  liveStatuses: [],              // trạng thái mọi nguồn từ /api/live/statuses
  selectedCameras: new Set(),    // source_id người dùng tick chọn theo dõi
  focusedSourceId: null,         // tile đang được xem trong Inspector
  tileSessions: {},              // source_id -> session_id đã gán vào img.src
  catalog: [],                   // danh mục camera từ /api/cameras
  maxParallel: 4,
  liveSourceId: 'cam0',          // nguồn đang focus (quick policy áp vào nguồn này)
  liveSessionId: undefined,      // phiên của nguồn đang focus (tương thích events.js cũ)
  activeSessionIds: new Set(),   // mọi phiên đang chạy (bộ lọc "live" của Nhật ký vi phạm)
  seenEventIds: new Set(),
  initialEventsLoaded: false,
  soundEnabled: false,
  presets: [],
};

const LIVE_STATE_LABELS = {
  idle: 'Đang dừng',
  starting: 'Đang nạp mô hình…',
  running: 'Đang giám sát',
  stopping: 'Đang dừng…',
  error: 'Lỗi nguồn phát',
};

// Màu phân biệt từng camera (xưởng nhiều khu — nhìn vô biết ngay khu nào):
// ghép ổn định theo source_id, cùng một cam luôn cùng màu ở mọi nơi (tile, feed, thống kê)
const SOURCE_PALETTE = ['#38bdf8', '#f97316', '#4ade80', '#a855f7', '#f472b6', '#facc15', '#2dd4bf', '#fb7185'];

export function sourceColor(sourceId) {
  let h = 0;
  for (const ch of String(sourceId)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return SOURCE_PALETTE[h % SOURCE_PALETTE.length];
}

function tileDomId(sourceId) {
  return String(sourceId).replace(/[^a-zA-Z0-9_-]/g, '_');
}

function sourceName(sourceId) {
  const item = monitorState.catalog.find((c) => c.source_id === sourceId);
  return item ? item.name : sourceId;
}

export async function initMonitorModule() {
  await loadCamerasList();

  // Đóng ngăn thả xuống (chọn camera / quy định nhanh) khi bấm ra ngoài
  document.addEventListener('click', (e) => {
    for (const wrapId of ['quick-policy-wrap', 'mon-camera-picker-wrap']) {
      const wrap = document.getElementById(wrapId);
      const drawer = wrap ? wrap.querySelector('.quick-policy-drawer') : null;
      if (wrap && drawer && drawer.classList.contains('open') && !wrap.contains(e.target)) {
        drawer.classList.remove('open');
      }
    }
  });

  // Ngăn chọn camera đang mở thì tự làm mới mỗi 6s: laptop khác bật laptop_cam_server
  // trong WiFi là camera mới tự xuất hiện trong danh sách, không cần bấm gì
  setInterval(() => {
    const picker = document.getElementById('mon-camera-picker');
    if (picker && picker.classList.contains('open')) {
      loadCamerasList();
    }
  }, 6000);
}

export async function loadCamerasList() {
  try {
    const data = await apiGet('/api/cameras');
    monitorState.catalog = data.catalog || [];
    monitorState.maxParallel = data.max_parallel || 4;
    const setCamSel = document.getElementById('set-camera-index');
    if (setCamSel) {
      setCamSel.innerHTML = (data.cameras || [])
        .map((c) => `<option value="${c.index}">Webcam ${c.index} (${c.width}x${c.height})</option>`)
        .join('');
      setCamSel.value = String(data.default_index ?? 0);
    }
    renderDiscoveredList(data.discovered || []);
    renderCameraPicker();
  } catch (err) {
    console.error('Lỗi tải danh mục camera:', err);
  }
}

function renderCameraPicker() {
  const list = document.getElementById('mon-camera-list');
  const note = document.getElementById('mon-camera-note');
  const summary = document.getElementById('mon-camera-summary');
  if (!list) return;

  if (!monitorState.catalog.length) {
    list.innerHTML = `<div class="dock-empty">Không tìm thấy camera nào.</div>`;
    if (summary) summary.textContent = 'Chọn camera: 0/0';
    return;
  }

  list.innerHTML = monitorState.catalog
    .map((c) => {
      const running = c.in_use;
      const checked = running || monitorState.selectedCameras.has(c.source_id);
      if (running) monitorState.selectedCameras.add(c.source_id);
      const color = sourceColor(c.source_id);
      return `
        <label class="camera-check-row ${running ? 'in-use' : ''}">
          <input type="checkbox" ${checked ? 'checked' : ''}
                 onchange="window.onCameraCheckChange('${c.source_id}', this.checked)">
          <span class="cam-color-dot" style="background:${color}"></span>
          <span class="camera-check-name">${c.name}</span>
          <button class="btn btn-sm" title="Đặt tên khu vực cho camera này"
                  onclick="event.preventDefault(); window.renameSourcePrompt('${c.source_id}')">✎</button>
          ${running ? '<span class="badge badge-ok">Đang chạy</span>' : ''}
        </label>
      `;
    })
    .join('');

  const runningCount = monitorState.catalog.filter((c) => c.in_use).length;
  if (note) {
    note.textContent = `Tối đa ${monitorState.maxParallel} camera chạy pipeline đồng thời · đang chạy ${runningCount}`;
  }
  if (summary) {
    summary.textContent = `Chọn camera: ${monitorState.selectedCameras.size}/${monitorState.catalog.length}`;
  }
}

export function onCameraCheckChange(sourceId, checked) {
  if (checked) {
    monitorState.selectedCameras.add(sourceId);
  } else {
    monitorState.selectedCameras.delete(sourceId);
  }
  const summary = document.getElementById('mon-camera-summary');
  if (summary) {
    summary.textContent = `Chọn camera: ${monitorState.selectedCameras.size}/${monitorState.catalog.length}`;
  }
}

export async function renameSourcePrompt(sourceId) {
  const current = sourceName(sourceId);
  const name = window.prompt(`Đặt tên khu vực cho ${sourceId}\n(ví dụ: Khu hàn, Khu sơn, Cổng vào…):`, current);
  if (!name || !name.trim() || name.trim() === current) return;
  try {
    await apiSend(`/api/sources/${encodeURIComponent(sourceId)}/name`, 'PUT', { name: name.trim() });
    showToast(`Đã đặt tên khu vực: "${name.trim()}" (${sourceId}).`, 'ok');
    await loadCamerasList();
    await pollLive();
  } catch (err) {
    showToast(`Không đổi được tên: ${err.message}`, 'danger');
  }
}

export async function openEvidenceFolder() {
  // mở thư mục lưu ảnh minh chứng (desktop: qua pywebview bridge; web: hiện đường dẫn)
  try {
    const data = await apiGet('/api/evidence/path');
    const p = data.path;
    if (hasDesktopBridge() && typeof window.pywebview.api.open_folder === 'function') {
      await window.pywebview.api.open_folder(p);
      return;
    }
    showToast(`Thư mục minh chứng: ${p}`, 'info');
  } catch (err) {
    showToast(`Không mở được thư mục: ${err.message}`, 'danger');
  }
}

export function openDatePicker(inputEl) {
  // mở lịch chọn ngày bằng 1 click thay vì phải gõ tay (Chromium/WebView2 hỗ trợ showPicker)
  try {
    if (inputEl && typeof inputEl.showPicker === 'function') {
      inputEl.showPicker();
    }
  } catch (_) {
    // trình duyệt không hỗ trợ hoặc cần tương tác người dùng trước — cứ để input tự xử
  }
}

function renderDiscoveredList(cams) {
  const list = document.getElementById('mon-discovered-list');
  if (!list) return;
  if (!cams.length) {
    list.innerHTML = `<div class="dock-empty">Chưa thấy camera LAN nào quảng cáo. Laptop khác chạy laptop_cam_server sẽ tự xuất hiện ở đây trong vài giây.</div>`;
    return;
  }
  list.innerHTML = cams
    .map((c) => `
      <div class="camera-check-row">
        <span class="camera-check-name" title="${c.url}">${c.name} <span class="mono" style="color:var(--text-muted);font-size:10px;">${c.host}</span></span>
        <button class="btn btn-sm" onclick="window.addDiscoveredCam('${encodeURIComponent(c.url)}', '${encodeURIComponent(c.name)}')">Thêm</button>
      </div>
    `)
    .join('');
}

export async function discoverLanCams() {
  const btn = document.getElementById('mon-discover-btn');
  const list = document.getElementById('mon-discovered-list');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Đang quét 3 giây…';
  }
  // listener UDP chạy nền liên tục — chờ 3 giây cho các gói quảng cáo kịp tới
  await new Promise((r) => setTimeout(r, 3000));
  try {
    const data = await apiGet('/api/cameras/discovered');
    const cams = data.discovered || [];
    if (!list) return;
    if (!cams.length) {
      list.innerHTML = `<div class="dock-empty">Không thấy camera nào trong mạng LAN. Camera phải đang chạy laptop_cam_server (hoặc app phát stream tương tự) mới được nhìn thấy.</div>`;
      return;
    }
    renderDiscoveredList(cams);
  } catch (err) {
    if (list) list.innerHTML = `<div class="dock-empty">Lỗi quét: ${err.message}</div>`;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="13" height="13"><path d="M21 21l-4.35-4.35"></path><circle cx="11" cy="11" r="8"></circle></svg>
        Quét camera trong mạng`;
    }
  }
}

export async function addDiscoveredCam(urlEncoded, nameEncoded) {
  const url = decodeURIComponent(urlEncoded);
  const name = decodeURIComponent(nameEncoded);
  await addCameraUrlByName(name, url);
}

export async function addCameraUrl() {
  const nameInput = document.getElementById('cam-url-name');
  const urlInput = document.getElementById('cam-url-value');
  const note = document.getElementById('cam-url-note');
  const name = (nameInput?.value || '').trim() || 'Camera ngoài';
  const url = (urlInput?.value || '').trim();
  if (!url) {
    if (note) note.textContent = 'Chưa nhập URL stream.';
    return;
  }
  await addCameraUrlByName(name, url, note);
  if (urlInput) urlInput.value = '';
}

async function addCameraUrlByName(name, url, noteEl) {
  try {
    const data = await apiSend('/api/cameras/url', 'POST', { name, url });
    showToast(data.existed
      ? `Camera "${data.name}" đã có sẵn trong danh sách.`
      : `Đã thêm camera "${data.name}" (${data.source_id}) vào danh sách chọn.`, 'ok');
    await loadCamerasList();
  } catch (err) {
    showToast(`Không thêm được camera: ${err.message}`, 'danger');
    if (noteEl) noteEl.textContent = `Lỗi: ${err.message}`;
  }
}

export function toggleCameraPicker(ev) {
  if (ev) ev.stopPropagation();
  const picker = document.getElementById('mon-camera-picker');
  if (picker) {
    picker.classList.toggle('open');
    // quét lại webcam mỗi lần mở: webcam ảo (iVCam/DroidCam/...) cắm sau vẫn xuất hiện
    loadCamerasList();
  }
}

export function switchSourceMode(mode) {
  monitorState.sourceMode = mode === 'file' ? 'file' : 'camera';

  const btnCam = document.getElementById('seg-src-camera');
  const btnFile = document.getElementById('seg-src-file');
  const camControls = document.getElementById('mon-camera-picker-wrap');
  const fileControls = document.getElementById('mon-file-controls');
  const pauseBtn = document.getElementById('live-pause');

  if (btnCam) btnCam.classList.toggle('active', monitorState.sourceMode === 'camera');
  if (btnFile) btnFile.classList.toggle('active', monitorState.sourceMode === 'file');
  if (camControls) camControls.style.display = monitorState.sourceMode === 'camera' ? 'inline-flex' : 'none';
  if (fileControls) fileControls.style.display = monitorState.sourceMode === 'file' ? 'inline-flex' : 'none';
  if (pauseBtn) pauseBtn.style.display = monitorState.sourceMode === 'file' ? 'inline-flex' : 'none';
}

export async function pickVideoFile() {
  if (hasDesktopBridge() && typeof window.pywebview.api.pick_video === 'function') {
    const chosen = await window.pywebview.api.pick_video();
    if (chosen) {
      setSelectedVideoPath(chosen);
    }
    return;
  }
  // Khi mở bằng trình duyệt web thông thường: cho phép nhập đường dẫn tệp trên máy chủ
  const current = monitorState.selectedFilePath || 'data/videos/video4.mp4';
  const input = window.prompt('Nhập đường dẫn tệp video (.mp4, .avi, .mov):', current);
  if (input && input.trim()) {
    setSelectedVideoPath(input.trim());
  }
}

export function setSelectedVideoPath(pathStr) {
  monitorState.selectedFilePath = pathStr;
  const display = document.getElementById('mon-file-display');
  if (display) {
    const parts = pathStr.replace(/\\/g, '/').split('/');
    display.textContent = parts[parts.length - 1] || pathStr;
    display.title = pathStr;
  }
}

export async function quickStartLive() {
  // CTA từ empty-state: chưa tick cam nào thì tự chọn tất cả camera có sẵn rồi bật
  if (monitorState.selectedCameras.size === 0) {
    for (const c of monitorState.catalog) {
      if (!c.in_use) monitorState.selectedCameras.add(c.source_id);
    }
    renderCameraPicker();
  }
  monitorState.sourceMode = 'camera';
  await startLive();
}

export async function startLive() {
  const startBtn = document.getElementById('live-start');
  const errBanner = document.getElementById('live-error-banner');
  const errText = document.getElementById('live-error');
  if (startBtn) startBtn.disabled = true;
  if (errBanner) errBanner.style.display = 'none';
  if (errText) errText.textContent = '';

  if (monitorState.sourceMode === 'file') {
    // Chế độ tệp video: một phiên như trước (hiển thị thành một tile trong lưới)
    if (!monitorState.selectedFilePath) {
      await pickVideoFile();
      if (!monitorState.selectedFilePath) {
        if (startBtn) startBtn.disabled = false;
        return;
      }
    }
    const modeSel = document.getElementById('mon-playback-mode');
    const payload = {
      source: 'file',
      path: monitorState.selectedFilePath,
      mode: modeSel ? modeSel.value : 'realtime',
    };
    try {
      await apiSend('/api/live/start', 'POST', payload);
      if (window.refreshSourcesAndPolicies) {
        window.refreshSourcesAndPolicies();
      }
    } catch (err) {
      if (errText) errText.textContent = `Không khởi động được nguồn phát: ${err.message}`;
      if (errBanner) errBanner.style.display = 'flex';
    }
    await pollLive();
    if (startBtn) startBtn.disabled = false;
    return;
  }

  // Chế độ camera: bật theo dõi mọi camera đã tick và chưa chạy
  const targets = [...monitorState.selectedCameras].filter((sid) => {
    const item = monitorState.catalog.find((c) => c.source_id === sid);
    return !item || !item.in_use;
  });

  if (!targets.length) {
    showToast('Chưa chọn camera nào mới để bật (camera đã chọn có thể đang chạy).', 'info');
    if (startBtn) startBtn.disabled = false;
    return;
  }

  let failures = [];
  for (const sid of targets) {
    try {
      await apiSend('/api/live/start', 'POST', { source: 'camera', source_id: sid });
    } catch (err) {
      failures.push(`${sourceName(sid)}: ${err.message}`);
    }
  }

  if (failures.length) {
    if (errText) errText.textContent = `Một số camera không bật được: ${failures.join(' · ')}`;
    if (errBanner) errBanner.style.display = 'flex';
    showToast(`Bật được ${targets.length - failures.length}/${targets.length} camera.`, failures.length ? 'danger' : 'ok');
  } else {
    showToast(`Đã bật theo dõi ${targets.length} camera.`, 'ok');
  }
  if (window.refreshSourcesAndPolicies) {
    window.refreshSourcesAndPolicies();
  }
  await loadCamerasList();
  await pollLive();
  if (startBtn) startBtn.disabled = false;
}

export async function togglePauseLive() {
  const fileStatus = monitorState.liveStatuses.find((s) => s.source_type === 'file');
  if (!fileStatus || fileStatus.state !== 'running') return;
  try {
    if (fileStatus.paused) {
      await apiSend(`/api/live/resume?source_id=${encodeURIComponent(fileStatus.source_id)}`, 'POST');
    } else {
      await apiSend(`/api/live/pause?source_id=${encodeURIComponent(fileStatus.source_id)}`, 'POST');
    }
  } catch (err) {
    showToast(`Lỗi điều khiển tạm dừng: ${err.message}`, 'danger');
  }
  await pollLive();
}

export async function stopLive(sourceId) {
  // Không truyền sourceId = dừng tất cả camera đang chạy (nút "Dừng tất cả")
  try {
    const qs = sourceId ? `?source_id=${encodeURIComponent(sourceId)}` : '';
    await apiSend(`/api/live/stop${qs}`, 'POST');
  } catch (err) {
    console.error(err);
  }
  if (sourceId && monitorState.focusedSourceId === sourceId) {
    monitorState.focusedSourceId = null;
  }
  await loadCamerasList();
  await pollLive();
  if (window.fetchAllData) {
    window.fetchAllData();
  }
}

export async function stopLiveSource(sourceId) {
  await stopLive(sourceId);
  showToast(`Đã dừng nguồn ${sourceName(sourceId)}.`, 'info');
}

export function focusCamTile(sourceId) {
  monitorState.focusedSourceId = sourceId;
  const statuses = monitorState.liveStatuses;
  const focused = statuses.find((s) => s.source_id === sourceId);
  if (focused) {
    monitorState.liveSourceId = focused.source_id;
    monitorState.liveSessionId = focused.session_id;
  }
  renderAllTiles(statuses);
  renderPersonsInspector(focused || null);
}

export function toggleQuickPolicyDrawer(ev) {
  if (ev) ev.stopPropagation();
  const drawer = document.getElementById('quick-policy-drawer');
  if (drawer) {
    drawer.classList.toggle('open');
  }
}

export function toggleSoundQuick() {
  monitorState.soundEnabled = !monitorState.soundEnabled;
  updateSoundButtonUI();
  apiSend('/api/settings', 'PUT', { alerts: { sound_enabled: monitorState.soundEnabled } }).catch(() => {});
  if (monitorState.soundEnabled) {
    playAlertBeep();
    showToast('Đã bật âm báo khi có sự kiện vi phạm mới.', 'ok');
  } else {
    showToast('Đã tắt âm báo vi phạm.', 'info');
  }
}

export function updateSoundButtonUI() {
  const btn = document.getElementById('mon-sound-btn');
  const setChk = document.getElementById('set-sound-enabled');
  if (btn) {
    btn.textContent = monitorState.soundEnabled ? 'Âm báo: Bật' : 'Âm báo: Tắt';
    btn.classList.toggle('btn-primary', monitorState.soundEnabled);
  }
  if (setChk) {
    setChk.checked = monitorState.soundEnabled;
  }
}

export async function pollLive() {
  let data;
  try {
    data = await apiGet('/api/live/statuses');
  } catch (_) {
    return;   // backend chưa sẵn sàng (desktop đang khởi động)
  }
  const statuses = data.cameras || [];
  monitorState.liveStatuses = statuses;

  // tập phiên đang chạy: bộ lọc "live" của Nhật ký vi phạm dùng tập này
  monitorState.activeSessionIds = new Set(
    statuses.filter((s) => s.session_id && (s.state === 'running' || s.state === 'starting')).map((s) => s.session_id)
  );

  // focus: nguồn người dùng chọn, nếu mất thì lấy nguồn đầu tiên
  if (!statuses.some((s) => s.source_id === monitorState.focusedSourceId)) {
    monitorState.focusedSourceId = statuses.length ? statuses[0].source_id : null;
  }
  const focused = statuses.find((s) => s.source_id === monitorState.focusedSourceId) || null;
  if (focused) {
    monitorState.liveSourceId = focused.source_id;
    monitorState.liveSessionId = focused.session_id;
  }

  // tự đặt bộ lọc sự kiện về "live" khi một phiên mới xuất hiện
  const filSession = document.getElementById('filter-session');
  if (filSession) {
    const hasNew = statuses.some((s) => s.session_id && (s.state === 'running' || s.state === 'starting'));
    if (hasNew && filSession.value !== 'live') {
      filSession.value = 'live';
      if (window.onSessionFilterAutoChanged) window.onSessionFilterAutoChanged(true);
    } else if (!hasNew && !s_statusesHasAnySession(statuses) && window.isSessionFilterUntouched && window.isSessionFilterUntouched()) {
      filSession.value = '';
    }
    if (window.renderEventsTable) window.renderEventsTable();
  }

  renderAllTiles(statuses);
  renderPersonsInspector(focused);

  // nhãn tổng trên topbar + thanh trạng thái đáy
  const runningCount = statuses.filter((s) => s.state === 'running').length;
  const stateBadge = document.getElementById('live-state');
  if (stateBadge) {
    stateBadge.textContent = runningCount
      ? `Đang giám sát ${runningCount} cam`
      : (focused ? (LIVE_STATE_LABELS[focused.state] || focused.state) : 'Đang dừng');
    stateBadge.className = `badge ${runningCount ? 'badge-ok' : (focused && focused.state === 'error' ? 'badge-danger' : 'badge-neutral')}`;
  }
  updateBottomStatusBar(focused, runningCount, statuses.length);

  // nút điều khiển
  const startBtn = document.getElementById('live-start');
  const stopBtn = document.getElementById('live-stop');
  const pauseBtn = document.getElementById('live-pause');
  const fileStatus = statuses.find((s) => s.source_type === 'file');
  const anyActive = statuses.some((s) => s.state === 'starting' || s.state === 'running');
  if (startBtn) startBtn.disabled = false;
  if (stopBtn) stopBtn.disabled = !statuses.length;
  if (pauseBtn) {
    pauseBtn.style.display = fileStatus ? 'inline-flex' : 'none';
    pauseBtn.disabled = !(fileStatus && fileStatus.state === 'running');
    pauseBtn.textContent = fileStatus && fileStatus.paused ? 'Tiếp tục' : 'Tạm dừng';
  }

  // quy định nhanh: đếm theo nguồn đang focus
  const quickPolLabel = document.getElementById('quick-policy-summary');
  if (quickPolLabel) {
    const reqCount = Array.isArray(focused?.required_ppe) ? focused.required_ppe.length : 5;
    quickPolLabel.textContent = `Quy định PPE: ${reqCount}/5`;
  }

  // lỗi nguồn: banner lỗi cho tile đang focus
  const errBanner = document.getElementById('live-error-banner');
  const errText = document.getElementById('live-error');
  if (focused && focused.error) {
    if (errText) {
      errText.textContent = `${focused.error} (nguồn ${sourceName(focused.source_id)})`;
    }
    if (errBanner) errBanner.style.display = 'flex';
  } else if (errBanner) {
    errBanner.style.display = 'none';
  }

  // thanh tiến độ tệp video
  renderFileProgress(fileStatus);
}

function s_statusesHasAnySession(statuses) {
  return statuses.some((s) => Boolean(s.session_id));
}

function renderAllTiles(statuses) {
  const grid = document.getElementById('live-tiles');
  if (!grid) return;
  const placeholder = document.getElementById('live-placeholder');

  // xóa tile của nguồn đã dừng
  for (const el of Array.from(grid.querySelectorAll('.cam-tile'))) {
    const sid = el.getAttribute('data-source');
    if (!statuses.some((s) => s.source_id === sid)) {
      el.remove();
      delete monitorState.tileSessions[sid];
    }
  }

  // tạo / cập nhật tile cho từng nguồn
  for (const s of statuses) {
    const color = sourceColor(s.source_id);
    let tile = grid.querySelector(`.cam-tile[data-source="${CSS.escape(s.source_id)}"]`);
    if (!tile) {
      tile = document.createElement('div');
      tile.className = 'cam-tile';
      tile.setAttribute('data-source', s.source_id);
      tile.style.setProperty('--cam-color', color);
      tile.innerHTML = `
        <div class="cam-tile-head" style="border-left: 3px solid ${color};">
          <span class="cam-color-dot" style="background:${color}"></span>
          <span class="cam-tile-name" style="color:${color};">${sourceName(s.source_id)}</span>
          <span class="badge badge-info mono cam-tile-fps">— FPS</span>
          <button class="btn btn-sm btn-danger" title="Dừng nguồn này">Dừng</button>
        </div>
        <div class="cam-tile-stage">
          <img alt="Luồng ${s.source_id}">
          <div class="tile-placeholder">${LIVE_STATE_LABELS[s.state] || s.state}</div>
        </div>
      `;
      tile.addEventListener('click', () => window.focusCamTile(s.source_id));
      const stopBtn = tile.querySelector('button.btn-danger');
      if (stopBtn) {
        stopBtn.addEventListener('click', (ev) => {
          ev.stopPropagation();
          window.stopLiveSource(s.source_id);
        });
      }
      grid.appendChild(tile);
    }
    tile.style.setProperty('--cam-color', color);
    const nameEl = tile.querySelector('.cam-tile-name');
    if (nameEl) nameEl.textContent = sourceName(s.source_id);

    const img = tile.querySelector('img');
    const phEl = tile.querySelector('.tile-placeholder');
    const fpsEl = tile.querySelector('.cam-tile-fps');
    const active = s.state === 'starting' || s.state === 'running';

    if (active && img) {
      if (monitorState.tileSessions[s.source_id] !== s.session_id) {
        monitorState.tileSessions[s.source_id] = s.session_id;
        img.src = `${API_BASE}/api/live/stream?source_id=${encodeURIComponent(s.source_id)}`;
        img.onerror = () => {
          delete monitorState.tileSessions[s.source_id];
        };
      }
      tile.classList.add('on');
      if (phEl) phEl.style.display = 'none';
    } else {
      if (img && monitorState.tileSessions[s.source_id]) {
        img.removeAttribute('src');
        delete monitorState.tileSessions[s.source_id];
      }
      tile.classList.remove('on');
      if (phEl) {
        phEl.style.display = 'flex';
        phEl.textContent = s.state === 'error'
          ? (s.error || 'Không thể mở nguồn phát')
          : (LIVE_STATE_LABELS[s.state] || s.state);
      }
    }

    if (fpsEl) {
      fpsEl.textContent = s.state === 'running'
        ? `${(s.fps || 0).toFixed(1)} FPS · ${s.persons || 0} người`
        : (LIVE_STATE_LABELS[s.state] || s.state);
    }

    const hasViolation = s.state === 'running' && (s.persons_detail || []).some((p) => p.status === 'violation');
    tile.classList.toggle('alert-border', Boolean(hasViolation));
    tile.classList.toggle('focused', s.source_id === monitorState.focusedSourceId);
  }

  if (placeholder) {
    placeholder.style.display = statuses.length ? 'none' : 'flex';
  }
  // đánh dấu các nguồn không còn tồn tại trong monitorState.tileSessions
  for (const sid of Object.keys(monitorState.tileSessions)) {
    if (!statuses.some((s) => s.source_id === sid)) {
      delete monitorState.tileSessions[sid];
    }
  }
}

function renderFileProgress(fileStatus) {
  const progBar = document.getElementById('video-progress-bar');
  if (!progBar) return;
  const active = fileStatus && (fileStatus.state === 'running' || fileStatus.frames > 0);
  if (fileStatus && active) {
    progBar.style.display = 'flex';
    const pct = fileStatus.total_frames > 0 ? Math.min(100, Math.round((fileStatus.frame / fileStatus.total_frames) * 100)) : 0;
    const fill = document.getElementById('video-progress-fill');
    const timeLabel = document.getElementById('video-progress-time');
    const frameLabel = document.getElementById('video-progress-frames');
    if (fill) fill.style.width = `${pct}%`;
    if (timeLabel) timeLabel.textContent = `${fmtSeconds(fileStatus.position_s)} / ${fmtSeconds(fileStatus.duration_s)}`;
    if (frameLabel) frameLabel.textContent = `Khung ${fileStatus.frame} / ${fileStatus.total_frames || '—'}`;
  } else {
    progBar.style.display = 'none';
  }
}

function renderPersonsInspector(s) {
  const container = document.getElementById('inspector-persons-list');
  const countBadge = document.getElementById('inspector-persons-count');
  if (!container) return;

  const active = Boolean(s) && s.state === 'running';
  const details = s && Array.isArray(s.persons_detail) ? s.persons_detail : [];
  const count = active ? (details.length || s.persons || 0) : 0;

  if (countBadge) {
    countBadge.textContent = String(count).padStart(2, '0');
  }

  if (!s) {
    container.innerHTML = `<div class="dock-empty">Chưa bật nguồn nào. Tick chọn camera rồi bấm "Bật theo dõi".</div>`;
    return;
  }

  if (!active) {
    container.innerHTML = `<div class="dock-empty">Nguồn ${sourceName(s.source_id)} đang dừng.</div>`;
    return;
  }

  if (details.length === 0) {
    if (s.persons > 0) {
      container.innerHTML = `<div class="dock-empty">Phát hiện ${s.persons} đối tượng trong khung hình (đang khởi tạo mã theo dõi).</div>`;
    } else {
      container.innerHTML = `<div class="dock-empty">Hiện không có người trong vùng quan sát của ${sourceName(s.source_id)}.</div>`;
    }
    return;
  }

  container.innerHTML = details
    .map((p) => {
      let badgeHtml = '';
      let summaryHtml = '';

      if (p.status === 'violation') {
        badgeHtml = `<span class="badge badge-danger">ĐANG VI PHẠM</span>`;
        const missNames = (p.confirmed_missing.length ? p.confirmed_missing : p.missing_now)
          .map((k) => PPE_META[k]?.name || k)
          .join(', ');
        summaryHtml = `<span class="person-summary-text danger">Thiếu: ${missNames || 'Trang bị bắt buộc'}</span>`;
      } else if (p.status === 'observing_missing') {
        badgeHtml = `<span class="badge badge-warn">ĐANG XÁC MINH</span>`;
        const missNames = p.missing_now.map((k) => PPE_META[k]?.name || k).join(', ');
        summaryHtml = `<span>Nghi thiếu ${missNames} (đang tích lũy thời gian)</span>`;
      } else if (p.status === 'compliant') {
        badgeHtml = `<span class="badge badge-ok">ĐỦ TRANG BỊ</span>`;
        summaryHtml = `<span>Tuân thủ đầy đủ quy định hiện hành</span>`;
      } else if (p.status === 'lost') {
        badgeHtml = `<span class="badge badge-neutral">TẠM KHUẤT</span>`;
        summaryHtml = `<span>Mất dấu tạm thời, đang giữ mã theo dõi</span>`;
      } else {
        badgeHtml = `<span class="badge badge-info">ĐANG QUAN SÁT</span>`;
        summaryHtml = `<span>Một số bộ phận chưa nhìn rõ hoặc mới vào khung</span>`;
      }

      const cellsHtml = PPE_KEYS.map((key) => {
        const meta = PPE_META[key];
        const st = (p.items && p.items[key]) || 'unknown';
        let cellClass = 'st-unknown';
        let stateWord = 'Khuất';
        if (st === 'have') {
          cellClass = 'st-have';
          stateWord = 'Đạt';
        } else if (st === 'missing') {
          cellClass = 'st-missing';
          stateWord = 'Thiếu';
        } else if (st === 'unchecked') {
          cellClass = 'st-unchecked';
          stateWord = 'Tắt';
        }
        return `
          <div class="ppe-cell ${cellClass}" title="${meta.name}: ${stateWord}">
            <span class="ppe-cell-code">${meta.code}</span>
            <span class="ppe-cell-state">${stateWord}</span>
          </div>
        `;
      }).join('');

      const actionBtn = p.event_id
        ? `<button class="btn btn-sm" onclick="window.viewEvent('${p.event_id}')">Minh chứng</button>`
        : '';

      return `
        <div class="person-card status-${p.status}">
          <div class="person-card-top">
            <span class="person-id mono">Người #${String(p.track_id).padStart(2, '0')}</span>
            ${badgeHtml}
          </div>
          <div class="person-ppe-grid">
            ${cellsHtml}
          </div>
          <div class="person-card-footer">
            ${summaryHtml}
            ${actionBtn}
          </div>
        </div>
      `;
    })
    .join('');
}

export function renderLiveAlertFeed(allEvents) {
  const container = document.getElementById('inspector-alerts-list');
  const countBadge = document.getElementById('inspector-alerts-count');
  if (!container) return;

  // Kiểm tra sự kiện mới để phát thông báo góc màn hình & âm báo
  if (monitorState.initialEventsLoaded) {
    for (const ev of allEvents) {
      if (!monitorState.seenEventIds.has(ev.event_id)) {
        monitorState.seenEventIds.add(ev.event_id);
        if (ev.event_state === 'active') {
          const missText = ev.missing_items.map((k) => PPE_META[k]?.name || k).join(', ');
          showToast(
            `Phát hiện vi phạm mới (${sourceName(ev.source_id)}): Người #${ev.track_id} thiếu ${missText}`,
            'danger',
            'Xem',
            () => window.viewEvent(ev.event_id)
          );
          if (monitorState.soundEnabled) {
            playAlertBeep();
          }
        }
      }
    }
  } else {
    allEvents.forEach((ev) => monitorState.seenEventIds.add(ev.event_id));
    monitorState.initialEventsLoaded = true;
  }

  // Ưu tiên hiển thị sự kiện của các phiên đang chạy; nếu chưa chạy gì thì 8 sự kiện gần nhất
  const activeSessions = [...monitorState.activeSessionIds];
  const sessionEvents = activeSessions.length
    ? allEvents.filter((e) => activeSessions.includes(e.session_id))
    : allEvents.slice(0, 8);

  if (countBadge) {
    countBadge.textContent = String(sessionEvents.length).padStart(2, '0');
  }

  if (!sessionEvents.length) {
    container.innerHTML = `<div class="dock-empty">${
      activeSessions.length
        ? 'Chưa ghi nhận sự kiện vi phạm nào trong các phiên hiện tại.'
        : 'Chưa có sự kiện vi phạm nào.'
    }</div>`;
    return;
  }

  container.innerHTML = sessionEvents
    .slice(0, 10)
    .map((ev) => {
      const thumbUrl = ev.thumbnail_url
        ? ev.thumbnail_url.startsWith('http')
          ? ev.thumbnail_url
          : `${API_BASE}${ev.thumbnail_url}`
        : '';
      const thumbHtml = thumbUrl
        ? `<img class="alert-thumb" src="${thumbUrl}" alt="Minh chứng" onclick="window.viewEvent('${ev.event_id}')">`
        : `<div class="alert-thumb" style="display:flex;align-items:center;justify-content:center;font-size:10px;color:var(--text-dim);">Không ảnh</div>`;

      const missNames = ev.missing_items.length
        ? ev.missing_items.map((k) => PPE_META[k]?.name || k).join(', ')
        : 'Chờ xác minh mục còn lại';

      const stBadge =
        ev.event_state === 'active'
          ? `<span class="badge badge-danger">Đang mở</span>`
          : ev.event_state === 'pending_observation'
          ? `<span class="badge badge-warn">Tạm khuất</span>`
          : `<span class="badge badge-ok">Đã đóng</span>`;

      return `
        <div class="alert-feed-item ${ev.event_state === 'active' ? 'active-ev' : ''}">
          ${thumbHtml}
          <div class="alert-info">
            <div class="alert-title">Người #${ev.track_id} · Thiếu: ${missNames}</div>
            <div class="alert-sub mono">${fmtTimeShort(ev.system_time)} · Mốc ${ev.confirmed_at.toFixed(1)}s
              <span class="src-chip" style="background:${sourceColor(ev.source_id)}">${sourceName(ev.source_id)}</span></div>
            <div>${stBadge}</div>
          </div>
          <button class="btn btn-sm" onclick="window.viewEvent('${ev.event_id}')">Chi tiết</button>
        </div>
      `;
    })
    .join('');
}

function updateBottomStatusBar(focused, runningCount, totalSources) {
  const dot = document.getElementById('sb-dot');
  const stateEl = document.getElementById('sb-state');
  const fpsEl = document.getElementById('sb-fps');
  const sessionEl = document.getElementById('sb-session');

  const st = focused || null;
  if (dot) {
    dot.className = `status-dot ${st && st.state === 'running' ? 'running' : (st ? st.state : 'idle')}`;
  }
  if (stateEl) {
    stateEl.textContent = runningCount
      ? `${runningCount} cam đang giám sát${st ? ` · ${sourceName(st.source_id)}` : ''}`
      : LIVE_STATE_LABELS[st ? st.state : 'idle'] || 'Sẵn sàng';
  }
  if (fpsEl) {
    fpsEl.textContent = st && st.state === 'running'
      ? `${st.fps.toFixed(1)} / ${st.camera_fps.toFixed(1)} FPS`
      : '— FPS';
  }
  if (sessionEl) {
    sessionEl.textContent = st ? (st.session_id || 'Chưa mở phiên') : 'Chưa mở phiên';
  }
}
