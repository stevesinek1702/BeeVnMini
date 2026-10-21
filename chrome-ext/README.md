# Bee.vn mini — bản thử Chrome extension

Bản **thử nghiệm** để kiểm xem có chuyển Bee.vn mini (Python/Tkinter) sang Chrome extension được không.
Chỉ có bảng nhỏ Mã · Giá · % · KLGD · %KL/TB cho vài mã; **chưa có** bộ lọc, tiêu chí, cài đặt.
Không đụng gì tới bản Python.

## Nạp vào Chrome

1. Mở `chrome://extensions`, bật **Developer mode** (góc trên phải).
2. Bấm **Load unpacked**, chọn thư mục `chrome-ext` này.
3. Bấm biểu tượng *Bee.vn mini (thử nghiệm)* trên thanh công cụ (ghim nó từ nút hình mảnh ghép)
   → mở tab bảng giá (tab được ghim sẵn).

## Thử 4 điểm

| # | Thử gì | Cách thử |
|---|--------|----------|
| 1 | Gọi giá FireAnt + nến VNDirect | Mở tab là tự gọi; dòng 1a/1b trong *Kết quả kiểm tra* báo ✔/✘ |
| 2 | Cửa sổ nổi luôn trên cùng | Bấm **Mở cửa sổ nổi (PiP)** → cửa sổ nhỏ hiện góc dưới-phải; mở Excel lên, cửa sổ vẫn nổi. Kéo, đổi cỡ được. (**Mở side panel** rồi bấm nút PiP trong panel: cửa sổ mở xong tự đóng ngay — Chrome không giữ PiP mở từ side panel) |
| 3 | Tự cập nhật 30 s, không nhấp nháy | Để yên ≥ 1 phút; dòng 3 ghi khoảng cách giữa các lần (≈ 30 s). Chân cửa sổ PiP ghi “dựng bảng 1 lần · đã đổi N ô” — bảng chỉ dựng một lần, sau đó chỉ đổi chữ trong ô. Có thể đổi giữa `chrome.alarms` và `setInterval` |
| 4 | Đọc tên mã giọng Việt | Bấm **chrome.tts** / **Web Speech**; dòng 4 liệt kê giọng tiếng Việt Chrome thấy. Nút *Google Dịch* là đường dự phòng (không chính thức) chỉ để so sánh |

Ghi chú:
- **Cửa sổ nổi sống theo tab** đã mở nó: đóng tab (hoặc side panel) là cửa sổ nổi đóng theo. Tab được ghim
  và đặt `autoDiscardable: false` để Chrome không tự giải phóng.
- Ngoài giờ giao dịch giá không đổi nên “đã đổi N ô” có thể đứng yên — vẫn thấy giờ ở đầu bảng nhảy mỗi 30 s.
- Trạng thái thử có trong DevTools: `window.beeTest`.

Kết quả thử và ước lượng công chuyển toàn bộ app: xem [BAO-CAO.md](BAO-CAO.md).

## Tệp

- `manifest.json` — MV3, quyền `alarms`, `tts`, `sidePanel`; `host_permissions` cho fireant.vn và dchart-api.vndirect.com.vn
- `sw.js` — service worker: hẹn giờ `chrome.alarms` 30 s, nút trên thanh công cụ mở tab
- `lib.js` — lấy dữ liệu, định dạng (chép từ `core.py`), bảng nhỏ chỉ đổi ô
- `board.html` / `board.js` / `board.css` — trang thử (dùng chung cho tab và side panel)
