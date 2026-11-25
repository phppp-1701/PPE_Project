/* ==========================================================================
   PPE MONITOR — MODULE 3, 4, 5, 6: QUY ĐỊNH PPE, THỐNG KÊ, CÀI ĐẶT & TRỢ GIÚP
   ========================================================================== */

import {
  PPE_KEYS,
  PPE_META,
  apiGet,
  apiSend,
  closeHelpModal,
  hasDesktopBridge,
  openHelpModal,
  showToast,
  toggleAppFullscreen,
} from './api.js';
import {
  changeEventsPage,
  closeModal,
  exportEvents,
  isSessionFilterUntouched,
  loadEventsAndSessions,
  onSessionFilterAutoChanged,
  renderEventsTable,
  resetEventFilters,
  selectFrame,
  stepFrame,
  submitFeedback,
  toggleFalseAlarmSection,
  viewEvent,
} from './events.js';
import {
  addCameraUrl,
  addDiscoveredCam,
  discoverLanCams,
  initMonitorModule,
  loadCamerasList,
  monitorState,
  onCameraCheckChange,
  openDatePicker,
  openEvidenceFolder,
  pickVideoFile,
  pollLive,
  focusCamTile,
  quickStartLive,
  sourceColor,
  startLive,
  stopLive,
  stopLiveSource,
  switchSourceMode,
  toggleCameraPicker,
  togglePauseLive,
  toggleQuickPolicyDrawer,
  toggleSoundQuick,
  updateSoundButtonUI,
  renameSourcePrompt,
} from './monitor.js';

const VIEW_METADATA = {
  monitor: {
    title: 'Giám sát trực tiếp',
    subtitle: 'Trung tâm phát hiện vi phạm PPE thời gian thực qua Camera & Tệp Video',
  },
  events: {
    title: 'Nhật ký vi phạm & Minh chứng',
    subtitle: 'Tra cứu lịch sử sự kiện, kiểm tra khung hình theo mốc thời gian và xuất dữ liệu báo cáo',
  },
  policy: {
    title: 'Quy định PPE theo nguồn',
    subtitle: 'Thiết lập trang bị bảo hộ bắt buộc và các mẫu quy định nhanh cho từng nguồn phát',
  },
  stats: {
    title: 'Thống kê & Phân tích',
    subtitle: 'Tổng hợp tần suất vi phạm theo loại trang bị, khung giờ, nguồn phát và độ chính xác cảnh báo',
  },
  settings: {
    title: 'Cài đặt hệ thống',
    subtitle: 'Cấu hình thiết bị Camera, bộ xử lý GPU/CPU, lưu trữ dữ liệu và thông số mô hình',
  },
  help: {
    title: 'Trợ giúp & Thông tin hệ thống (F1)',
    subtitle: 'Hướng dẫn vận hành, quy ước màu sắc, câu hỏi thường gặp và giới hạn kỹ thuật',
  },
};

let policySaveTimer = null;

export function switchView(viewId) {
  if (!VIEW_METADATA[viewId]) return;

  document.querySelectorAll('.nav-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.view === viewId);
  });

  document.querySelectorAll('.view-pane').forEach((pane) => {
    pane.classList.toggle('active', pane.id === `view-${viewId}`);
  });

  const titleEl = document.getElementById('topbar-title');
  const subEl = document.getElementById('topbar-subtitle');
  if (titleEl) titleEl.textContent = VIEW_METADATA[viewId].title;
  if (subEl) subEl.textContent = VIEW_METADATA[viewId].subtitle;

  if (viewId === 'events') {
    loadEventsAndSessions();
  } else if (viewId === 'stats') {
    loadStatsView();
  } else if (viewId === 'settings') {
    loadSettingsAndSystemInfo();
  }
}

/* ==========================================================================
   MODULE 3: QUY ĐỊNH PPE & MẪU NHANH (PRESETS)
   ========================================================================== */

