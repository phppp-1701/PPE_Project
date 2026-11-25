"""Worker dò webcam chạy trong TIỂU TRÌNH RIÊNG (backend/camera_probe_worker.py).

OpenCV DirectShow trên Windows thỉnh thoảng segfault khi mở/thả webcam trong cùng
tiến trình với luồng đang ghi hình — crash đó giết cả app. Chạy probe ở đây thì
crash (nếu có) chỉ chết worker, app gốc vẫn sống và dùng kết quả dò lần trước.

Cách gọi:  python camera_probe_worker.py <max_index> '<json danh sách index cần bỏ qua>'
Kết quả:   in ra stdout một dòng JSON [{"index": 0, "width": 640, "height": 480}, ...]
"""

import json
import sys


def main():
    max_index = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    skip = set(json.loads(sys.argv[2])) if len(sys.argv) > 2 else set()

    import cv2

    out = []
    for idx in range(max_index + 1):
        if idx in skip:
            continue
        cap = None
        try:
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap is not None and cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
                out.append({"index": idx, "width": w, "height": h})
        except Exception:
            pass
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
    print(json.dumps(out))


if __name__ == "__main__":
    main()
