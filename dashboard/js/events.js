/* ==========================================================================
   PPE MONITOR — MODULE 2: NHẬT KÝ VI PHẠM, CHI TIẾT MINH CHỨNG & XUẤT DỮ LIỆU
   ========================================================================== */

import {
  API_BASE,
  CLOSE_REASON_LABELS,
  PPE_KEYS,
  PPE_META,
  apiGet,
  apiSend,
  fmtClock,
  hasDesktopBridge,
  showToast,
} from './api.js';
import { monitorState, renderLiveAlertFeed } from './monitor.js';

export const eventsState = {
  allEvents: [],
  sessions: [],
  currentPage: 1,
  pageSize: 50,
  sessionFilterTouched: false,
  currentEventData: null,
  currentFrameIdx: 0,
};

export function isSessionFilterUntouched() {
  return !eventsState.sessionFilterTouched;
}

export function onSessionFilterAutoChanged(resetTouch = false) {
  if (resetTouch) {
    eventsState.sessionFilterTouched = false;
  }
}

export async function loadEventsAndSessions() {
  try {
    const [eventsRes, sessionsRes] = await Promise.all([
      apiGet('/api/events?limit=500'),
      apiGet('/api/sessions?limit=60').catch(() => []),
    ]);
    eventsState.allEvents = eventsRes.events || [];
    eventsState.sessions = Array.isArray(sessionsRes) ? sessionsRes : [];

    populateSessionSelect();
    renderEventsTable();
    renderLiveAlertFeed(eventsState.allEvents);
  } catch (err) {
    console.error('Lỗi tải danh sách sự kiện:', err);
  }
}

function populateSessionSelect() {
  const sel = document.getElementById('filter-session');
  if (!sel) return;
  const currentVal = sel.value;

  const baseOptions = [
    `<option value="">Tất cả các phiên</option>`,
    `<option value="live">Phiên trực tiếp gần nhất</option>`,
  ];
  const sessionOptions = eventsState.sessions.map(
    (s) => `<option value="${s.session_id}">${s.session_id} (${s.event_count || 0} sự kiện)</option>`
  );
  sel.innerHTML = baseOptions.concat(sessionOptions).join('');

  if ([...sel.options].some((o) => o.value === currentVal)) {
    sel.value = currentVal;
  }
}

