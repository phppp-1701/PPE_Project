"""Bước 6: vòng đời sự kiện vi phạm và minh chứng (spec 5.5, mục 3.4.6; trường sự kiện theo Bảng 3.7).

Mỗi (source_id, session_id, track_id) có tối đa một sự kiện đang mở; PPE không nằm trong khóa.
Đóng `recovered` chỉ khi mọi PPE bắt buộc đạt điều kiện khắc phục (missing_items rỗng chưa đủ).
"""

import copy
import uuid
from pathlib import Path

ACTIVE, PENDING, CLOSED = "active", "pending_observation", "closed"


class EventManager:
    def __init__(self, source_id, session_id, required_ppe, evidence_dir=None, policy_version=1, on_change=None):
        self.source_id, self.session_id = source_id, session_id
        self.required = list(required_ppe)
        self.evidence_dir = Path(evidence_dir) / session_id if evidence_dir else None
        self.policy_version = policy_version
        self.on_change = on_change              # hàm nhận (loại thay đổi, bản sao sự kiện), vd. ghi file / gửi backend
        self.open = {}                          # track_id -> sự kiện đang mở
        self.closed = []

    def _emit(self, kind, ev):
        ev["history"].append({"t": ev["last_change_time"], "change": kind, "missing_items": list(ev["missing_items"])})
        if self.on_change:
            self.on_change(kind, copy.deepcopy(ev))

    def _evidence(self, ev, frame, box, t):
        """Lưu tệp trước, rồi mới ghi đường dẫn vào sự kiện (spec mục 6)."""
        if frame is None or self.evidence_dir is None:
            return
        import cv2

        img = frame.copy()
        x1, y1, x2, y2 = [int(v) for v in box]
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
        cv2.putText(img, f"ID {ev['track_id']} thieu: {','.join(ev['missing_items'])}", (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        path = self.evidence_dir / f"{ev['event_id']}_{len(ev['evidence_refs'])}.jpg"
        if cv2.imwrite(str(path), img):
            ev["evidence_refs"].append({"t": t, "path": str(path)})

    def update(self, t, track_id, checks, frame=None, box=None):
        """checks: {ppe: temporal.Check} của người này ở thời điểm t (chỉ gọi khi người có mặt ở khung)."""
        confirmed = [p for p in self.required if checks[p].missing_confirmed]
        ev = self.open.get(track_id)
        if ev is None:
            if confirmed:
                starts = [checks[p].since for p in confirmed if checks[p].since is not None]
                ev = dict(event_id=str(uuid.uuid4()), source_id=self.source_id, session_id=self.session_id,
                          track_id=track_id, start_time=min(starts) if starts else t, confirmed_at=t,
                          last_seen_time=t, missing_items=sorted(confirmed), event_state=ACTIVE, end_time=None,
                          close_reason=None, evidence_refs=[], policy_version=self.policy_version,
                          history=[], last_change_time=t)
                self.open[track_id] = ev
                self._evidence(ev, frame, box, t)
                self._emit("created", ev)
            return ev

        changed = []
        if any(checks[p].valid_now for p in self.required):
            ev["last_seen_time"] = t
            if ev["event_state"] == PENDING:
                ev["event_state"] = ACTIVE
                changed.append("active")
        elif ev["event_state"] == ACTIVE:
            ev["event_state"] = PENDING                       # không có quan sát hợp lệ mới; không có timeout
            changed.append("pending_observation")
        added = [p for p in confirmed if p not in ev["missing_items"]]
        removed = [p for p in ev["missing_items"] if checks[p].recovered]
        if added or removed:
            ev["missing_items"] = sorted((set(ev["missing_items"]) | set(added)) - set(removed))
            changed.append("missing_items")
            if added:
                self._evidence(ev, frame, box, t)
        if all(checks[p].recovered for p in self.required):
            self._close(ev, t, "recovered")
            return ev
        if changed:
            ev["last_change_time"] = t
            self._emit("+".join(changed), ev)
        return ev

    def absent(self, t, present_ids):
        """Người có sự kiện đang mở nhưng không xuất hiện ở khung này -> chờ quan sát (giữ kết quả gần nhất)."""
        for tid, ev in self.open.items():
            if tid not in present_ids and ev["event_state"] == ACTIVE:
                ev["event_state"] = PENDING
                ev["last_change_time"] = t
                self._emit("pending_observation", ev)

    def _close(self, ev, t, reason):
        ev.update(event_state=CLOSED, end_time=t, close_reason=reason, last_change_time=t)
        del self.open[ev["track_id"]]
        self.closed.append(ev)
        self._emit("closed", ev)

    def end_session(self, t, reason="session_ended_unverified"):
        """Kết thúc phiên (hết video / dừng camera) hoặc đổi PPE bắt buộc áp dụng ngay (reason="policy_changed")."""
        for ev in list(self.open.values()):
            self._close(ev, t, reason)
