"""Bước 5: xác nhận theo thời gian (spec 5.4, mục 3.4.5). Cửa sổ tính theo giây, không theo số khung.

Chưa xác định được lưu nhưng không tính vào số quan sát hợp lệ, và không bao giờ là bằng chứng khắc phục.
"""

from collections import defaultdict, deque
from dataclasses import dataclass

from . import HAVE, MISSING, require


@dataclass
class Check:
    missing_confirmed: bool    # đủ điều kiện xác nhận thiếu ở thời điểm này
    recovered: bool            # đủ điều kiện xác nhận khắc phục ở thời điểm này
    valid_now: bool            # quan sát hiện tại là Có hoặc Thiếu
    since: float | None = None # thời điểm Thiếu sớm nhất trong cửa sổ T_on (start_time của sự kiện)


class TemporalConfirmer:
    def __init__(self, cfg=None, params=None):
        p = params or require(cfg, "temporal")
        self.T_on, self.T_off = float(p["T_on"]), float(p["T_off"])
        self.n_on, self.n_off = int(p["n_on"]), int(p["n_off"])
        self.theta_on, self.theta_off = float(p["theta_on"]), float(p["theta_off"])
        self.keep = max(self.T_on, self.T_off)
        # Tỉ lệ tối thiểu khung có kết luận (Có/Thiếu) trên mọi khung của người đó trong T_on; null = không xét.
        # Chặn trường hợp vài khung Thiếu lẻ giữa nhiều khung Chưa xác định vẫn đủ n_on để mở sự kiện.
        self.min_valid_frac_on = float(p.get("min_valid_frac_on") or 0.0)
        self.history = defaultdict(deque)       # (track_id, ppe) -> deque[(t, state)]

    @staticmethod
    def _counts(hist, t, window):
        have = miss = 0
        for ts, s in hist:
            if ts > t - window:
                have += s == HAVE
                miss += s == MISSING
        return have, miss

    def update(self, t, track_id, ppe, state):
        hist = self.history[(track_id, ppe)]
        hist.append((t, state))
        while hist and hist[0][0] <= t - self.keep:
            hist.popleft()
        have, miss = self._counts(hist, t, self.T_on)
        valid = have + miss
        total = sum(1 for ts, _ in hist if ts > t - self.T_on)
        missing = (state == MISSING and valid >= self.n_on and valid > 0 and miss / valid >= self.theta_on
                   and valid / total >= self.min_valid_frac_on)
        have, miss = self._counts(hist, t, self.T_off)
        valid = have + miss
        recovered = state == HAVE and valid >= self.n_off and valid > 0 and have / valid >= self.theta_off
        since = next((ts for ts, s in hist if ts > t - self.T_on and s == MISSING), None)
        return Check(missing, recovered, state in (HAVE, MISSING), since)

    def drop(self, track_id):
        for key in [k for k in self.history if k[0] == track_id]:
            del self.history[key]