export async function refreshSourcesAndPolicies() {
  try {
    const sources = await apiGet('/api/sources');
    const polSel = document.getElementById('policy-source');
    const filSel = document.getElementById('filter-source');
    const prevPol = polSel?.value;
    const prevFil = filSel?.value;

    if (polSel) {
      polSel.innerHTML = sources
        .map((s) => `<option value="${s.source_id}">${s.name} (${s.source_id})</option>`)
        .join('');
      const cam = sources.find((s) => s.source_type === 'camera');
      polSel.value =
        prevPol && sources.some((s) => s.source_id === prevPol)
          ? prevPol
          : cam
          ? cam.source_id
          : sources[0]?.source_id || '';
    }

    if (filSel) {
      filSel.innerHTML =
        `<option value="">Tất cả nguồn phát</option>` +
        sources.map((s) => `<option value="${s.source_id}">${s.name}</option>`).join('');
      if (prevFil && sources.some((s) => s.source_id === prevFil)) {
        filSel.value = prevFil;
      }
    }

    await loadPolicyForCurrentSource();
  } catch (err) {
    console.error('Lỗi tải danh sách nguồn:', err);
  }
}

export async function loadPolicyForCurrentSource() {
  const polSel = document.getElementById('policy-source');
  const src = polSel?.value || monitorState.liveSourceId || 'webcam';
  if (!src) return;
  try {
    const pol = await apiGet(`/api/sources/${encodeURIComponent(src)}/policy`);
    syncPolicyCheckboxes(pol.required_ppe || []);
    updatePolicyNoteText(`Nguồn ${src} · Quy định phiên bản v${pol.version}. Thay đổi được lưu và áp dụng tự động.`);
  } catch (err) {
    console.error('Lỗi tải quy định PPE:', err);
  }
}

function syncPolicyCheckboxes(requiredList) {
  const reqSet = new Set(requiredList || []);
  PPE_KEYS.forEach((p) => {
    const checked = reqSet.has(p);
    const mainChk = document.getElementById(`pol-${p}`);
    const quickChk = document.getElementById(`qpol-${p}`);
    const statusCell = document.getElementById(`pol-status-${p}`);
    if (mainChk) mainChk.checked = checked;
    if (quickChk) quickChk.checked = checked;
    if (statusCell) {
      statusCell.innerHTML = checked
        ? `<span class="badge badge-ok">Bắt buộc</span>`
        : `<span class="badge badge-neutral">Không kiểm</span>`;
    }
  });
  const quickSummary = document.getElementById('quick-policy-summary');
  if (quickSummary) {
    quickSummary.textContent = `Quy định PPE: ${reqSet.size}/5`;
  }
}

function updatePolicyNoteText(text) {
  const note1 = document.getElementById('policy-note');
  const note2 = document.getElementById('quick-policy-note');
  if (note1) note1.textContent = text;
  if (note2) note2.textContent = text;
}

export function onPolicyCheckboxToggle(ppeKey, fromQuick = false) {
  const srcEl = document.getElementById(fromQuick ? `qpol-${ppeKey}` : `pol-${ppeKey}`);
  const dstEl = document.getElementById(fromQuick ? `pol-${ppeKey}` : `qpol-${ppeKey}`);
  if (srcEl && dstEl) {
    dstEl.checked = srcEl.checked;
  }
  const currentItems = PPE_KEYS.filter((p) => document.getElementById(`pol-${p}`)?.checked);
  if (currentItems.length === 0) {
    const ok = window.confirm(
      'Không kiểm trang bị nào: hệ thống chỉ theo dõi người và không tạo cảnh báo vi phạm. Bạn có muốn tiếp tục?'
    );
    if (!ok) {
      if (srcEl) srcEl.checked = true;
      if (dstEl) dstEl.checked = true;
      return;
    }
  }
  syncPolicyCheckboxes(PPE_KEYS.filter((p) => document.getElementById(`pol-${p}`)?.checked));
  schedulePolicySave();
}

export function applyPolicyPreset(items, confirmEmpty = false) {
  if (confirmEmpty && items.length === 0) {
    const ok = window.confirm(
      'Tắt toàn bộ PPE bắt buộc: hệ thống chỉ theo dõi người trên khung hình và không sinh cảnh báo. Tiếp tục?'
    );
    if (!ok) return;
  }
  syncPolicyCheckboxes(items);
  schedulePolicySave();
}

export function schedulePolicySave() {
  updatePolicyNoteText('Đang lưu quy định…');
  clearTimeout(policySaveTimer);
  policySaveTimer = setTimeout(savePolicyNow, 500);
}

