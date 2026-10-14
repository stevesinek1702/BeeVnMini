# Bee.vn mini — bảng giá nhỏ luôn nổi trên màn hình

Chương trình nhỏ cho Windows (không phải extension). Cửa sổ bảng giá **luôn nằm trên mọi cửa sổ**:
chuyển sang Chrome, Excel, Zalo… nó vẫn hiện ở góc dưới-phải.

- **1 mã = 1 hàng.** Nhiều mã thì cửa sổ dài thêm lên trên, giống chồng thông báo.
- **Thu gọn:** chỉ *Mã CP* + các cột đang lọc (cột có chấm đỏ). **Bấm vào bảng** → đủ 11 cột như bảng giá Bee.vn.
- Tự lấy giá **30 giây/lần** trong giờ giao dịch (8:45–15:15, thứ 2–6), ngoài giờ 10 phút/lần.
- Có **mã mới** lọt vào bộ lọc → hàng đó sáng vàng vài giây + **đọc to tên mã** bằng giọng tiếng Việt
  của Windows ("Mã mới: V I B, M B B"). Đổi sang kêu "ting" hoặc im lặng trong ⚙ (có nút *Nghe thử*).
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
| Sắp xếp | **Bấm tiêu đề cột** (▼ lớn → nhỏ; bấm lần nữa ▲ nhỏ → lớn). Mã CP / Sàn xếp A → Z |
| Xem đủ cột / thu gọn | Bấm vào các hàng mã (hoặc nút ⤢) |
| Dời chỗ (kể cả sang màn hình khác) | Giữ chuột vào thanh trên cùng (chỗ chữ Bee.vn) rồi kéo — lần sau mở lại đúng chỗ đó |
| Nhiều mã quá dài | Lăn chuột trên bảng |
| Tải lại ngay | Nút **↻** |
| Menu (về góc màn hình, tắt…) | Bấm chuột phải lên bảng |
| Tắt | Nút **✕** |

Đơn vị trong bộ lọc giống bảng giá web: Giá bằng nghìn đồng (14.2 = 14.200đ), KLGD bằng cổ phiếu
(1000000 = 1 triệu CP), GTGD bằng tỷ đồng.

## Dữ liệu lấy từ đâu

| Cột | Nguồn |
|---|---|
| Giá, Thay đổi, % Thay đổi, KLGD, GTGD, Lực cầu | FireAnt (công khai) — cùng nguồn bảng giá Bee.vn |
| MA10, MA20, MA45, % KL/TB | FireAnt TradingStatistic bằng cookie ở ô **D2** sheet *Dashboard* (sheet của anh Si, dùng chung; đổi / xoá trong ⚙) — số khớp y hệt web. Cookie hết hạn → tự tính từ lịch sử ngày VNDirect (mất ~1 phút sau khi mở). |

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
| `symbols.py` | ~1.600 mã HOSE/HNX/UPCoM — mã mới niêm yết thì thêm vào đây |
| `tests/` | `python -m unittest discover -s tests -t .` |

Chỉ dùng thư viện có sẵn của Python 3 (đã thử với 3.12). Cài đặt + bộ nhớ đệm nằm ở
`%APPDATA%\BeeVnMini` (`config.json`, `hist.json`, `log.txt`).
