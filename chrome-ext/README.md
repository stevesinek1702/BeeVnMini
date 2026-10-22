# BeeMini Claude — Bee.vn mini chạy trong Chrome (thử nghiệm)

Bản chuyển app Bee.vn mini (Python/Tkinter) sang Chrome extension. Bảng giá nhỏ **luôn nổi trên mọi cửa sổ**
(Excel, Zalo…) bằng cửa sổ *Document Picture-in-Picture* của Chrome; lọc nhiều tiêu chí kiểu FireAnt Screener,
pullback / trendline, danh mục ★ Theo dõi, đọc tên mã mới bằng giọng Việt. Logic lọc chép nguyên từ bản Python
và đã đối chiếu từng số (xem cuối trang).

## Nạp vào Chrome

1. Mở `chrome://extensions`, bật **Developer mode** (góc trên phải).
2. Bấm **Load unpacked**, chọn thư mục `D:\Extension BeeMini Claude` (bản chép từ `chrome-ext/` trong kho mã).
   Đã nạp rồi thì chép đè xong bấm nút **↻ Reload** của extension.
3. Bấm biểu tượng *BeeMini Claude* trên thanh công cụ (ghim nó từ nút hình mảnh ghép) → mở tab bảng giá (tab tự ghim).
4. Trong tab, bấm **Mở cửa sổ nổi** → bảng giá nổi ở góc dưới-phải màn hình.

Giữ tab đó mở (thu nhỏ Chrome cũng được): **cửa sổ nổi sống theo tab**, đóng tab là cửa sổ nổi đóng theo.
Mỗi lần mở lại Chrome phải bấm **Mở cửa sổ nổi** một lần (Chrome bắt phải có cú bấm).

## Dùng

| Muốn | Làm |
|---|---|
| Đặt / đổi bộ lọc | Phần **⚙ Cài đặt bộ lọc** bên phải tab (trên cửa sổ nổi bấm ⚙ để nhảy về tab). Sửa xong bấm **Lưu** |
| Thêm tiêu chí thứ 2, 3… | **＋ Thêm tiêu chí** → đặt tên, sàn, kiểu báo, điều kiện → **Lưu**. Mỗi tiêu chí một khối trên bảng; đổi qua lại bằng ô *Tiêu chí*, bỏ bằng **Xoá** |
| Lọc theo cột có sẵn (Giá, % Thay đổi, KLGD, % KL/TB, GTGD, MA10/20/45, Lực cầu) | Các ô bên trái: chọn > < = và gõ số. Để trống = không lọc |
| Thêm điều kiện kiểu FireAnt (RSI, MFI, MACD, Bollinger, cắt SMA/EMA, vượt đỉnh, KL dự kiến, nước ngoài…) | Cột **Thêm điều kiện**: chọn nhóm → điều kiện → đặt giá trị → **＋ Thêm** (✕ để bỏ). 24 cột số + 42 tín hiệu y như bản Python |
| Pullback & trendline | Nhóm **Pullback & trendline**: pullback / bật lên từ SMA 10-20-50 và trendline tăng 3T/6T; vượt trendline giảm; pullback / bật lên sau vượt; cột **Vượt TL 3T/6T** (vd *Đến ≤ 5* = vượt trong tuần), **Giá vượt**, **% từ vượt**, **↕SMA20/50**. Luật kẻ trendline y bản Python |
| Khi có mã mới | Ô *Khi có mã mới* của từng tiêu chí: **Đọc tên mã** (giọng Windows "Microsoft An") / **Kêu "ting"** / **Im lặng**; nút **Nghe thử**. Mã mới sáng vàng 6 giây |
| ★ Theo dõi | Ô **★ Theo dõi** (gõ `VIB MBB HPG`) → khối riêng cuối bảng. Hoặc **chuột phải lên một mã** trên bảng → ★ Theo dõi / ✕ Bỏ theo dõi |
| Chép cài đặt từ app Windows | Ô *Chép cài đặt từ app Bee.vn mini* → chọn `%APPDATA%\BeeVnMini\config.json` → **Lưu** |
| Sắp xếp | Bấm tiêu đề cột (▼ lớn → nhỏ, bấm lần nữa ▲). Mỗi tiêu chí xếp riêng |
| Thu gọn / đầy đủ | Bấm vào các hàng mã (hoặc nút ⤢). Cửa sổ nổi tự co giãn theo |
| Gập / mở, nhiều / ít hàng | Bấm dòng tên khối (▾ / ▸); nút **＋ / －** bên phải dòng tên |
| Quét lại trendline / chỉ báo ngay | Chuột phải lên bảng → **Quét lại trendline / chỉ báo ngay** |
| Đổi sàn nhanh (khi chỉ có 1 tiêu chí) | Chuột phải lên bảng → *Sàn: …* |

