"""Bước 2: ByteTrack chỉ theo dõi hộp người (spec 5.1). Dùng BYTETracker của Ultralytics, không dùng model.track()."""

from types import SimpleNamespace

import numpy as np

from . import Track


class _Dets:
    """Đầu vào tối thiểu BYTETracker cần: conf, cls, xywh, xyxy, hỗ trợ lọc bằng mảng bool."""

    def __init__(self, xyxy, conf):
        self.xyxy = np.asarray(xyxy, dtype=np.float32).reshape(-1, 4)
        self.conf = np.asarray(conf, dtype=np.float32).reshape(-1)
        self.cls = np.zeros(len(self.conf), dtype=np.float32)
        xy = (self.xyxy[:, :2] + self.xyxy[:, 2:]) / 2
        self.xywh = np.concatenate([xy, self.xyxy[:, 2:] - self.xyxy[:, :2]], axis=1)

    def __len__(self):
        return len(self.conf)

    def __getitem__(self, idx):
        return _Dets(self.xyxy[idx], self.conf[idx])


class PersonTracker:
    def __init__(self, cfg):
        from ultralytics.trackers.byte_tracker import BYTETracker

        self.person_conf = cfg["detector"]["conf"]["person"]
        self.tracker = BYTETracker(SimpleNamespace(**cfg["tracker"]))
        # BYTETracker cấp số cho cả quỹ đạo thử chỉ sống 1 khung rồi bị bỏ, nên số nội bộ nhảy cóc.
        # Đổi sang số hiển thị liên tục theo thứ tự xuất hiện; không ảnh hưởng việc ghép.
        self.display_ids = {}

    def _display(self, tid):
        return self.display_ids.setdefault(int(tid), len(self.display_ids) + 1)

    def lost(self):
        """Quỹ đạo đang bị mất tạm (chưa quá track_buffer): [(track_id, hộp dự đoán)]. Chỉ để hiển thị;
        khung này không có quan sát nên không dùng để xác định trạng thái."""
        return [(self._display(s.track_id), np.asarray(s.xyxy, dtype=float)) for s in self.tracker.lost_stracks
                if int(s.track_id) in self.display_ids]

    def update(self, persons, frame=None):
        """Cập nhật với hộp người của khung hiện tại; trả về các Track được ghép ở khung này.

        Quỹ đạo chỉ còn trong bộ nhớ (bị mất tạm thời) không được trả về: khung này không có quan sát.
        `confident` = hộp người ghép được đạt ngưỡng conf person (spec 5.1: chỉ hộp này mới dùng xác định trạng thái).
        """
        dets = _Dets([p.xyxy for p in persons], [p.conf for p in persons])
        rows = self.tracker.update(dets, frame)
        tracks = []
        for row in rows:
            x1, y1, x2, y2, tid, _score, _cls, idx = row[:8]
            det = persons[int(idx)]
            tracks.append(Track(self._display(tid), np.array([x1, y1, x2, y2], dtype=float), det.conf,
                                det.conf >= self.person_conf))
        return tracks