export function getFilteredEvents() {
  const srcFilter = document.getElementById('filter-source')?.value || '';
  const stateFilter = document.getElementById('filter-state')?.value || '';
  const ppeFilter = document.getElementById('filter-ppe')?.value || '';
  const sessionFilter = document.getElementById('filter-session')?.value || '';
  const dateFrom = document.getElementById('filter-date-from')?.value || '';
  const dateTo = document.getElementById('filter-date-to')?.value || '';
  const q = (document.getElementById('filter-q')?.value || '').trim().toLowerCase();

  return eventsState.allEvents.filter((ev) => {
    if (sessionFilter === 'live') {
      // nhiều camera cùng lúc: lấy sự kiện của mọi phiên đang chạy
      if (!monitorState.activeSessionIds.has(ev.session_id)) return false;
    } else if (sessionFilter && ev.session_id !== sessionFilter) {
      return false;
    }
    if (srcFilter && ev.source_id !== srcFilter) return false;
    if (stateFilter && ev.event_state !== stateFilter) return false;
    if (ppeFilter && !(ev.missing_items || []).includes(ppeFilter)) return false;
    if (dateFrom && (ev.system_time || '') < dateFrom) return false;
    if (dateTo && (ev.system_time || '') > `${dateTo}T23:59:59`) return false;
    if (q) {
      const hay = `${ev.event_id} ${ev.session_id} ${ev.source_id} ${ev.track_id}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

export function resetEventFilters() {
  ['filter-source', 'filter-state', 'filter-ppe', 'filter-date-from', 'filter-date-to', 'filter-q'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const ses = document.getElementById('filter-session');
  if (ses) ses.value = '';
  eventsState.sessionFilterTouched = true;
  eventsState.currentPage = 1;
  renderEventsTable();
}

export function changeEventsPage(delta) {
  const filtered = getFilteredEvents();
  const totalPages = Math.max(1, Math.ceil(filtered.length / eventsState.pageSize));
  const next = Math.min(totalPages, Math.max(1, eventsState.currentPage + delta));
  eventsState.currentPage = next;
  renderEventsTable();
}

export function renderEventsTable() {
  const tbody = document.getElementById('events-tbody');
  if (!tbody) return;

  const sessionFilter = document.getElementById('filter-session')?.value || '';
  const filtered = getFilteredEvents();
  const total = filtered.length;
  const totalPages = Math.max(1, Math.ceil(total / eventsState.pageSize));
  if (eventsState.currentPage > totalPages) {
    eventsState.currentPage = totalPages;
  }

  const pageInfo = document.getElementById('events-page-info');
  const prevBtn = document.getElementById('events-prev-btn');
  const nextBtn = document.getElementById('events-next-btn');
  if (pageInfo) {
    pageInfo.textContent = `Hiển thị ${total ? (eventsState.currentPage - 1) * eventsState.pageSize + 1 : 0}–${Math.min(
      total,
      eventsState.currentPage * eventsState.pageSize
    )} / ${total} sự kiện (Trang ${eventsState.currentPage}/${totalPages})`;
  }
  if (prevBtn) prevBtn.disabled = eventsState.currentPage <= 1;
  if (nextBtn) nextBtn.disabled = eventsState.currentPage >= totalPages;

  if (!filtered.length) {
    const emptyText =
      sessionFilter === 'live'
        ? monitorState.liveSessionId
          ? `Chưa có sự kiện vi phạm nào trong phiên ${monitorState.liveSessionId}.`
          : 'Chưa có phiên trực tiếp đang mở. Chọn "Tất cả các phiên" để tra cứu toàn bộ lịch sử.'
        : 'Không có sự kiện vi phạm nào khớp với bộ lọc hiện tại.';
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 32px;">${emptyText}</td></tr>`;
    return;
  }

  const startIdx = (eventsState.currentPage - 1) * eventsState.pageSize;
  const pageRows = filtered.slice(startIdx, startIdx + eventsState.pageSize);

  tbody.innerHTML = pageRows
    .map((ev) => {
      let stateBadge = '';
      if (ev.event_state === 'active') {
        stateBadge = `<span class="badge badge-danger">Đang vi phạm</span>`;
      } else if (ev.event_state === 'pending_observation') {
        stateBadge = `<span class="badge badge-warn">Chờ quan sát</span>`;
      } else {
        stateBadge = `<span class="badge badge-ok">Đã đóng</span>`;
      }

      const ppeBadges =
        ev.missing_items && ev.missing_items.length
          ? ev.missing_items
              .map((it) => `<span class="badge badge-neutral"><strong class="mono">${PPE_META[it]?.code || it}</strong> ${PPE_META[it]?.name || it}</span>`)
              .join(' ')
          : `<span class="badge badge-warn">Đã khắc phục mục thiếu, chờ xác minh mục còn lại</span>`;

      const closeText = CLOSE_REASON_LABELS[ev.close_reason] || ev.close_reason || '—';
      const duration = ((ev.end_time || ev.last_seen_time || ev.confirmed_at) - ev.start_time).toFixed(1);

      const thumbUrl = ev.thumbnail_url
        ? ev.thumbnail_url.startsWith('http')
          ? ev.thumbnail_url
          : `${API_BASE}${ev.thumbnail_url}`
        : '';
      const thumbHtml = thumbUrl
        ? `<img src="${thumbUrl}" alt="Minh chứng" style="width: 72px; height: 46px; object-fit: cover; border-radius: 3px; border: 1px solid var(--border-main); cursor: pointer; display: block;" onclick="window.viewEvent('${ev.event_id}')">`
        : `<span style="color: var(--text-dim); font-size: 11px;">Không ảnh</span>`;

      let fbBadge = `<span style="color: var(--text-dim); font-size: 11.5px;">Chưa đánh giá</span>`;
      if (ev.feedback === 'correct') {
        fbBadge = `<span class="badge badge-ok">Báo đúng</span>`;
      } else if (ev.feedback === 'false_alarm') {
        fbBadge = `<span class="badge badge-danger">Báo sai</span>`;
      }

      return `
        <tr>
          <td style="width: 84px;">${thumbHtml}</td>
          <td class="mono">
            <div style="font-weight: 600; color: #fff;">${fmtClock(ev.system_time)}</div>
            <div style="font-size: 11.5px; color: var(--text-muted);">Mốc ${ev.confirmed_at.toFixed(1)}s · Kéo dài ${duration}s</div>
          </td>
          <td>
            <div style="font-weight: 500; color: var(--text-secondary);">${ev.source_id}</div>
            <div class="mono" style="font-size: 11px; color: var(--text-muted);">${ev.session_id}</div>
          </td>
          <td class="mono"><strong style="color: var(--accent-light);">Người #${String(ev.track_id).padStart(2, '0')}</strong></td>
          <td>${ppeBadges}</td>
          <td>${stateBadge}</td>
          <td style="font-size: 12px; color: var(--text-muted);">${closeText}</td>
          <td>${fbBadge}</td>
          <td>
            <button class="btn btn-sm" onclick="window.viewEvent('${ev.event_id}')">Xem minh chứng</button>
          </td>
        </tr>
      `;
    })
    .join('');
}

export async function exportEvents(kind = 'csv') {
  const srcFilter = document.getElementById('filter-source')?.value || '';
  const stateFilter = document.getElementById('filter-state')?.value || '';
  const ppeFilter = document.getElementById('filter-ppe')?.value || '';
  const sessionFilterRaw = document.getElementById('filter-session')?.value || '';
  const sessionFilter = sessionFilterRaw === 'live' ? monitorState.liveSessionId || '' : sessionFilterRaw;
  const dateFrom = document.getElementById('filter-date-from')?.value || '';
  const dateTo = document.getElementById('filter-date-to')?.value || '';
  const q = (document.getElementById('filter-q')?.value || '').trim();

  const params = new URLSearchParams();
  if (srcFilter) params.set('source_id', srcFilter);
  if (sessionFilter) params.set('session_id', sessionFilter);
  if (stateFilter) params.set('state', stateFilter);
  if (ppeFilter) params.set('ppe', ppeFilter);
  if (dateFrom) params.set('date_from', dateFrom);
  if (dateTo) params.set('date_to', dateTo);
  if (q) params.set('q', q);

  const endpoint = kind === 'zip' ? '/api/export/events.zip' : '/api/export/events.csv';
  const queryStr = params.toString();
  const fullUrl = `${API_BASE}${endpoint}${queryStr ? `?${queryStr}` : ''}`;

  const now = new Date();
  const p = (n) => String(n).padStart(2, '0');
  const stamp = `${now.getFullYear()}${p(now.getMonth() + 1)}${p(now.getDate())}_${p(now.getHours())}${p(now.getMinutes())}`;
  const defaultName = kind === 'zip' ? `ppe_events_evidence_${stamp}.zip` : `ppe_events_${stamp}.csv`;

  if (hasDesktopBridge() && typeof window.pywebview.api.export_from_url === 'function') {
    try {
      const savedPath = await window.pywebview.api.export_from_url(fullUrl, defaultName, kind);
      if (savedPath) {
        showToast(`Đã xuất dữ liệu tại: ${savedPath}`, 'ok', 'Mở thư mục', () => {
          window.pywebview.api.open_folder(savedPath);
        });
      }
    } catch (err) {
      showToast(`Lỗi xuất tệp: ${err.message}`, 'danger');
    }
    return;
  }

  // Chế độ trình duyệt web thông thường
  window.open(fullUrl, '_blank');
  showToast(`Đang tải xuống ${defaultName}…`, 'ok');
}

/* ==========================================================================
   MODAL CHI TIẾT MINH CHỨNG & PHẢN HỒI GIÁM SÁT VIÊN
   ========================================================================== */

export async function viewEvent(eventId) {
  try {
    const data = await apiGet(`/api/events/${encodeURIComponent(eventId)}`);
    let rawFrames = Array.isArray(data.frames) && data.frames.length > 0 ? data.frames : [];
    if (rawFrames.length === 0 && Array.isArray(data.evidence) && data.evidence.length > 0) {
      rawFrames = data.evidence.map((ev, i) => ({
        index: i,
        t: ev.t,
        label: `Mốc ${typeof ev.t === 'number' ? ev.t.toFixed(2) : ev.t}s: Xác nhận vi phạm`,
        url: ev.url,
        missing_items: data.missing_items || [],
      }));
    }
    data.frames = rawFrames;
    eventsState.currentEventData = data;

    const titleEl = document.getElementById('modal-title');
    const subEl = document.getElementById('modal-subtitle');
    if (titleEl) {
      titleEl.textContent = `Chi tiết sự kiện vi phạm — Người #${String(data.track_id).padStart(2, '0')} (tạm thời trong phiên)`;
    }
    if (subEl) {
      subEl.textContent = `Mã sự kiện: ${data.event_id} | Nguồn: ${data.source_id} | Phiên: ${data.session_id} | Thời điểm: ${data.start_time.toFixed(
        2
      )}s – ${(data.end_time || data.last_seen_time).toFixed(2)}s (Quy định v${data.policy_version})`;
    }

    // Đặt lại biểu mẫu đánh giá
    const radCorrect = document.querySelector('input[name="fb_type"][value="correct"]');
    if (radCorrect) radCorrect.checked = true;
    toggleFalseAlarmSection();
    const notesEl = document.getElementById('fb-notes');
    if (notesEl) notesEl.value = '';
    PPE_KEYS.forEach((p) => {
      const chk = document.getElementById(`fa-${p}`);
      if (chk) chk.checked = false;
    });

    // Dải khung hình theo mốc thời gian
    const ribbon = document.getElementById('modal-frames-ribbon');
    if (ribbon) {
      if (rawFrames.length > 0) {
        ribbon.innerHTML = rawFrames
          .map((f, idx) => {
            const tVal = typeof f.t === 'number' ? f.t.toFixed(2) : f.t;
            const itemsCnt = f.missing_items ? f.missing_items.length : 0;
            return `
              <button class="frame-tab mono ${idx === 0 ? 'active' : ''}" id="frame-btn-${idx}" onclick="window.selectFrame(${idx})">
                <span>t = ${tVal}s</span>
                <span class="badge ${itemsCnt > 0 ? 'badge-danger' : 'badge-ok'}">${itemsCnt > 0 ? `Thiếu ${itemsCnt}` : 'Đủ'}</span>
              </button>
            `;
          })
          .join('');
        eventsState.currentFrameIdx = 0;
        selectFrame(0);
      } else {
        ribbon.innerHTML = `<span style="color: var(--text-muted); font-size: 12px;">Không có khung hình minh chứng</span>`;
        const wrap = document.getElementById('modal-img-wrap');
        if (wrap) wrap.innerHTML = `<div style="color: var(--text-muted);">Không có tệp ảnh minh chứng</div>`;
        const info = document.getElementById('current-frame-info');
        if (info) info.textContent = '';
      }
    }

    // Dòng thời gian (Timeline)
    const timeline = document.getElementById('modal-timeline');
    if (timeline) {
      timeline.innerHTML = (data.history || [])
        .map((h) => {
          const itemsText =
            (h.missing_items || []).map((i) => PPE_META[i]?.name || i).join(', ') ||
            'Không còn mục thiếu (chờ xác minh trang bị chưa nhìn thấy)';
          return `
            <div class="timeline-node">
              <div class="mono" style="font-size: 11.5px; color: var(--text-muted);">t = ${Number(h.t).toFixed(2)}s (${h.change_type})</div>
              <div style="font-size: 12.5px; margin-top: 2px;">Trang bị thiếu: <strong>${itemsText}</strong></div>
            </div>
          `;
        })
        .join('');
    }

    renderFeedbackHistory(data.feedbacks || []);

    const modal = document.getElementById('event-modal');
    if (modal) modal.classList.add('open');
  } catch (err) {
    showToast(`Không tải được chi tiết sự kiện: ${err.message}`, 'danger');
  }
}

export function selectFrame(idx) {
  const data = eventsState.currentEventData;
  if (!data || !data.frames || !data.frames[idx]) return;
  eventsState.currentFrameIdx = idx;

  document.querySelectorAll('.frame-tab').forEach((btn, i) => {
    btn.classList.toggle('active', i === idx);
  });

  const frame = data.frames[idx];
  const imgWrap = document.getElementById('modal-img-wrap');
  const infoWrap = document.getElementById('current-frame-info');

  if (imgWrap) {
    if (frame && frame.url) {
      const fullUrl = frame.url.startsWith('http') ? frame.url : `${API_BASE}${frame.url}`;
      imgWrap.innerHTML = `<img src="${fullUrl}" alt="${frame.label}">`;
    } else {
      imgWrap.innerHTML = `<div style="color: var(--text-muted);">Không tìm thấy tệp ảnh cho mốc thời gian này</div>`;
    }
  }

  if (infoWrap) {
    const ppeBadges =
      frame.missing_items && frame.missing_items.length > 0
        ? frame.missing_items.map((i) => `<span class="badge badge-danger">${PPE_META[i]?.name || i}</span>`).join(' ')
        : `<span class="badge badge-ok">Đủ trang bị</span>`;
    infoWrap.innerHTML = `
      <div><strong>${frame.label}</strong></div>
      <div>Trang bị thiếu tại mốc này: ${ppeBadges}</div>
    `;
  }
}

export function stepFrame(delta) {
  const data = eventsState.currentEventData;
  if (!data || !data.frames || !data.frames.length) return;
  const next = Math.min(data.frames.length - 1, Math.max(0, eventsState.currentFrameIdx + delta));
  selectFrame(next);
}

export function toggleFalseAlarmSection() {
  const checked = document.querySelector('input[name="fb_type"]:checked');
  const isFalse = checked && checked.value === 'false_alarm';
  const wrap = document.getElementById('false-alarm-items-wrap');
  if (wrap) {
    wrap.style.display = isFalse ? 'block' : 'none';
  }
}

export async function submitFeedback() {
  const data = eventsState.currentEventData;
  if (!data) return;

  const fbType = document.querySelector('input[name="fb_type"]:checked')?.value || 'correct';
  const notes = (document.getElementById('fb-notes')?.value || '').trim();
  const falseAlarmItems = [];
  if (fbType === 'false_alarm') {
    PPE_KEYS.forEach((p) => {
      const el = document.getElementById(`fa-${p}`);
      if (el && el.checked) falseAlarmItems.push(p);
    });
  }

  try {
    const res = await apiSend(`/api/events/${encodeURIComponent(data.event_id)}/feedback`, 'POST', {
      feedback_type: fbType,
      false_alarm_items: falseAlarmItems,
      notes,
    });
    showToast(res.message || 'Đã lưu đánh giá sự kiện.', 'ok');
    const refreshed = await apiGet(`/api/events/${encodeURIComponent(data.event_id)}`);
    eventsState.currentEventData.feedbacks = refreshed.feedbacks || [];
    renderFeedbackHistory(refreshed.feedbacks || []);
    const notesEl = document.getElementById('fb-notes');
    if (notesEl) notesEl.value = '';
    loadEventsAndSessions();
    if (window.loadStatsView) window.loadStatsView();
  } catch (err) {
    showToast(`Lỗi lưu đánh giá: ${err.message}`, 'danger');
  }
}

function renderFeedbackHistory(feedbacks) {
  const container = document.getElementById('fb-history-list');
  if (!container) return;
  if (!feedbacks || feedbacks.length === 0) {
    container.innerHTML = `<span style="color: var(--text-dim); font-size: 12px;">Chưa có đánh giá nào cho sự kiện này.</span>`;
    return;
  }
  container.innerHTML = feedbacks
    .map((f) => {
      const badge =
        f.feedback_type === 'correct'
          ? `<span class="badge badge-ok">Cảnh báo đúng</span>`
          : `<span class="badge badge-danger">Cảnh báo sai</span>`;
      const items =
        f.false_alarm_items && f.false_alarm_items.length > 0
          ? `<span style="color: var(--text-secondary); font-size: 11.5px;">Phạt nhầm: ${f.false_alarm_items
              .map((p) => PPE_META[p]?.name || p)
              .join(', ')}</span>`
          : '';
      const timeStr = f.system_time ? f.system_time.replace('T', ' ').substring(0, 19) : '';
      return `
        <div style="background: var(--bg-input); padding: 7px 10px; border-radius: 4px; border: 1px solid var(--border-subtle); font-size: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
            <div style="display: flex; align-items: center; gap: 6px;">${badge} ${items}</div>
            <span class="mono" style="color: var(--text-dim); font-size: 11px;">${timeStr}</span>
          </div>
          ${f.notes ? `<div style="color: var(--text-secondary);">${f.notes}</div>` : ''}
        </div>
      `;
    })
    .join('');
}

export function closeModal() {
  const modal = document.getElementById('event-modal');
  if (modal) modal.classList.remove('open');
}
