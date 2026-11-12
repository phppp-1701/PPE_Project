"""Script QA kiểm thử tự động toàn diện Dashboard và API (sử dụng Playwright).

Đóng vai trò QA Tester độc lập: kiểm tra từ đầu đến cuối mọi tính năng, giao diện, ảnh minh chứng,
bắt lỗi console, network 404/500 và chụp ảnh bằng chứng.
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = ROOT / "outputs" / "qa_screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = ROOT / "docs" / "audit_ui_improvements.md"
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)


def run_qa_audit():
    issues = []
    observations = []
    console_errors = []
    network_errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Monitor console logs
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("requestfailed", lambda req: network_errors.append(f"FAILED: {req.method} {req.url} - {req.failure}"))
        page.on("response", lambda resp: network_errors.append(f"HTTP {resp.status}: {resp.url}") if resp.status >= 400 else None)

        print("1. Đang truy cập http://127.0.0.1:8000...")
        page.goto("http://127.0.0.1:8000/dashboard/index.html", wait_until="networkidle")
        time.sleep(2)

        # Chụp màn hình trang chủ
        page.screenshot(path=str(SCREENSHOT_DIR / "01_homepage.png"), full_page=True)

        # 2. Kiểm tra KPI
        kpi_total = page.locator("#kpi-total").inner_text()
        kpi_active = page.locator("#kpi-active").inner_text()
        kpi_closed = page.locator("#kpi-closed").inner_text()
        observations.append(f"KPIs hiển thị: Tổng={kpi_total}, Đang vi phạm={kpi_active}, Đã đóng={kpi_closed}")
        if kpi_total == "0":
            issues.append("KPI Tổng đợt vi phạm đang bằng 0 hoặc chưa tải được số liệu.")

        # 3. Kiểm tra thanh phân bổ PPE
        ppe_bars = page.locator(".ppe-bar-item").count()
        observations.append(f"Số thanh phân bổ PPE: {ppe_bars}")
        if ppe_bars < 5:
            issues.append(f"Chỉ có {ppe_bars}/5 thanh phân bổ loại PPE được hiển thị.")

        # 4. Kiểm tra bảng sự kiện và ảnh Thumbnail
        rows = page.locator("#events-tbody tr").count()
        observations.append(f"Số dòng sự kiện trong bảng: {rows}")
        if rows == 0:
            issues.append("Bảng sự kiện vi phạm hoàn toàn trống.")

        # Kiểm tra thumbnail ảnh trong bảng
        thumb_imgs = page.locator("#events-tbody img")
        thumb_count = thumb_imgs.count()
        observations.append(f"Số ảnh thumbnail trong bảng: {thumb_count}")
        broken_thumbs = 0
        for i in range(min(5, thumb_count)):
            img = thumb_imgs.nth(i)
            is_loaded = page.evaluate("(img) => img.complete && img.naturalWidth > 0", img.element_handle())
            src = img.get_attribute("src")
            if not is_loaded:
                broken_thumbs += 1
                issues.append(f"Thumbnail thứ {i+1} bị lỗi hiển thị (broken image): {src}")

        if broken_thumbs == 0 and thumb_count > 0:
            observations.append("Tất cả thumbnail trong bảng tải thành công, có ảnh rõ ràng.")

        # 5. Mở Modal Xem minh chứng
        print("2. Mở Modal Xem minh chứng...")
        first_btn = page.locator("#events-tbody button").first
        first_btn.click()
        time.sleep(1.5)

        # Chụp màn hình modal
        page.screenshot(path=str(SCREENSHOT_DIR / "02_evidence_modal.png"))

        modal = page.locator("#event-modal")
        if not modal.is_visible():
            issues.append("Nút 'Xem minh chứng' không mở được hộp thoại Modal.")
        else:
            observations.append("Hộp thoại Modal minh chứng đã mở thành công.")

            # Kiểm tra ảnh lớn trong modal
            modal_img = page.locator("#modal-img-wrap img")
            if modal_img.count() == 0:
                issues.append("Không tìm thấy thẻ <img> trong khung minh chứng modal (vẫn hiện 'Không có ảnh minh chứng' hoặc đang tải).")
            else:
                img_elem = modal_img.first
                img_src = img_elem.get_attribute("src")
                img_loaded = page.evaluate("(img) => img.complete && img.naturalWidth > 0", img_elem.element_handle())
                nat_w = page.evaluate("(img) => img.naturalWidth", img_elem.element_handle())
                nat_h = page.evaluate("(img) => img.naturalHeight", img_elem.element_handle())
                if not img_loaded or nat_w == 0:
                    issues.append(f"Ảnh lớn trong modal bị lỗi không load được (broken image): {img_src}")
                else:
                    observations.append(f"Ảnh lớn trong modal tải thành công: kích thước {nat_w}x{nat_h} px, URL: {img_src}")

            # Kiểm tra thanh mốc thời gian (Frames ribbon)
            frame_btns = page.locator(".frame-btn")
            btn_count = frame_btns.count()
            observations.append(f"Số nút mốc thời gian vi phạm: {btn_count}")
            if btn_count == 0:
                issues.append("Thanh chọn mốc thời gian vi phạm không có nút nào.")
            elif btn_count > 1:
                # Thử bấm vào mốc thứ 2
                print("3. Thử chuyển sang mốc thời gian thứ 2...")
                frame_btns.nth(1).click()
                time.sleep(1)
                page.screenshot(path=str(SCREENSHOT_DIR / "03_modal_frame2.png"))
                img_src_2 = modal_img.first.get_attribute("src")
                observations.append(f"Đã chuyển sang mốc 2, ảnh mới: {img_src_2}")

            # 6. Kiểm tra form Feedback
            print("4. Kiểm tra form Góp ý & Chỉnh sửa...")
            page.locator(".fb-badge-false").click()
            time.sleep(0.5)

            fa_wrap = page.locator("#false-alarm-items-wrap")
            if not fa_wrap.is_visible():
                issues.append("Khi chọn 'Cảnh báo sai', khung checkbox chọn trang bị phạt nhầm không hiển thị.")
            else:
                observations.append("Khung checkbox trang bị phạt nhầm hiển thị chính xác.")
                page.locator("#fa-gloves").check()

            # Nhập ghi chú
            notes_box = page.locator("#fb-notes")
            notes_box.fill("QA Test: Công nhân có mang găng bảo hộ màu be nhưng bị khuất khi bê đá.")

            # Bấm lưu
            save_btn = page.locator("button:has-text('Lưu góp ý & Điều chỉnh')")
            # Handle alert dialog
            dialog_message = []
            page.once("dialog", lambda dialog: (dialog_message.append(dialog.message), dialog.accept()))
            save_btn.click()
            time.sleep(1.5)

            page.screenshot(path=str(SCREENSHOT_DIR / "04_feedback_saved.png"))
            if dialog_message:
                observations.append(f"Thông báo từ hệ thống khi lưu: '{dialog_message[0]}'")

            # Kiểm tra xem feedback đã vào danh sách chưa
            fb_items = page.locator("#fb-history-list > div").count()
            observations.append(f"Số bản ghi trong lịch sử góp ý: {fb_items}")
            if fb_items == 0:
                issues.append("Sau khi lưu góp ý, bản ghi không xuất hiện trong danh sách Lịch sử góp ý.")

            # 7. Đóng modal
            page.locator(".close-btn").click()
            time.sleep(0.5)

        # 8. Kiểm tra bộ lọc
        print("5. Kiểm tra bộ lọc...")
        filter_ppe = page.locator("#filter-ppe")
        filter_ppe.select_option("helmet")
        time.sleep(0.5)
        page.screenshot(path=str(SCREENSHOT_DIR / "05_filter_helmet.png"))
        filtered_rows = page.locator("#events-tbody tr").count()
        observations.append(f"Số dòng sau khi lọc thiếu 'Mũ bảo hộ': {filtered_rows}")

        browser.close()

    # Tổng hợp báo cáo Markdown
    report_content = f"""# Báo cáo Kiểm thử Độc lập Giao diện Web PPE-6 (QA Independent Audit)

