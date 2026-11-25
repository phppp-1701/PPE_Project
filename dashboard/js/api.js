/* ==========================================================================
   PPE MONITOR — LỚP GIAO TIẾP API, HẰNG SỐ NGHIỆP VỤ & TIỆN ÍCH GIAO DIỆN
   ========================================================================== */

export const API_BASE = window.location.protocol.startsWith('http')
  ? window.location.origin
  : 'http://127.0.0.1:8000';

export const PPE_KEYS = ['helmet', 'vest', 'gloves', 'goggles', 'boots'];

export const PPE_META = {
  helmet: {
    code: 'M',
    name: 'Mũ bảo hộ',
    region: 'Vùng đầu',
    rule: 'Chỉ tính mũ bảo hộ công nghiệp; bộ phân loại bác bỏ mũ thường khi nhìn thẳng.',
  },
  vest: {
    code: 'A',
    name: 'Áo phản quang',
    region: 'Vùng thân trên',
    rule: 'Áo bảo hộ / áo phản quang che phủ phần thân trên của người lao động.',
  },
  gloves: {
    code: 'G',
    name: 'Găng tay bảo hộ',
    region: 'Hai cổ tay (xét riêng từng tay)',
    rule: 'Xét độc lập tay trái và tay phải khi cổ tay nhìn rõ; một tay thiếu vẫn tính là thiếu găng.',
  },
  goggles: {
    code: 'K',
    name: 'Kính bảo hộ',
    region: 'Vùng mắt / mặt',
    rule: 'Chỉ tính kính bảo hộ đang đeo trên mắt; kính cận và kính râm thông thường không được tính.',
  },
  boots: {
    code: 'U',
    name: 'Ủng / Giày bảo hộ',
    region: 'Hai cổ chân (xét riêng từng chân)',
    rule: 'Chỉ tính ủng hoặc giày bảo hộ nhìn rõ; dép và giày vải thường bị bộ phân loại bác bỏ.',
  },
};

export const STATE_LABELS = {
  active: 'Đang vi phạm',
  pending_observation: 'Chờ quan sát',
  closed: 'Đã đóng',
};

export const CLOSE_REASON_LABELS = {
  recovered: 'Đã khắc phục đầy đủ',
  session_ended_unverified: 'Kết thúc phiên (chưa xác minh)',
  policy_changed: 'Đổi quy định PPE',
  app_crash_recovered: 'Đóng tự động khi khởi động lại',
};

export const HELP_TOPICS = {
  inspector: {
    title: 'Bảng Đối tượng trong khung hình',
    body: [
      'Hiển thị danh sách từng người đang được ByteTrack theo dõi trong khung hình hiện tại (mã ID chỉ có ý nghĩa tạm thời trong phiên, không lưu danh tính cá nhân).',
      'Mỗi người có 5 ô chỉ báo tương ứng M (Mũ), A (Áo), G (Găng), K (Kính), U (Ủng):',
      '• Đạt (Xanh lá): Hệ thống xác nhận người đó đang mang trang bị hợp lệ.',
      '• Thiếu (Đỏ): Vùng cơ thể nhìn rõ nhưng không có trang bị bảo hộ.',
      '• Khuất / Chưa rõ (Xám): Bộ phận bị che khuất, quay lưng hoặc ở quá xa — hệ thống không kết luận phạt oan.',
      '• Tắt (Mờ): Trang bị không nằm trong quy định bắt buộc của nguồn hiện tại.',
    ],
  },
  policy: {
    title: 'Quy định PPE bắt buộc theo nguồn',
    body: [
      'Mỗi nguồn (Webcam hoặc từng tệp Video) có quy định PPE bắt buộc riêng và được đánh số phiên bản tự động.',
      'Khi gạt công tắc hoặc chọn Mẫu thiết lập nhanh (Công trường, Hàn / mài, Kho bãi), thay đổi được áp dụng ngay lập tức ở khung hình kế tiếp.',
      'Nếu nguồn đang chạy, mọi sự kiện đang mở sẽ được đóng với lý do "Đổi quy định PPE" và bộ đếm cửa sổ thời gian sẽ tính lại từ đầu theo quy định mới.',
    ],
  },
  legend: {
    title: 'Quy ước màu sắc & ký hiệu trên khung hình',
    body: [
      'Khung chữ nhật quanh người và các nhãn chữ M / A / G / K / U trên luồng video tuân thủ quy tắc thống nhất toàn hệ thống:',
      '• Xanh lá: Đã trang bị đầy đủ (Có).',
      '• Đỏ: Phát hiện thiếu trang bị bắt buộc (Thiếu).',
      '• Trắng / Xám: Chưa đủ điều kiện quan sát để kết luận (bị che khuất, quá nhỏ, ngoài khung).',
      '• Khung người xanh dương: Người mới bước vào vùng quan sát, đang tích lũy cửa sổ thời gian.',
      '• Khung nét đứt xám: Đối tượng tạm thời mất dấu, đang giữ mã theo dõi.',
    ],
  },
  export: {
    title: 'Xuất dữ liệu CSV và gói ảnh minh chứng (ZIP)',
    body: [
      'Dữ liệu xuất ra tuân theo đúng các bộ lọc đang chọn trên màn hình Nhật ký vi phạm (Phiên, Nguồn, Trạng thái, Loại PPE, Khoảng thời gian).',
      '• Xuất CSV: Bảng dữ liệu mã hóa UTF-8 có BOM, mở trực tiếp bằng Microsoft Excel hiển thị đúng tiếng Việt.',
      '• Xuất ZIP: Bao gồm tệp events.csv kèm toàn bộ thư mục ảnh chụp minh chứng của các sự kiện tương ứng.',
    ],
  },
  device: {
    title: 'Thiết bị suy luận (GPU NVIDIA CUDA / CPU)',
    body: [
      'Hệ thống ưu tiên chạy mô hình YOLO11 và bộ phân loại trên GPU NVIDIA (CUDA) để đạt tốc độ thời gian thực (>= 20 FPS).',
      'Nếu máy tính không có GPU NVIDIA hoặc chọn chế độ CPU, hệ thống vẫn hoạt động đầy đủ chức năng nhưng tốc độ xử lý khung hình sẽ chậm hơn.',
    ],
  },
};

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`, { cache: 'no-store' });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Lỗi HTTP ${res.status}`);
  }
  return data;
}

