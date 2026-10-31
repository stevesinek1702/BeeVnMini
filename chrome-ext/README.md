# Bee Mini — Bee.vn mini chạy trong Chrome (thử nghiệm)

Bản chuyển app Bee.vn mini (Python/Tkinter) sang Chrome extension. Bảng giá nhỏ **luôn nổi trên mọi cửa sổ**
(Excel, Zalo…) bằng cửa sổ *Document Picture-in-Picture* của Chrome; lọc nhiều tiêu chí,
pullback / trendline, danh mục ★ Theo dõi, đọc tên mã mới bằng giọng Việt. Logic lọc chép nguyên từ bản Python
và đã đối chiếu từng số (xem cuối trang).

## Nạp vào Chrome

1. Mở `chrome://extensions`, bật **Developer mode** (góc trên phải).
2. Bấm **Load unpacked**, chọn thư mục `D:\Extension BeeMini Claude` (bản chép từ `chrome-ext/` trong kho mã).
   Đã nạp rồi thì chép đè xong bấm nút **↻ Reload** của extension.
3. Bấm biểu tượng con ong *Bee Mini* trên thanh công cụ (ghim nó từ nút hình mảnh ghép) → mở tab bảng giá (tab tự ghim).
4. Trong tab, bấm **Mở cửa sổ nổi** → bảng giá nổi ở góc dưới-phải màn hình.

Giữ tab đó mở (thu nhỏ Chrome cũng được): **cửa sổ nổi sống theo tab**, đóng tab là cửa sổ nổi đóng theo.
Mỗi lần mở lại Chrome phải bấm **Mở cửa sổ nổi** một lần (Chrome bắt phải có cú bấm).

## Dùng

| Muốn | Làm |
|---|---|
| Đặt / đổi bộ lọc | Phần **⚙ Bộ lọc** bên phải tab (trên cửa sổ nổi bấm ⚙ để nhảy về tab). Mọi thay đổi nằm trên bản nháp (góc dưới hiện *● Có thay đổi chưa lưu*); bấm **Lưu & áp dụng** mới lên bảng, **Huỷ thay đổi** để quay lại |
| Thêm tiêu chí thứ 2, 3… | Hàng thẻ trên cùng: **＋ Tiêu chí** (hoặc **📋 Mẫu**). Mỗi thẻ = 1 khối trên bảng giá, số nhỏ trên thẻ là số điều kiện; bấm thẻ để sửa, **🗑 Xoá tiêu chí** để bỏ |
| Thêm điều kiện | Ô **🔍 Tìm điều kiện** (gõ không dấu cũng được: `rsi`, `kltb 50`, `cach dinh`, `sar`, `may`…) hoặc bấm nhóm → bấm điều kiện. Điều kiện vào danh sách phía trên; **sửa số / tham số ngay trong dòng** (vd đổi SMA(20) thành SMA(50)), ✕ để bỏ. Cột bảng giá (Giá, KLGD, GTGD, MA…) nằm trong nhóm *Cột bảng giá*. 43 cột số + 79 tín hiệu y như bản Python |
| ✨ Tạo tiêu chí bằng AI | Gõ tiêu chí như nói chuyện, vd *giá trên 10k, KLTB 50 phiên > 100 nghìn, cách đỉnh 1 năm dưới 35%, giá trên MA20* → **✨ Tạo tiêu chí** (Ctrl + Enter) → xem các điều kiện AI hiểu (ý nào không lọc được thì ghi rõ) → **＋ Thêm & áp dụng** hoặc **Thêm để sửa tiếp**. Cần khoá API: **🤖 Cài đặt AI** → chọn DeepSeek / Google Gemini / Khác (máy chủ tương thích OpenAI, vd web riêng sau này) → dán khoá. Khoá chỉ lưu trong Chrome máy đó, chỉ gửi tới máy chủ AI đã chọn; lần đầu Chrome hỏi cho phép gọi máy chủ AI |
| Tiêu chí mẫu | **📋 Mẫu**: cổ phiếu khoẻ sát đỉnh, pullback MA20, vượt đỉnh 3 tháng + KL lớn, RSI tạo đáy 15 phút, bắt đáy quá bán, xu hướng tăng mạnh (ADX + SAR + Ichimoku), nền chặt sát đỉnh, vượt trendline giảm, dòng tiền vào, khối ngoại mua ròng — bấm là thêm thành tiêu chí mới, sửa tiếp được |
| Chỉ báo | RSI, MFI, Stochastic (14,3,3), Williams %R, CCI (20), MACD, Bollinger, ADX / DMI (14), Parabolic SAR (y `ta.sar` của TradingView), Ichimoku (9,26,52), OBV, SMA / EMA 5…200, pullback / trendline. Cột số: giá trị các chỉ báo, % cách đỉnh / đáy 1 tháng … 1 năm, KLTB 50 / 100 phiên, GTTB 20 phiên |
| RSI tạo đáy (khung 15 phút hoặc ngày) | Nhóm **RSI (14)** → *RSI tạo đáy khung …* → chọn **khung** `15 phút` / `ngày`, ngưỡng quá bán (30), đáy trong (16 nến). Khớp khi đủ 3 dấu hiệu: trong 16 nến gần nhất RSI(14) từng ≤ 30 và nay đã thoát lên trên 30, RSI trên đường Signal (WMA14 của RSI), giá đóng cửa trên MA10. Khung **15 phút** xét nến **đã chốt** gần nhất, tự tải nến 15 phút cả thị trường ~20 giây sau mỗi lần chốt nến (~30 giây/lượt), nên danh sách đổi mỗi 15 phút; mã dưới 60 nến trong 3 tuần không tính. Khung **ngày** ghép giá hiện tại như các điều kiện khác |
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
tính từ nến ngày mỗi ngày một lần (~30 giây). Chỉ báo kỹ thuật + trendline chỉ tải khi có tiêu chí cần
(~1 phút cho cả thị trường, tính ở luồng phụ nên bảng không đơ), lưu lại dùng cả ngày. Nến 15 phút chỉ tải khi có
tiêu chí khung 15 phút, sau mỗi lần chốt nến (nghỉ trưa, ngoài giờ thì đứng yên).

