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
from .parts import PartClassifier
from .pose import PoseEstimator
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
        use_pose = self.stage >= 2 and self.cfg.get("pose", {}).get("enabled")
        self.pose = PoseEstimator(self.cfg, ROOT) if use_pose else None
        use_parts = use_pose and self.stage >= 3 and (self.cfg.get("part_cls") or {}).get("enabled")
        self.parts = PartClassifier(self.cfg, ROOT) if use_parts else None
        self.associator = Associator(self.cfg) if self.stage >= 2 else None
        self.compliance = Compliance(self.cfg) if self.stage >= 3 else None
        if self.stage >= 4:
            self.temporal = TemporalConfirmer(self.cfg)
            self.events = EventManager(source_id, session_id, self.required,
                                       ROOT / self.cfg["events"]["evidence_dir"], on_change=on_event,
                                       evidence_interval_s=self.cfg["events"].get("evidence_interval_s", 0.0),
                                       evidence_max=self.cfg["events"].get("evidence_max", 0))

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
        if self.pose:
            timed("pose", self.pose, frame, out["tracks"])
        if self.parts:
            timed("parts", self.parts, frame, out["tracks"])
        if self.stage >= 2:
            out["assoc"] = timed("association", self.associator, out["tracks"], out["ppe"], frame.shape)
        if self.stage >= 3:
            out["states"] = timed("compliance", self.compliance, out["tracks"], out["assoc"], frame.shape, self.required, t)
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

    def set_required(self, required_ppe, policy_version, t):
        """Đổi PPE bắt buộc khi đang chạy (camera trực tiếp, FR-10), áp dụng ngay:
        đóng mọi sự kiện đang mở với lý do policy_changed, xóa lịch sử cửa sổ thời gian (đếm lại từ đầu theo danh sách
        mới), rồi dùng danh sách mới cho các khung sau. Chạy video không gọi hàm này."""
        known = set(self.cfg["ppe"])
        bad = [p for p in required_ppe if p not in known]
        if bad:
            raise ValueError(f"PPE không có trong configs/pipeline.yaml: {bad}")
        self.required = [p for p in self.cfg["ppe"] if p in set(required_ppe)]   # giữ thứ tự cố định của cấu hình
        if self.stage >= 4:
            self.events.end_session(t, reason="policy_changed")
            self.events.required = list(self.required)
            self.events.policy_version = policy_version
            self.temporal.history.clear()

    def close(self, t):
        """Kết thúc phiên: đóng sự kiện chưa có bằng chứng khắc phục (session_ended_unverified)."""
        if self.stage >= 4:
            self.events.end_session(t)
