# Bee.vn mini — bảng giá nhỏ luôn nổi trên màn hình

Chương trình nhỏ cho Windows (không phải extension). Cửa sổ bảng giá **luôn nằm trên mọi cửa sổ**:
chuyển sang Chrome, Excel, Zalo… nó vẫn hiện ở góc dưới-phải.

- **Nhiều tiêu chí**, mỗi tiêu chí nhiều điều kiện (phải thoả tất cả) và sàn riêng — mỗi tiêu chí một khối.
- **★ Theo dõi:** danh mục mã anh tự chọn (không cần qua bộ lọc), hiện thành một khối riêng ở **cuối** bảng giá
  (Mã · Giá · %; bấm vào bảng thì đủ cột + cột Sàn).
- **1 mã = 1 hàng.** Nhiều mã thì cửa sổ dài thêm lên trên, giống chồng thông báo.
- **Thu gọn:** chỉ *Mã CP* + các cột đang lọc (cột có chấm đỏ). **Bấm vào bảng** → đủ 11 cột như bảng giá Bee.vn.
- Tự lấy giá **30 giây/lần** trong giờ giao dịch (8:45–15:15, thứ 2–6), ngoài giờ 10 phút/lần.
- Có **mã mới** lọt vào bộ lọc → hàng đó sáng vàng vài giây + **đọc to tên mã** bằng giọng tiếng Việt
  của Windows ("bùng nổ KL: V I B, M B B"). **Mỗi tiêu chí chọn riêng**: đọc tên mã / kêu "ting" /
  im lặng — trong ⚙, ô *Khi có mã mới* dưới *Sàn* (có nút *Nghe thử*).
- **Không cần đăng nhập**, không cần mở Chrome.

## Cài đặt (1 lần)

1. Mở thư mục `D:\BeeVnMini`.
2. Bấm đúp vào file **`Cai dat.bat`**.
3. Hiện thông báo *"Đã cài xong"* → bấm **OK**. Bảng giá mini hiện ở góc dưới-phải màn hình.

## Mở chương trình

- **Bật máy là tự mở** — không phải làm gì.
- Lỡ tắt (bấm ✕): bấm đúp biểu tượng **Bee.vn mini** ngoài Desktop, **hoặc** bấm phím Windows ⊞,
  gõ `Bee` → Enter.
- Không thấy bảng giá đâu (bị kéo lạc, đang ở màn hình khác…): làm y như trên — nếu nó đang chạy,
  nó sẽ **hiện lên trước mặt, nháy viền vàng**, không mở thêm bản thứ hai. Vẫn không thấy thì chuột
  phải lên nó → *Về góc dưới-phải màn hình*.

## Dùng