export async function apiSend(path, method = 'POST', body = undefined) {
  const opts = {
    method,
    headers: {},
  };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Lỗi HTTP ${res.status}`);
  }
  return data;
}

export function fmtClock(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())} ${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`;
}

export function fmtTimeShort(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

export function fmtSeconds(sec) {
  const s = Math.max(0, Number(sec) || 0);
  const mins = Math.floor(s / 60);
  const rem = (s % 60).toFixed(1).padStart(4, '0');
  return `${String(mins).padStart(2, '0')}:${rem}`;
}

export function showToast(message, variant = 'info', actionLabel = null, onAction = null) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const item = document.createElement('div');
  item.className = `toast-item ${variant === 'danger' ? 'toast-danger' : variant === 'ok' ? 'toast-ok' : ''}`;

  const textSpan = document.createElement('span');
  textSpan.textContent = message;
  item.appendChild(textSpan);

  if (actionLabel && typeof onAction === 'function') {
    const btn = document.createElement('button');
    btn.className = 'btn btn-sm';
    btn.textContent = actionLabel;
    btn.onclick = () => {
      onAction();
      item.remove();
    };
    item.appendChild(btn);
  }

  container.appendChild(item);
  setTimeout(() => {
    if (item.parentNode) item.remove();
  }, 4500);
}

let audioCtx = null;
export function playAlertBeep() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    if (!audioCtx) audioCtx = new Ctx();
    if (audioCtx.state === 'suspended') audioCtx.resume();

    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.22);

    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.22);
  } catch (_) {
    // Bỏ qua nếu thiết bị âm thanh không sẵn sàng
  }
}

export function hasDesktopBridge() {
  return Boolean(window.pywebview && window.pywebview.api);
}

export async function toggleAppFullscreen() {
  if (hasDesktopBridge() && typeof window.pywebview.api.toggle_fullscreen === 'function') {
    await window.pywebview.api.toggle_fullscreen();
    return;
  }
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen?.().catch(() => {});
  } else {
    document.exitFullscreen?.().catch(() => {});
  }
}

export function openHelpModal(topicKey) {
  const topic = HELP_TOPICS[topicKey];
  if (!topic) return;
  const modal = document.getElementById('help-popover-modal');
  const titleEl = document.getElementById('help-popover-title');
  const bodyEl = document.getElementById('help-popover-body');
  if (!modal || !titleEl || !bodyEl) return;

  titleEl.textContent = topic.title;
  bodyEl.innerHTML = topic.body.map((line) => `<p style="margin-bottom: 8px; color: var(--text-secondary);">${line}</p>`).join('');
  modal.classList.add('open');
}

export function closeHelpModal() {
  const modal = document.getElementById('help-popover-modal');
  if (modal) modal.classList.remove('open');
}