export async function savePolicyNow() {
  const polSel = document.getElementById('policy-source');
  const src = polSel?.value || monitorState.liveSourceId || 'webcam';
  const items = PPE_KEYS.filter((p) => document.getElementById(`pol-${p}`)?.checked);
  try {
    const data = await apiSend(`/api/sources/${encodeURIComponent(src)}/policy`, 'PUT', {
      required_ppe: items,
    });
    const msg = data.applied_live
      ? `Đã áp dụng quy định v${data.version} (${items.length}/5 món) cho luồng đang chạy. Các sự kiện đang mở được đóng với lý do "Đổi quy định PPE".`
      : `Đã lưu quy định v${data.version} (${items.length}/5 món) cho nguồn ${src}.`;
    updatePolicyNoteText(msg);
    showToast(`Đã áp dụng quy định PPE v${data.version} (${items.length}/5 trang bị).`, 'ok');
    pollLive();
  } catch (err) {
    updatePolicyNoteText(`Lỗi lưu quy định: ${err.message}`);
    showToast(`Lỗi lưu quy định: ${err.message}`, 'danger');
  }
}

/* ==========================================================================
   MODULE 4: THỐNG KÊ & BÁO CÁO (ANALYTICS)
   ========================================================================== */

export async function loadStatsView() {
  try {
    const stats = await apiGet('/api/stats');

    // Cập nhật KPI
    const setTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };
    setTxt('kpi-total', stats.total_events ?? 0);
    setTxt('kpi-active', stats.active_events ?? 0);
    setTxt('kpi-pending', stats.pending_events ?? 0);
    setTxt('kpi-closed', stats.closed_events ?? 0);

    const fb = stats.feedback_summary || {};
    const faPct = fb.reviewed_events > 0 ? `${(fb.false_alarm_rate * 100).toFixed(1)}%` : '0.0%';
    setTxt('kpi-false-rate', faPct);
    setTxt('kpi-false-sub', `Đã đánh giá ${fb.reviewed_events || 0} sự kiện (${fb.false_alarm_count || 0} báo sai)`);

    // Cập nhật badge số sự kiện đang mở trên Sidebar và Status Bar
    const navBadge = document.getElementById('nav-active-badge');
    const sbActive = document.getElementById('sb-active-events');
    if (navBadge) {
      navBadge.textContent = String(stats.active_events ?? 0);
      navBadge.classList.toggle('danger', (stats.active_events ?? 0) > 0);
    }
    if (sbActive) {
      sbActive.textContent = String(stats.active_events ?? 0);
      sbActive.style.color = (stats.active_events ?? 0) > 0 ? '#f87171' : 'var(--text-secondary)';
    }

    // Biểu đồ phân bố theo 5 loại PPE (đồng nhất 1 tông màu kỹ thuật)
    const ppeContainer = document.getElementById('ppe-bars-container');
    if (ppeContainer && stats.ppe_violations) {
      const maxVal = Math.max(...Object.values(stats.ppe_violations), 1);
      ppeContainer.innerHTML = PPE_KEYS.map((ppe) => {
        const count = stats.ppe_violations[ppe] || 0;
        const pct = Math.round((count / maxVal) * 100);
        const meta = PPE_META[ppe];
        return `
          <div class="bar-row">
            <div class="bar-meta">
              <span><strong class="mono">[${meta.code}]</strong> ${meta.name}</span>
              <span class="mono" style="color: var(--text-secondary); font-weight: 600;">${count} lượt</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill" style="width: ${pct}%;"></div>
            </div>
          </div>
        `;
      }).join('');
    }

    // Phân bố theo nguồn phát
    const srcContainer = document.getElementById('stats-by-source-tbody');
    if (srcContainer) {
      const entries = Object.entries(stats.by_source || {});
      if (entries.length === 0) {
        srcContainer.innerHTML = `<tr><td colspan="3" style="text-align:center; color: var(--text-dim); padding: 18px;">Chưa có dữ liệu</td></tr>`;
      } else {
        const total = Math.max(stats.total_events || 1, 1);
        srcContainer.innerHTML = entries
          .sort((a, b) => b[1] - a[1])
          .map(([src, cnt]) => {
            const ratio = ((cnt / total) * 100).toFixed(1);
            const color = sourceColor(src);
            const name = monitorState.catalog.find((c) => c.source_id === src)?.name || src;
            return `
              <tr>
                <td class="mono" style="font-weight: 600;">
                  <span class="cam-color-dot" style="background:${color}; display:inline-block; margin-right:6px;"></span>${name}
                  <span style="color: var(--text-muted); font-size: 11px;">(${src})</span>
                </td>
                <td class="mono">${cnt} sự kiện</td>
                <td class="mono" style="color: var(--text-muted);">${ratio}%</td>
              </tr>
            `;
          })
          .join('');
      }
    }
  } catch (err) {
    console.error('Lỗi tải dữ liệu thống kê:', err);
  }
}

