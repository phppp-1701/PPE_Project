"""Nối các bước thành một vòng lặp xử lý khung hình (spec 5.6, Bảng 3.6). Camera và video dùng chung.

`stage` cho phép chạy tới một bước nhất định khi các bước sau còn tham số null:
    detect < track < associate < comply < full (thêm cửa sổ thời gian và sự kiện).
Ghi thời gian từng bước (ms) cho mỗi khung.
"""

import time

from . import ROOT, load_config
from .association import Associator
from .compliance import Compliance
from .detector import Detector
from .events import EventManager
from .temporal import TemporalConfirmer
from .tracker import PersonTracker

STAGES = ["detect", "track", "associate", "comply", "full"]


class Pipeline:
    def __init__(self, source_id, session_id, stage="full", cfg=None, on_event=None, required_ppe=None):
        self.cfg = cfg or load_config()
        self.stage = STAGES.index(stage)
        self.required = list(required_ppe or self.cfg["required_ppe"])
        self.detector = Detector(self.cfg, ROOT)
        self.tracker = PersonTracker(self.cfg) if self.stage >= 1 else None
        self.associator = Associator(self.cfg) if self.stage >= 2 else None
        self.compliance = Compliance(self.cfg) if self.stage >= 3 else None
        if self.stage >= 4:
            self.temporal = TemporalConfirmer(self.cfg)
            self.events = EventManager(source_id, session_id, self.required,
                                       ROOT / self.cfg["events"]["evidence_dir"], on_change=on_event)

    def process(self, frame, t):
        """Xử lý một khung ở thời điểm t (giây). Trả về dict kết quả của các bước đã chạy và thời gian từng bước."""
        out, timing = {"t": t}, {}

        def timed(name, fn, *args):
            s = time.perf_counter()
            r = fn(*args)
            timing[name] = (time.perf_counter() - s) * 1000
            return r

        out["persons"], out["ppe"] = timed("detector", self.detector, frame)
        if self.stage >= 1:
            out["tracks"] = timed("tracker", self.tracker.update, out["persons"], frame)
            out["lost"] = self.tracker.lost()
        if self.stage >= 2:
            out["assoc"] = timed("association", self.associator, out["tracks"], out["ppe"])
        if self.stage >= 3:
            out["states"] = timed("compliance", self.compliance, out["tracks"], out["assoc"], frame.shape, self.required)
        if self.stage >= 4:
            def temporal_and_events():
                checks_all = {}
                for tr in out["tracks"]:
                    st = out["states"][tr.track_id]
                    checks = {p: self.temporal.update(t, tr.track_id, p, st[p]["state"]) for p in self.required}
                    checks_all[tr.track_id] = checks
                    self.events.update(t, tr.track_id, checks, frame, tr.xyxy)
                self.events.absent(t, {tr.track_id for tr in out["tracks"]})
                return checks_all
            out["checks"] = timed("temporal_events", temporal_and_events)
        out["timing"] = timing
        return out

    def close(self, t):
        """Kết thúc phiên: đóng sự kiện chưa có bằng chứng khắc phục (session_ended_unverified)."""
        if self.stage >= 4:
            self.events.end_session(t)