| Muốn | Làm |
|---|---|
| Đặt / đổi bộ lọc, đổi sàn | Bấm **⚙** |
| Thêm tiêu chí thứ 2, 3… | **⚙** → **＋ Thêm tiêu chí** → đặt tên + sàn + điều kiện → **Lưu**. Bảng giá hiện mỗi tiêu chí một khối (tên · sàn · số mã); đổi qua lại bằng ô *Tiêu chí*, bỏ bằng nút **Xoá** |
| Thêm điều kiện kiểu FireAnt (RSI, MACD, giá cắt SMA/EMA, vượt đỉnh, KL dự kiến, nước ngoài mua ròng…) | **⚙** → cột **Điều kiện thêm** bên phải: chọn nhóm → chọn điều kiện → đặt giá trị → **＋ Thêm** (**✕** để bỏ). Có 43 điều kiện dạng con số (từ / đến / trong khoảng) và 79 tín hiệu có tham số; tất cả phải thoả cùng các ô lọc bên trái. Giá cắt lên / xuống SMA, EMA chọn được kỳ **5, 10, 15, 20, 45, 50, 100, 200**; SMA ngắn cắt SMA dài có cả 50 / 100 / 200 (vd SMA50 cắt lên SMA200). Điều kiện cần lịch sử giá thì lần đầu mất ~1 phút để tải (có MA dài thì tải thêm 1 lần sau khi cập nhật bản này) |
| Lọc mã đang pullback về kiểm định SMA / trendline | **⚙** → nhóm **Pullback & trendline** → *Pullback về SMA(…)* (đang chạm vùng ±x% quanh SMA 10 / 20 / 50 hôm nay) hoặc *Bật lên từ SMA(…)* (đã chạm trong 3 phiên gần nhất, hôm nay xanh và đứng trên SMA); tương tự với **trendline tăng** 3 / 6 tháng. Chỉ bắt mã đang xu hướng tăng: SMA dốc lên, nhịp vừa rồi đã chạy xa khỏi đường, từ sau đỉnh chưa phiên nào đóng cửa thủng vùng. **KL cạn dần = có**: KLTB từ sau đỉnh (gồm KL dự kiến hôm nay) phải thấp hơn KLTB 20. Trendline máy tự kẻ trên **giá đóng cửa**: nối từ đáy / đỉnh lớn sớm nhất tới điểm gần nhất, đi qua ít nhất 3 điểm, cho lệch tới 2% như mắt người kẻ; trendline tăng còn phải có đỉnh sau cao hơn đỉnh trước. *Vượt lên trendline giảm 3 / 6 tháng*: các phiên trước chưa vượt, hôm nay giá vượt đường ≥ 1% và KL dự kiến ≥ KLTB 20 (tắt được). *Sau vượt trendline giảm: pullback về / bật lên*: đã vượt đường trong 10 phiên gần nhất, quay lại kiểm định đường từ phía trên (chưa đóng cửa rơi xuống dưới quá ±x%) rồi bật lên. Cột **↕SMA20 / ↕SMA50** (% cách SMA) để xếp mã sát đường nhất |
| Xem mã nào đã vượt trendline giảm trong N phiên qua (vd 1 tuần) | **⚙** → nhóm **Pullback & trendline** → *Vượt trendline giảm 3 / 6 tháng cách đây (phiên)* → **Đến (≤)** `5` (hôm nay + 5 phiên trước ≈ 1 tuần), hoặc **Trong khoảng** `6` đến `10` (tuần trước nữa). Cột **Vượt TL 6T** hiện ngày vượt (vd `19/10`, `hôm nay`), kèm luôn **Giá vượt 6T** (giá đóng cửa phiên vượt) và **% từ vượt 6T** (giá hiện tại so với giá vượt — lọc được, vd ≤ 5 để tìm mã còn sát điểm vượt); bấm tiêu đề cột để xếp. Xa nhất 20 phiên (~1 tháng). Vượt = đóng cửa trên đường ≥ 1% lần đầu, KL ≥ KLTB 20; app kẻ lại đường đúng như ngày đó. Lần đầu dùng tải lâu hơn ~30 giây vì phải quét lùi từng phiên |
| Lọc theo chỉ báo khác | Nhóm **Stochastic (14,3,3)**, **Williams %R & CCI**, **ADX / DMI (14)**, **Parabolic SAR**, **Ichimoku (9,26,52)**: cắt nhau, thoát vùng quá mua / quá bán, xu hướng mạnh, giá trên / dưới mây… (SAR tính y `ta.sar` của TradingView). Nhóm **Đường trung bình** có thêm *Giá đang trên / dưới SMA·EMA(n)*, *SMA ngắn đang trên SMA dài*, *EMA ngắn cắt EMA dài*; **Khối lượng & dòng tiền** có OBV cắt TB 20 phiên. Cột số mới: giá trị RSI / MFI / Stoch %K / Williams %R / CCI / ADX / ATR % / độ rộng Bollinger, **% giá cách đỉnh / đáy** 1 tháng … 1 năm (vd cách đỉnh 1 năm ≤ 35), **KLTB 50 / 100 phiên**, **GTTB 20 phiên** (tỷ đồng) |
| Lọc mã RSI tạo đáy (khung 15 phút hoặc ngày) | **⚙** → nhóm **RSI (14)** → *RSI tạo đáy khung …* → chọn **khung** `15 phút` / `ngày`, ngưỡng quá bán (mặc định 30), đáy trong (mặc định 16 nến). Khớp khi đủ 3 dấu hiệu: trong 16 nến gần nhất RSI(14) từng ≤ 30 và nay đã thoát lên trên 30, RSI nằm trên đường Signal (WMA14 của RSI), giá đóng cửa trên MA10 — cùng luật Long khung 15 phút bên hệ phái sinh. Khung **15 phút** xét nến **đã chốt** gần nhất: app tự tải nến 15 phút cả thị trường ~20 giây sau mỗi lần chốt nến (~30 giây/lượt; nghỉ trưa, ngoài giờ thì đứng yên), nên danh sách đổi mỗi 15 phút, không nhảy theo từng nhịp giá; mã ít khớp lệnh (dưới 60 nến trong 3 tuần) không tính. Khung **ngày** ghép giá hiện tại làm giá đóng cửa hôm nay như các điều kiện khác |
| Quét lại trendline / chỉ báo ngay | **Chuột phải** lên bảng giá → **Quét lại trendline / chỉ báo ngay** (tải lại nến cả thị trường ~1–2 phút; trong lúc đó vẫn dùng số cũ). Bình thường app tự kẻ 1 lần mỗi ngày, còn giá hiện tại thì so với đường mỗi 30 giây |
| Theo dõi một mã | **Chuột phải lên hàng của mã** (ở khối nào cũng được) → **★ Theo dõi**. Bỏ: chuột phải lên mã đó → **✕ Bỏ theo dõi**. Muốn gõ nhiều mã một lần: **⚙** → ô **★ Theo dõi** (cách nhau bằng dấu cách, vd `VIB MBB HPG`) → **Lưu**. Khối ★ Theo dõi xếp A → Z, bấm tiêu đề cột để đổi (vd `%` để thấy mã tăng mạnh nhất), gập / ＋ － như khối tiêu chí |
| Sắp xếp | **Bấm tiêu đề cột** (▼ lớn → nhỏ; bấm lần nữa ▲ nhỏ → lớn). Mã CP xếp A → Z. Cột Sàn chỉ hiện ở chế độ đầy đủ |
| Xem đủ cột / thu gọn | Bấm vào các hàng mã (hoặc nút ⤢) |
| Dời chỗ (kể cả sang màn hình khác) | Giữ chuột vào thanh trên cùng (chỗ chữ Bee.vn) rồi kéo — lần sau mở lại đúng chỗ đó |
| Nhiều mã quá dài | Lăn chuột trên khối đó — chỉ danh sách khối đó trượt, tên tiêu chí + tiêu đề cột đứng yên |
| Gập / mở 1 tiêu chí | Bấm vào dòng tên tiêu chí (▾ mở, ▸ gập) |
| Khối hiện nhiều / ít hàng hơn | Nút **＋ / －** bên phải dòng tên tiêu chí (mặc định 8 hàng) |
| Tải lại ngay | Nút **↻** |
| Menu (về góc màn hình, tắt…) | Bấm chuột phải lên bảng |
| Tắt | Nút **✕** |