/* ==========================================================================
   MODULE 5: CÀI ĐẶT HỆ THỐNG & THÔNG TIN MÔ HÌNH
   ========================================================================== */

export async function loadSettingsAndSystemInfo() {
  try {
    const [settings, sysInfo] = await Promise.all([apiGet('/api/settings'), apiGet('/api/system')]);

    // Lưu trữ presets và trạng thái âm báo
    monitorState.presets = settings.presets || [];
    monitorState.soundEnabled = Boolean(settings.alerts?.sound_enabled);
    updateSoundButtonUI();
    renderPresetButtons(monitorState.presets);

    // Điền biểu mẫu cài đặt
    const camCfg = settings.camera || {};
    const procCfg = settings.processing || {};
    const retCfg = settings.retention || {};

    const camIdxEl = document.getElementById('set-camera-index');
    if (camIdxEl && camCfg.default_index !== undefined) {
      camIdxEl.value = String(camCfg.default_index);
    }
    const resEl = document.getElementById('set-camera-res');
    if (resEl) {
      resEl.value = `${camCfg.width || 1280}x${camCfg.height || 720}`;
    }
    const devEl = document.getElementById('set-device');
    if (devEl) {
      devEl.value = procCfg.device || 'auto';
    }
    const keepDaysEl = document.getElementById('set-keep-days');
    if (keepDaysEl) {
      keepDaysEl.value = String(retCfg.keep_days ?? 30);
    }
    const dataDirEl = document.getElementById('set-data-dir');
    if (dataDirEl) {
      dataDirEl.value = sysInfo.storage?.data_dir || settings.paths?.data_dir || '';
    }

    // Cập nhật thông tin hệ thống và Status Bar
    const sbDevice = document.getElementById('sb-device');
    const sbDisk = document.getElementById('sb-disk');
    const sideVer = document.getElementById('sidebar-version');
    const sideModel = document.getElementById('sidebar-model');

    if (sbDevice) sbDevice.textContent = sysInfo.compute?.active_device || 'CPU';
    if (sbDisk) {
      const freeGb = sysInfo.storage?.disk_free_gb;
      sbDisk.textContent = freeGb !== null && freeGb !== undefined ? `${freeGb} GB trống` : '—';
      sbDisk.style.color = sysInfo.storage?.low_disk_warning ? '#fbbf24' : 'var(--text-secondary)';
    }
    if (sideVer) {
      sideVer.textContent = `v${sysInfo.app_version || '1.0.0'} (${sysInfo.git_commit || 'release'})`;
    }
    if (sideModel) {
      sideModel.textContent = sysInfo.model?.detector_model_name || 'YOLO11s PPE-6';
    }

    // Bảng thông số Mô hình & Ngưỡng (Chỉ đọc)
    const m = sysInfo.model || {};
    const setSysTxt = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };
    setSysTxt('sys-det-weights', m.detector_weights || '—');
    setSysTxt('sys-det-sha', m.detector_sha256 ? `${m.detector_sha256} (Đã xác thực)` : 'Chưa nạp tệp .pt');
    setSysTxt('sys-det-params', `imgsz=${m.imgsz ?? '—'}, conf_person=${m.conf_person ?? '—'}, conf_ppe=${m.conf_ppe ?? '—'}`);
    setSysTxt(
      'sys-temporal-params',
      `T_on=${m.temporal?.T_on ?? '—'}s (n_on=${m.temporal?.n_on ?? '—'}, theta_on=${m.temporal?.theta_on ?? '—'}) · T_off=${
        m.temporal?.T_off ?? '—'
      }s`
    );
    setSysTxt(
      'sys-comp-params',
      `tau_in=${m.compliance?.tau_in ?? '—'}, tau_occ=${m.compliance?.tau_occ ?? '—'}, area_min=${m.compliance?.area_min_px ?? '—'} px²`
    );
    setSysTxt('sys-gpu-info', sysInfo.compute?.active_device || 'CPU');
  } catch (err) {
    console.error('Lỗi tải cài đặt hệ thống:', err);
  }
}