## Khác bản Python

- **Chưa có:** cột MA lấy qua cookie Google Sheet — bản này luôn tự tính MA từ nến ngày
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
| `data.js`, `techworker.js` | Lấy giá, nến ngày và nến 15 phút; luồng phụ tính chỉ báo |
| `sw.js` | Hẹn giờ 30 giây (`chrome.alarms`), nút trên thanh công cụ |
| `icons/` | Logo con ong / tổ ong (`logo.svg`, bản rút gọn `logo-small.svg`, icon PNG 16–128; vẽ lại bằng `ve-logo.py`) |
| `lib/ai.js` | Tạo tiêu chí bằng AI: câu lệnh gửi AI (sinh từ danh mục điều kiện), gọi DeepSeek / Gemini / máy chủ tương thích OpenAI, kiểm từng điều kiện AI trả về |
| `tests/` | `node --test` (88 test: chép từ `tests/` của bản Python + test AI / tiêu chí mẫu) |

Đã đối chiếu với bản Python 1.7.0 trên nến thật cả thị trường (21–22/10/2026): 1.191.909 con số thống kê
(gồm trendline, phiên vượt), 25,4 triệu lần đánh giá 42 tín hiệu, 69.312 bộ cột số — **0 sai lệch**;
chạy cả extension trong Chrome rồi đưa đúng dữ liệu đó vào `core.py`: các khối lọc ra cùng danh sách mã, cùng thứ tự.
RSI tạo đáy (31/10/2026): 11.823 bộ thống kê nến 15 phút (~402 nghìn con số) + toàn bộ thống kê nến ngày 1.443 mã,
~1,1 triệu lần đánh giá — **0 sai lệch**; chạy extension trong Chromium, khối "RSI tạo đáy 15 phút, GTGD > 5" ra đúng
14 mã, cùng thứ tự với bản Python.
Chỉ báo bổ sung (31/10/2026): toàn bộ thống kê nến ngày 1.443 mã, 2,85 triệu lần đánh giá 79 tín hiệu (395 bộ tham số ×
5 tình huống giá), 289 nghìn giá trị cột số — **0 sai lệch** với bản Python. Bản Python đối chiếu với thư viện `ta` 0.11
(Stochastic, Williams %R, CCI, ADX, ATR, Ichimoku khớp) và bản chép `ta.sar` của TradingView (59.163 phiên khớp hẳn).