Đơn vị trong bộ lọc giống bảng giá web: Giá bằng nghìn đồng (14.2 = 14.200đ), KLGD bằng cổ phiếu
(1000000 = 1 triệu CP), GTGD bằng tỷ đồng.

## Dữ liệu lấy từ đâu

| Cột | Nguồn |
|---|---|
| Giá, Thay đổi, % Thay đổi, KLGD, GTGD, Lực cầu | FireAnt (công khai) — cùng nguồn bảng giá Bee.vn |
| MA10, MA20, MA45, % KL/TB (KL hôm nay so với **trung bình 45 phiên**) | FireAnt TradingStatistic bằng cookie ở ô **D2** sheet *Dashboard* (sheet của anh Si, dùng chung; đổi / xoá trong ⚙) — số khớp y hệt web. Cookie hết hạn → tự tính từ lịch sử ngày VNDirect (mất ~1 phút sau khi mở). |

| Điều kiện thêm cần lịch sử giá (RSI, MFI, MACD, Bollinger, SMA/EMA, đỉnh / đáy, số phiên tăng giảm, KLTB) | Tự tính từ nến ngày VNDirect (~1 năm), công thức chép từ bộ lọc FireAnt Screener. **Chỉ tải khi có tiêu chí dùng đến**, mỗi ngày một lần (~1 phút cho cả thị trường, lưu ở `tech.json`) |
| Điều kiện khung 15 phút (RSI tạo đáy) | Nến 15 phút VNDirect (3 tuần gần nhất), tải lại sau mỗi lần chốt nến khi có tiêu chí dùng đến (~30 giây cho cả thị trường, lưu ở `intra.json`) |
| % KL mua chủ động, nước ngoài mua ròng, KL dự kiến cả phiên | FireAnt (công khai), tính từ giá đang chạy |

