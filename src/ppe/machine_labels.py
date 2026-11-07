"""Quy trình máy gán nhãn trước, người kiểm định sau. Nhãn máy không phải nhãn người và không bao giờ vào human_review.csv.

Trạng thái một hộp hoặc ảnh, không trộn lẫn:
    machine_labeled   có nhãn máy nhưng hai lượt khác nhau hoặc mới có một lượt, chưa dùng cho val, test
    machine_consensus hai lượt máy giống nhau
    human_audited     người đã xem hộp này trong gói kiểm định
    human_reviewed    người đã duyệt hộp này ở luồng human_review.csv
"""

import csv
import random
import re
from collections import Counter, defaultdict

from ppe.ppe6_data import wilson

MACHINE_LABELED, MACHINE_CONSENSUS, HUMAN_AUDITED, HUMAN_REVIEWED = "machine_labeled", "machine_consensus", "human_audited", "human_reviewed"
STATUSES = (MACHINE_LABELED, MACHINE_CONSENSUS, HUMAN_AUDITED, HUMAN_REVIEWED)
REPORT_NOTE = "nhãn máy, có kiểm định mẫu của người"
MACHINE_NAME = re.compile(r"^machine_pass_[a-z]$")
PASS_FIELDS = ["labeler", "guide_version", "labeled_at", "task", "kind", "id", "decision", "person_ok", "image_result", "reason"]
DECISIONS = ("safety", "ordinary", "unclear", "ignore")
PERSON = ("du_lon", "qua_nho", "khong_ro")
IMAGE_RESULTS = ("no_missing", "missing_box", "reject")


def is_machine_name(name):
    return bool(MACHINE_NAME.match(name.strip().lower())) or name.strip().lower().startswith("machine")


def check_labeler(name):
    """Tên ở file nhãn máy phải là tên lượt máy, không phải tên người."""
    if not MACHINE_NAME.match(name):
        raise ValueError(f"Nhãn máy phải mang tên lượt máy, không dùng: {name}")


def check_pass_row(r):
    """Một dòng nhãn máy hợp lệ, trả về danh sách lỗi."""
    bad = []
    if not MACHINE_NAME.match(r.get("labeler", "")):
        bad.append("labeler")
    if r["kind"] == "box":
        if r["decision"] not in DECISIONS:
            bad.append("decision")
        if r["person_ok"] and r["person_ok"] not in PERSON:
            bad.append("person_ok")
    elif r["kind"] == "image":
        if r["image_result"] not in IMAGE_RESULTS:
            bad.append("image_result")
    else:
        bad.append("kind")
    return bad


def merge_passes(a, b):
    """a, b: {(task, kind, id): dòng}. Giống nhau ở mọi trường mới là machine_consensus. Thiếu một lượt thì là machine_labeled."""
    rows = []
    for k in sorted(set(a) | set(b)):
        x, y = a.get(k), b.get(k)
        fields = ("decision", "person_ok") if k[1] == "box" else ("image_result",)
        same = bool(x and y) and all(x[f] == y[f] for f in fields)
        diff = [] if same or not (x and y) else [f for f in fields if x[f] != y[f]]
        rows.append(dict(task=k[0], kind=k[1], id=k[2], status=MACHINE_CONSENSUS if same else MACHINE_LABELED, differ="+".join(diff) or ("" if same else "thieu_luot"),
                         decision_a=(x or {}).get("decision", ""), decision_b=(y or {}).get("decision", ""), person_a=(x or {}).get("person_ok", ""), person_b=(y or {}).get("person_ok", ""),
                         image_a=(x or {}).get("image_result", ""), image_b=(y or {}).get("image_result", "")))
    return rows


def label_status(merged=None, audited=False, reviewed=False):
    """Trạng thái cao nhất đã có. Người duyệt hơn kiểm định, kiểm định hơn máy."""
    if reviewed:
        return HUMAN_REVIEWED
    if audited:
        return HUMAN_AUDITED
    return merged or MACHINE_LABELED


def eval_usable(status, tier_passed):
    """Được dùng cho val, test không. Hàng đợi bất đồng không bao giờ được; nhãn máy đồng thuận chỉ khi tầng đạt kiểm định."""
    if status in (HUMAN_REVIEWED, HUMAN_AUDITED):
        return True
    return status == MACHINE_CONSENSUS and tier_passed


def stratified_sample(rows, n, floor, seed, key):
    """Chọn khoảng n dòng: mỗi tầng tối thiểu `floor` nếu có, phần còn lại theo tỉ lệ. Cố định theo seed."""
    rng = random.Random(seed)
    strata = defaultdict(list)
    for r in sorted(rows, key=lambda x: x["id"]):
        strata[key(r)].append(r)
    for v in strata.values():
        rng.shuffle(v)
    take = {k: min(floor, len(v)) for k, v in strata.items()}
    left = max(n - sum(take.values()), 0)
    total = sum(len(v) - take[k] for k, v in strata.items())
    for k, v in sorted(strata.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        take[k] += min(round(left * (len(v) - take[k]) / max(total, 1)), len(v) - take[k])
    return [r for k in sorted(strata) for r in strata[k][:take[k]]]


def audit_tiers(rows, max_rate):
    """rows: dict(tier, machine, human). Mỗi tầng: số khác, tỉ lệ, khoảng tin cậy, kiểu sai lặp lại, đạt hay không.

    Đạt khi tỉ lệ dưới max_rate và không có kiểu sai chiếm đa số trong các ca khác (ít nhất 3 ca cùng kiểu).
    """
    groups = defaultdict(list)
    for r in rows:
        groups[r["tier"]].append(r)
    out = {}
    for t, v in sorted(groups.items()):
        wrong = [(r["machine"], r["human"]) for r in v if r["machine"] != r["human"]]
        p, lo, hi = wilson(len(wrong), len(v))
        top = Counter(wrong).most_common(1)
        pattern = top[0] if top and top[0][1] >= 3 and top[0][1] * 2 > len(wrong) else None
        out[t] = dict(n=len(v), different=len(wrong), rate=round(p, 4), ci=[round(lo, 4), round(hi, 4)], pattern=None if pattern is None else f"{pattern[0][0]} -> {pattern[0][1]} ({pattern[1]})",
                      passed=p < max_rate and pattern is None)
    return out


def read_csv(path):
    return list(csv.DictReader(path.open(encoding="utf-8"))) if path.exists() else []