function renderPresetButtons(presets) {
  const list = Array.isArray(presets) && presets.length > 0
    ? presets
    : [
        { id: 'cong_truong', name: 'Công trường', required_ppe: ['helmet', 'vest', 'gloves', 'boots'] },
        { id: 'han_mai', name: 'Hàn / mài', required_ppe: ['helmet', 'vest', 'gloves', 'goggles', 'boots'] },
        { id: 'kho', name: 'Kho bãi', required_ppe: ['helmet', 'vest'] },
      ];

  const html =
    list
      .map(
        (p) =>
          `<button class="preset-btn" onclick='window.applyPolicyPreset(${JSON.stringify(p.required_ppe)}, false)' title="${
            p.description || ''
          }">Mẫu: ${p.name}</button>`
      )
      .join('') +
    `<button class="preset-btn" onclick='window.applyPolicyPreset(["helmet","vest","gloves","goggles","boots"], false)'>Bật tất cả (5/5)</button>` +
    `<button class="preset-btn" onclick='window.applyPolicyPreset([], true)'>Tắt tất cả (0/5)</button>`;

  const quickBox = document.getElementById('quick-preset-buttons');
  const mainBox = document.getElementById('main-preset-buttons');
  if (quickBox) quickBox.innerHTML = html;
  if (mainBox) mainBox.innerHTML = html;
}

export async function saveSystemSettings() {
  const camIdx = parseInt(document.getElementById('set-camera-index')?.value || '0', 10);
  const resVal = document.getElementById('set-camera-res')?.value || '1280x720';
  const [w, h] = resVal.split('x').map((x) => parseInt(x, 10));
  const dev = document.getElementById('set-device')?.value || 'auto';
  const keepDays = parseInt(document.getElementById('set-keep-days')?.value || '30', 10);
  const sound = Boolean(document.getElementById('set-sound-enabled')?.checked);

  try {
    await apiSend('/api/settings', 'PUT', {
      camera: { default_index: camIdx, width: w || 1280, height: h || 720 },
      processing: { device: dev },
      retention: { keep_days: Math.max(1, keepDays) },
      alerts: { sound_enabled: sound },
    });
    monitorState.soundEnabled = sound;
    updateSoundButtonUI();
    await loadCamerasList();
    await loadSettingsAndSystemInfo();
    showToast('Đã lưu cài đặt hệ thống. Thay đổi thiết bị suy luận sẽ áp dụng từ phiên giám sát kế tiếp.', 'ok');
  } catch (err) {
    showToast(`Lỗi lưu cài đặt: ${err.message}`, 'danger');
  }
}

export async function runCleanupOldData() {
  const keepDays = parseInt(document.getElementById('set-keep-days')?.value || '30', 10);
  const ok = window.confirm(
    `Xác nhận xóa vĩnh viễn các sự kiện đã đóng và ảnh minh chứng cũ hơn ${keepDays} ngày? Hành động này không thể hoàn tác.`
  );
  if (!ok) return;
  try {
    const res = await apiSend('/api/settings/cleanup', 'POST', { keep_days: keepDays });
    showToast(`Đã dọn dẹp ${res.deleted_events} sự kiện và ${res.deleted_files} tệp ảnh cũ.`, 'ok');
    loadEventsAndSessions();
    loadStatsView();
  } catch (err) {
    showToast(`Lỗi dọn dữ liệu: ${err.message}`, 'danger');
  }
}

export async function openDataFolder() {
  if (hasDesktopBridge() && typeof window.pywebview.api.open_folder === 'function') {
    await window.pywebview.api.open_folder('');
    return;
  }
  const dir = document.getElementById('set-data-dir')?.value || 'outputs/';
  showToast(`Thư mục dữ liệu trên máy chủ: ${dir}`, 'info');
}

export async function saveDiagnosticBundle() {
  if (hasDesktopBridge() && typeof window.pywebview.api.save_diagnostic_bundle === 'function') {
    const out = await window.pywebview.api.save_diagnostic_bundle();
    if (out) {
      showToast(`Đã lưu gói chẩn đoán kỹ thuật tại: ${out}`, 'ok');
    }
    return;
  }
  showToast('Chức năng lưu gói chẩn đoán trực tiếp hoạt động trong cửa sổ ứng dụng Desktop.', 'info');
}

export function filterHelpTopics() {
  const q = (document.getElementById('help-search-input')?.value || '').trim().toLowerCase();
  document.querySelectorAll('.help-section-card').forEach((card) => {
    const text = card.textContent.toLowerCase();
    card.style.display = !q || text.includes(q) ? 'flex' : 'none';
  });
}