Ở chế độ đầy đủ, dòng trên bảng ghi rõ đang dùng nguồn nào: `MA: FireAnt` hoặc
`MA: tự tính từ VNDirect (cookie FireAnt hết hạn)`. Cookie được làm mới trong sheet thì trong
vòng 10 phút chương trình tự chuyển sang FireAnt.

## Chia sẻ cho người khác

Gửi đúng **một file**: `D:\BeeVnMini\dist\BeeVnMini.exe` (~11 MB, qua Zalo / Google Drive / USB).
Máy người nhận **không cần cài Python** hay gì khác. Họ làm:

1. Bấm đúp `BeeVnMini.exe`.
2. Windows có thể hiện màn hình xanh *"Windows protected your PC"* (vì file chưa có chữ ký số của
   công ty phần mềm — không phải virus): bấm **More info** → **Run anyway**.
3. Hỏi *"Cài Bee.vn mini vào máy?"* → bấm **Yes** → **OK**. Xong: có biểu tượng ngoài Desktop,
   tự mở khi bật máy, bảng giá hiện góc dưới-phải.
4. Bấm **⚙** để đặt bộ lọc.

Bản chia sẻ dùng chung sheet cookie FireAnt của anh Si cho cột MA.
Gỡ: chuột phải lên bảng giá → **Gỡ khỏi máy…**

Link tải luôn là bản mới nhất: https://raw.githubusercontent.com/stevesinek1702/BeeVnMini/release/BeeVnMini.exe

### Tự cập nhật

Từ v1.1.0, máy đã cài **tự kiểm tra bản mới mỗi 6 tiếng**. Có bản mới → hiện nút vàng
**⬆ Cập nhật** trên bảng giá → bấm → **Yes**: tự tải, kiểm tra mã sha256, thay file, mở lại
(vài giây). Muốn kiểm tra ngay: chuột phải → *Kiểm tra cập nhật*.

Máy nào đang dùng bản trước v1.1.0 (chưa có nút này) thì phải cập nhật tay **một lần**: gửi file
mới, bấm đúp → *"Cập nhật?"* → **Yes**.

Phát hành bản mới (người sửa code): tăng `APP_VERSION` trong `beevn_mini.pyw`, rồi
`python tools/release.py "ghi chú có gì mới"` — chạy test, đóng gói, đẩy `main` và ghi đè nhánh
`release` (chỉ chứa `BeeVnMini.exe` + `latest.json`) lên GitHub `stevesinek1702/BeeVnMini`.
Bấm đúp **`Dong goi exe.bat`** nếu chỉ muốn ra file .exe để gửi tay, không phát hành.

## Gỡ

Bấm đúp **`Go cai dat.bat`** (xoá biểu tượng Desktop + bỏ tự chạy), rồi bấm ✕ trên bảng giá mini.

## Cho người sửa code

| File | Việc |
|---|---|
| `beevn_mini.pyw` | Cửa sổ (tkinter), luồng lấy giá / lịch sử, cài đặt, tạo biểu tượng |
| `speak.ps1` | Đọc to bằng giọng Windows — ưu tiên giọng tiếng Việt *Microsoft An*, máy không có thì đọc tiếng Anh |
| `core.py` | Lấy dữ liệu, lọc / sắp xếp / định dạng giống bảng giá Bee.vn — không dính giao diện |
| `conditions.py` | Danh mục điều kiện lọc kiểu FireAnt Screener (cột số + tín hiệu có tham số) và công thức đánh giá — không dính giao diện |
| `tech.py` | Chỉ báo từ nến ngày (SMA/EMA, RSI, MFI, MACD, Bollinger, đỉnh đáy, số phiên tăng giảm) + nến 15 phút (RSI tạo đáy) + KL dự kiến cả phiên |
| `symbols.py` | ~1.600 mã HOSE/HNX/UPCoM — mã mới niêm yết thì thêm vào đây |
| `tests/` | `python -m unittest discover -s tests -t .` |

Chỉ dùng thư viện có sẵn của Python 3 (đã thử với 3.12). Cài đặt + bộ nhớ đệm nằm ở
`%APPDATA%\BeeVnMini` (`config.json` — gồm cả danh mục theo dõi `watch`, `hist.json`, `tech.json`, `intra.json`, `log.txt`).
