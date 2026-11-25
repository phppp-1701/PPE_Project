"""Đồng bộ đồng hồ camera Fofu = giờ máy tính (qua protocol CACS).

Camera này mất giờ khi mất điện/reset — OSD ghi nhầm ngày làm bản đồ minh chứng sai.
Chạy file này bất cứ lúc nào thấy giờ trên khung hình sai:
    python scripts/fofu_sync_time.py
Cần `mipc-camera-client==0.1.3` trong Python toàn cục (như bridge).
"""

import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from mipc_camera_client import MipcCameraClient
from mipc_camera_client.crypto_helpers import des_encrypt_password_hash

HOST = "192.168.1.202"
SN = "1jfiegbqnuu6a"
STORED_MD5 = "994b89017e4c7143ef7ff13a5901dbf7"  # md5(password) đã lưu từ web UI


def main():
    c = MipcCameraClient(HOST)
    c._r.headers["Referer"] = f"http://{HOST}/"
    print("1) DH key exchange ...")
    c.run_dh()
    print("2) login ...")
    resp = c.run_rpc("cacs_login_req", {
        "dlid": c.lid,
        "dnid": c._create_nid_ex(2),
        "duser": SN,
        "dpass": des_encrypt_password_hash(STORED_MD5, str(c.shared_secret)),
        "dsession_req": 1,
        "dparam__x_countz_": 1, "dparam": 1,
        "dparam_name": "spv", "dparam_value": "v1",
    })
    c._handle_login_response(resp)

    # gửi đúng lúc máy tính vừa sang giây mới để biên giây camera khớp PC
    time.sleep(1.0 - (time.time() % 1) + 0.05)
    t = time.localtime()
    r = c.run_rpc("ccm_date_set", {
        "dsess": 1, "dsess_nid": c.nid(), "dsess_sn": c.get_device_sn(),
        "dtype": 0, "dtimezone": 7,
        "dyear": t.tm_year, "dmon": t.tm_mon, "dday": t.tm_mday,
        "dhour": t.tm_hour, "dmin": t.tm_min, "dsec": t.tm_sec,
    })
    code = r.get("data", {}).get("ret", {}).get("code", "")
    print("3) ccm_date_set:", "OK" if code == "" else f"FAILED ({code})")
    print(f"   camera giờ = giờ PC: {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