Giá tự lấy **30 giây/lần** trong giờ giao dịch (8:45–15:15, thứ 2–6), ngoài giờ 10 phút/lần. MA / KL trung bình tự
tính từ nến ngày VNDirect mỗi ngày một lần (~30 giây). Chỉ báo kỹ thuật + trendline chỉ tải khi có tiêu chí cần
(~1 phút cho cả thị trường, tính ở luồng phụ nên bảng không đơ), lưu lại dùng cả ngày.

## Khác bản Python

- **Chưa có:** cột MA lấy từ FireAnt TradingStatistic bằng cookie Google Sheet — bản này luôn tự tính MA từ VNDirect
  (bản Python cũng tự chuyển sang cách này khi cookie hết hạn). Độ trong suốt cửa sổ.
- **Bỏ hẳn:** cài đặt / biểu tượng Desktop / tự chạy khi bật máy, tự cập nhật qua GitHub, khoá chạy một bản.
- **Do Chrome:** cửa sổ nổi có thanh tiêu đề của Chrome; diện tích tối đa ~¼ màn hình (bảng rộng quá thì cuộn ngang);
  không tự dời được nên khi co lại nó co về phía trên-trái (kéo thanh tiêu đề để dời).

## Cho người sửa code

| File | Việc |
|---|---|
| `lib/core.js`, `lib/conditions.js`, `lib/tech.js` | Chép từ `core.py`, `conditions.py`, `tech.py` — lọc, điều kiện, chỉ báo, trendline. Không dính giao diện |
| `lib/pyfloat.js` | Phép cộng / làm tròn y hệt Python 3.12 (`sum` bù sai số Neumaier, `round` về số chẵn) để số khớp từng chữ số |
| `lib/symbols.js` | ~1.600 mã (sinh từ `symbols.py`) |
| `app.js` | Trang chính: vòng lấy dữ liệu, lọc, báo mã mới, cửa sổ nổi |
| `view.js` | Vẽ bảng (dựng khung một lần, các lượt sau chỉ đổi chữ trong ô → không nháy) |
| `settings.js` | Cài đặt bộ lọc |
| `data.js`, `techworker.js` | Gọi FireAnt / VNDirect; luồng phụ tính chỉ báo |
| `sw.js` | Hẹn giờ 30 giây (`chrome.alarms`), nút trên thanh công cụ |
| `icons/` | Logo con ong / tổ ong (`logo.svg`, bản rút gọn `logo-small.svg`, icon PNG 16–128; vẽ lại bằng `ve-logo.py`) |
| `tests/` | `node --test` (69 test, chép từ `tests/` của bản Python) |

Đã đối chiếu với bản Python 1.7.0 trên nến thật cả thị trường (21–22/10/2026): 1.191.909 con số thống kê
(gồm trendline, phiên vượt), 25,4 triệu lần đánh giá 42 tín hiệu, 69.312 bộ cột số — **0 sai lệch**;
chạy cả extension trong Chrome rồi đưa đúng dữ liệu đó vào `core.py`: các khối lọc ra cùng danh sách mã, cùng thứ tự.