/* ==========================================================================
   KHỞI ĐỘNG TOÀN BỘ ỨNG DỤNG & GẮN SỰ KIỆN BÀN PHÍM
   ========================================================================== */

export async function fetchAllData() {
  await Promise.all([loadStatsView(), loadEventsAndSessions()]);
}

function startClockTicker() {
  const updateClock = () => {
    const el = document.getElementById('sb-clock');
    if (!el) return;
    const now = new Date();
    const p = (n) => String(n).padStart(2, '0');
    el.textContent = `${p(now.getHours())}:${p(now.getMinutes())}:${p(now.getSeconds())} ${p(now.getDate())}/${p(
      now.getMonth() + 1
    )}/${now.getFullYear()}`;
  };
  updateClock();
  setInterval(updateClock, 1000);
}

function setupGlobalShortcuts() {
  document.addEventListener('keydown', (e) => {
    const tag = (e.target?.tagName || '').toLowerCase();
    const isInput = tag === 'input' || tag === 'textarea' || tag === 'select';

    const eventModal = document.getElementById('event-modal');
    const helpModal = document.getElementById('help-popover-modal');

    if (eventModal && eventModal.classList.contains('open')) {
      if (e.key === 'ArrowLeft' && !isInput) {
        e.preventDefault();
        stepFrame(-1);
      } else if (e.key === 'ArrowRight' && !isInput) {
        e.preventDefault();
        stepFrame(1);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        closeModal();
      }
      return;
    }

    if (helpModal && helpModal.classList.contains('open') && e.key === 'Escape') {
      e.preventDefault();
      closeHelpModal();
      return;
    }

    if (e.key === 'F1') {
      e.preventDefault();
      switchView('help');
    } else if (e.key === 'F11') {
      e.preventDefault();
      toggleAppFullscreen();
    } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'e') {
      e.preventDefault();
      exportEvents('csv');
    } else if (e.key === ' ' && !isInput) {
      const monitorPane = document.getElementById('view-monitor');
      if (monitorPane && monitorPane.classList.contains('active')) {
        e.preventDefault();
        const fileStatus = (monitorState.liveStatuses || []).find((s) => s.source_type === 'file');
        if (fileStatus && fileStatus.state === 'running') {
          togglePauseLive();
        } else {
          startLive();
        }
      }
    }
  });
}

// Gắn các hàm vào `window` để gọi từ thuộc tính HTML
Object.assign(window, {
  switchView,
  switchSourceMode,
  pickVideoFile,
  startLive,
  quickStartLive,
  togglePauseLive,
  stopLive,
  toggleCameraPicker,
  onCameraCheckChange,
  stopLiveSource,
  focusCamTile,
  discoverLanCams,
  addDiscoveredCam,
  addCameraUrl,
  openDatePicker,
  openEvidenceFolder,
  renameSourcePrompt,
  toggleQuickPolicyDrawer,
  toggleSoundQuick,
  pollLive,
  fetchAllData,
  fetchData: fetchAllData,
  refreshSourcesAndPolicies,
  loadPolicy: loadPolicyForCurrentSource,
  onPolicyCheckboxToggle,
  applyPolicyPreset,
  schedulePolicySave,
  renderEvents: renderEventsTable,
  renderEventsTable,
  resetEventFilters,
  changeEventsPage,
  exportEvents,
  viewEvent,
  selectFrame,
  stepFrame,
  toggleFalseAlarmSection,
  submitFeedback,
  closeModal,
  loadStatsView,
  saveSystemSettings,
  runCleanupOldData,
  openDataFolder,
  saveDiagnosticBundle,
  filterHelpTopics,
  openHelpModal,
  closeHelpModal,
  toggleAppFullscreen,
  isSessionFilterUntouched,
  onSessionFilterAutoChanged,
  onManualSessionFilterChange: () => {
    onSessionFilterAutoChanged(false);
    const el = document.getElementById('filter-session');
    if (el) {
      import('./events.js').then((m) => {
        m.eventsState.sessionFilterTouched = true;
        m.eventsState.currentPage = 1;
        m.renderEventsTable();
      });
    }
  },
});

window.addEventListener('DOMContentLoaded', async () => {
  startClockTicker();
  setupGlobalShortcuts();
  await initMonitorModule();
  await refreshSourcesAndPolicies();
  await loadSettingsAndSystemInfo();
  await fetchAllData();
  await pollLive();

  setInterval(fetchAllData, 3000);
  setInterval(pollLive, 1000);
});