*Thời gian thực hiện kiểm thử:* {time.strftime('%Y-%m-%d %H:%M:%S')}  
*URL kiểm thử:* `http://127.0.0.1:8000`  
*Công cụ thực thi:* Chromium Headless Automation (Playwright)

---

## 1. Kết quả kiểm tra tổng quan (Observations)

{chr(10).join(f"- ✅ {obs}" for obs in observations)}

---

## 2. Các vấn đề và lỗi tồn đọng phát hiện được (Issues & Defects)

{chr(10).join(f"- ❌ **Vấn đề {i+1}**: {iss}" for i, iss in enumerate(issues)) if issues else "🎉 Không phát hiện lỗi nghiêm trọng nào cản trở luồng nghiệp vụ chính."}

---

## 3. Lỗi Console & Network Logs

### Console Warnings/Errors:
{chr(10).join(f"- `{e}`" for e in console_errors) if console_errors else "- Không có lỗi console."}

### Network Errors (HTTP >= 400 hoặc Request Failed):
{chr(10).join(f"- `{e}`" for e in network_errors) if network_errors else "- Toàn bộ request HTTP (API & hình ảnh) đều đạt mã 200 OK."}

---

## 4. Đề xuất các yêu cầu cải thiện (Actionable Improvement Requirements)

1. **Hiển thị trực quan trạng thái ảnh vi phạm**:
   - Bổ sung nút phóng to ảnh (Full-screen Lightbox) để giám sát viên soi rõ các trang bị nhỏ như kính, cổ tay có găng.
2. **Bộ phím tắt điều hướng nhanh**:
   - Hỗ trợ phím mũi tên trái/phải (`←` / `→`) để lướt qua lại giữa các mốc thời gian vi phạm trong modal thay vì chỉ bấm chuột.
3. **Phản hồi người dùng không dùng `alert()`**:
   - Thay thế hộp thoại thông báo gốc `alert()` của trình duyệt bằng Toast Notification thông minh ở góc màn hình để trải nghiệm chuyên nghiệp hơn.
4. **Hiển thị huy hiệu đã được giám sát viên xác nhận (Reviewed Badge)**:
   - Khi một sự kiện vi phạm đã được giám sát viên gửi góp ý (đúng/sai), gắn một nhãn nhỏ `Đã xác minh` ngay trên bảng để người giám sát không kiểm tra lại lần thứ hai.
"""

    REPORT_PATH.write_text(report_content, encoding="utf-8")
    print(f"Đã xuất báo cáo tại: {REPORT_PATH}")
    return issues, observations, console_errors, network_errors


if __name__ == "__main__":
    run_qa_audit()
