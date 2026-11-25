"""Lớp hiển thị (A2, docs/experiments/2026-11-25_close_range_fixes.md): làm mượt trạng thái PPE vẽ trên người.

Chỉ để vẽ (video đã vẽ, camera trực tiếp). Không đổi trạng thái từng khung, cửa sổ thời gian, sự kiện hay chỉ số.
Khung hiện tại là Chưa xác định mà trong `hold_s` giây gần nhất đã có trạng thái chắc chắn (Có hoặc Thiếu) thì hiển thị trạng
thái đó; Có và Thiếu hiển thị ngay khi xuất hiện.
"""

from . import UNKNOWN


class DisplaySmoother:
    def __init__(self, hold_s):
        self.hold_s = float(hold_s)
        self.last = {}          # (track_id, ppe) -> (t, trạng thái chắc chắn)

    def __call__(self, t, states):
        """states: {track_id: {ppe: {"state": ...}}} -> {track_id: {ppe: trạng thái hiển thị}}."""
        out = {}
        for tid, per in states.items():
            row = {}
            for name, v in per.items():
                st, key = v["state"], (tid, name)
                if st != UNKNOWN:
                    self.last[key] = (t, st)
                    row[name] = st
                elif key in self.last and t is not None and t - self.last[key][0] <= self.hold_s:
                    row[name] = self.last[key][1]
                else:
                    row[name] = UNKNOWN
            out[tid] = row
        return out
