"""Cache model YOLO dùng chung giữa các camera (chạy nhiều camera cùng lúc).

Mỗi Pipeline trước đây tự load 5 bản model (detector + pose + 3 bộ phân loại bộ phận):
hai camera trở lên là tràn VRAM trên GPU 4GB. Model YOLO chỉ đọc khi predict nên các
camera có thể dùng chung một bản: cache theo đường dẫn trọng số, predict được khoá
theo model (GPU vốn chạy tuần tự nên khoá không làm mất throughput).
Không đổi kết quả nhận diện: cùng trọng số, cùng tham số, chỉ khác chỗ lưu model.
"""

import threading

_CACHE: dict = {}          # key (str đường dẫn trọng số) -> (model, lock)
_CACHE_LOCK = threading.Lock()


def get_model(loader, path):
    """Trả (model, lock) cho `path`; `loader()` chỉ được gọi lần đầu tiên."""
    key = str(path)
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is None:
            entry = (loader(), threading.Lock())
            _CACHE[key] = entry
        return entry


def predict(lock, model, *args, **kwargs):
    """Gọi model.predict dưới khoá để hai camera không chen nhau dùng cùng model."""
    with lock:
        return model.predict(*args, **kwargs)
