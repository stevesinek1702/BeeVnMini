"""Test điều kiện lọc kiểu FireAnt Screener (tech.py + conditions.py + phần nối ở core.py).

Công thức đã được đối chiếu với code gốc của FireAnt bằng cách chạy cả hai trên cùng số liệu thật
(~23.000 ca × 185 bộ tham số, 0 sai lệch); các test dưới đây giữ lại những ca đáng nhớ, tính tay được.
"""
import unittest
from datetime import date, datetime, timedelta, timezone

import conditions
import core
import tech

VN = timezone(timedelta(hours=7))


def make_bars(n, close=lambda i: i + 1, vol=1000, start=date(2026, 8, 1)):
    """n nến ngày liên tiếp; 't' để luôn là chuỗi ngày (date_of = hàm giữ nguyên)."""
    days = [(start + timedelta(days=i)).isoformat() for i in range(n)]
    c = [close(i) for i in range(n)]
    return {'s': 'ok', 't': days, 'o': c, 'h': [x + .5 for x in c], 'l': [x - .5 for x in c], 'c': c, 'v': [vol] * n}, days


def keep(t):
    return t


def stats_of(n=60, **kw):
    bars, days = make_bars(n, **kw)
    today = (date.fromisoformat(days[-1]) + timedelta(days=1)).isoformat()
    return tech.stats_from_bars(bars, today, keep), today


class ThongKeKyThuat(unittest.TestCase):
    def test_lui_ngay_lui_thang(self):
        self.assertEqual(tech.minus_period('2026-10-15', 'd', 7), '2026-10-08')
        self.assertEqual(tech.minus_period('2026-03-31', 'm', 1), '2026-02-28')    # tháng ngắn hơn → ngày cuối tháng
        self.assertEqual(tech.minus_period('2026-01-15', 'm', 3), '2025-10-15')
        self.assertEqual(tech.minus_period('2026-10-15', 'm', 12), '2025-10-15')

    def test_chuoi_phien_tang_giam(self):
        self.assertEqual(tech.streak([1, 2, 3, 4]), 3)
        self.assertEqual(tech.streak([4, 3, 2, 3]), 1)          # phiên tăng cuối cắt chuỗi giảm
        self.assertEqual(tech.streak([5, 4, 3]), -2)
        self.assertEqual(tech.streak([1, 2, 3, 3]), 0)          # đứng giá = không chuỗi

    def test_ema_va_rsi_wilder(self):
        self.assertEqual(tech.ema_last([1, 2, 3], 3), 2.25)     # hệ số 0.5
        self.assertEqual(tech.ema_last([7] * 30, 12), 7)
        ag, al = tech.wilder_rsi_parts(list(range(1, 17)))      # tăng đều → không có phiên giảm
        self.assertEqual((ag, al), (1, 0))
        self.assertEqual(tech.wilder_rsi_parts([1, 2, 3]), (None, None))

    def test_dong_tien_mfi(self):
        up, _ = make_bars(20, close=lambda i: 10 + i)
        down, _ = make_bars(20, close=lambda i: 50 - i)
        rows = lambda b: tech.closed_bars(b, '2099-01-01', keep)
        p, n, mfi, _ = tech.money_flow(rows(up))
        self.assertEqual((n, mfi), (0, 100.0))
        self.assertGreater(p, 0)
        p, n, mfi, _ = tech.money_flow(rows(down))
        self.assertEqual((p, mfi), (0, 0.0))

    def test_bo_nen_hom_nay_va_nen_hong(self):
        bars, days = make_bars(40)
        today = days[-1]                                    # nến cuối chính là hôm nay → phải bị bỏ
        st = tech.stats_from_bars(bars, today, keep)
        self.assertEqual((st['n'], st['lc'], st['ld']), (39, 39, days[-2]))
        bars['c'][5] = None
        self.assertEqual(tech.stats_from_bars(bars, today, keep)['n'], 38)
        self.assertIsNone(tech.stats_from_bars(make_bars(10)[0], '2099-01-01', keep))     # quá ít nến
        self.assertIsNone(tech.stats_from_bars({'s': 'no_data'}, '2099-01-01', keep))
        self.assertIsNone(tech.stats_from_bars(None, '2099-01-01', keep))

    def test_so_thong_ke_tinh_tay(self):
        st, _ = stats_of(60)                                # đóng cửa 1..60, KL 1000 mỗi phiên
        self.assertEqual((st['lc'], st['lh'], st['ll']), (60, 60.5, 59.5))
        self.assertEqual((st['p5'], st['p20'], st['p4']), (58, 50.5, 58.5))
        self.assertEqual((st['v20'], st['v44']), (1000, 1000))
        self.assertEqual(st['streak'], 59)
        self.assertEqual(st['mfi'], 100.0)
        self.assertAlmostEqual(st['sd20'], 5.766281, places=5)    # độ lệch chuẩn tổng thể của 41..60
        # Mốc "1 tuần": hôm nay là 61 (7 ngày lùi = ngày của đóng cửa 54) → đỉnh trong 7 phiên 54..60, giá mốc = 54
        self.assertEqual((st['hi1w'], st['lo1w'], st['px1w']), (60.5, 53.5, 54))

    def test_ngay_cua_nen_dchart_la_gio_vn(self):
        # dchart đặt mốc thời gian 00:00 UTC = 07:00 VN cùng ngày; today chỉ là chuỗi ngày
        import calendar
        t = calendar.timegm((2026, 10, 14, 0, 0, 0))
        bars = {'s': 'ok', 't': [t], 'o': [1], 'h': [1], 'l': [1], 'c': [1], 'v': [1]}
        self.assertEqual(len(tech.closed_bars(bars, '2026-10-15', core.vn_date)), 1)
        self.assertEqual(len(tech.closed_bars(bars, '2026-10-14', core.vn_date)), 0)

    def test_phut_giao_dich_va_kl_du_kien(self):
        at = lambda h, m, s=0: datetime(2026, 10, 14, h, m, s, tzinfo=VN)
        self.assertEqual(tech.elapsed_minutes(at(8, 59), 'HSX'), 0)
        self.assertEqual(tech.elapsed_minutes(at(10, 0), 'HSX'), 60)
        self.assertEqual(tech.elapsed_minutes(at(12, 0), 'HSX'), 150)        # nghỉ trưa
        self.assertEqual(tech.elapsed_minutes(at(14, 0), 'HSX'), 210)
        self.assertEqual(tech.elapsed_minutes(at(16, 0), 'HSX'), 255)
        self.assertEqual(tech.elapsed_minutes(at(16, 0), 'HNX'), 270)
        self.assertEqual(tech.estimated_volume(1000, 'HSX', at(10, 0)), 1000 * 255 / 60)
        self.assertIsNone(tech.estimated_volume(1000, 'HSX', at(8, 30)))
        self.assertIsNone(tech.estimated_volume(0, 'HSX', at(10, 0)))


def lv(last, **kw):
    return {'last': last, 'high': kw.get('high'), 'low': kw.get('low'), 'volume': kw.get('volume', 0), 'est': kw.get('est')}


def sig(id_, **params):
    return conditions.normalize_signal({'id': id_, 'params': params})


class TinHieu(unittest.TestCase):
    def ev(self, s, st, live):
        return conditions.eval_signal(s, st, live)

    def test_gia_cat_sma(self):
        st = {'lc': 10, 'p5': 10.2, 'p4': 10}               # hôm qua đóng 10 ≤ SMA5 10.2
        up = sig('PriceCrossAboveSMA', period=5)
        self.assertTrue(self.ev(up, st, lv(11)))             # SMA5 hôm nay (11+4×10)/5 = 10.2 < 11
        self.assertFalse(self.ev(up, st, lv(10)))
        down = sig('PriceCrossBelowSMA', period=5)
        self.assertFalse(self.ev(down, st, lv(11)))
        self.assertTrue(self.ev(down, {'lc': 10.5, 'p5': 10.2, 'p4': 10.2}, lv(9)))

    def test_gia_cat_ema_co_khoang_dem_50_dong(self):
        st = {'lc': 10, 'e5': 10}
        s = sig('PriceCrossAboveEMA', period=5)
        self.assertFalse(self.ev(s, st, lv(10.04)))          # EMA hôm nay 10.0133; phải cao hơn 0.05 nữa
        self.assertTrue(self.ev(s, st, lv(10.2)))

    def test_sma_ngan_cat_sma_dai(self):
        st = {'p5': 9, 'p4': 9, 'p15': 10, 'p14': 10}
        s = sig('ShortSMACrossAboveLongSMA', short=5, long=15)
        self.assertTrue(self.ev(s, st, lv(20)))              # SMA5 mới (20+36)/5 = 11.2 > SMA15 mới (20+140)/15 = 10.67
        self.assertFalse(self.ev(s, st, lv(9)))
        self.assertFalse(self.ev(sig('ShortSMACrossBelowLongSMA', short=5, long=15), st, lv(20)))

    def test_rsi_vao_vung_qua_mua(self):
        st = {'lc': 10, 'ag': 1, 'al': 1}                    # RSI phiên trước = 50
        s = sig('RSICrossAboveOverBoughtLine', level=70)
        self.assertTrue(self.ev(s, st, lv(40)))              # RSI nếu giá là 40: (13+30)/13 → 76.8
        self.assertFalse(self.ev(s, st, lv(12)))             # → 53.6
        self.assertTrue(self.ev(sig('RSIAboveOverBoughtLine', level=70), st, lv(40)))
        crash = {'lc': 100, 'ag': 1, 'al': 1}
        self.assertTrue(self.ev(sig('RSICrossBelowOverSoldLine', level=30), crash, lv(70)))   # sập 30% → RSI 23 → vào vùng quá bán
        self.assertTrue(self.ev(sig('RSIBelowOverSoldLine', level=30), crash, lv(70)))
        self.assertFalse(self.ev(sig('RSICrossAboveOverSoldLine', level=30), crash, lv(70)))
        self.assertEqual(conditions.rsi_now({'lc': 10, 'ag': 1, 'al': 0}, 10)[0], 100.0)

    def test_mfi_gia_bang_gia_dien_hinh_khong_co_dong_tien(self):
        # Hôm nay giá cao / thấp / đóng y hệt hôm qua → giá điển hình bằng nhau → không tính dòng tiền dương hay âm
        st = {'lh': 1.4, 'll': 1.4, 'lc': 1.4, 'pmf': 0.0, 'nmf': 0.0, 'mfi': 0.0}
        prev, live = conditions.mfi_now(st, lv(1.4, high=1.4, low=1.4, volume=1000))
        self.assertEqual((prev, live), (0.0, 100.0))          # nmf = 0 → MFI quy ước 100
        # Cùng giá điển hình (1.32+1.23+1.25 = 1.3+1.2+1.3 = 3.8) dù cao / thấp / đóng khác nhau → vẫn không có dòng tiền
        st2 = {'lh': 1.3, 'll': 1.2, 'lc': 1.3, 'pmf': 10.0, 'nmf': 5.0, 'mfi': 66.0}
        _, live = conditions.mfi_now(st2, lv(1.25, high=1.32, low=1.23, volume=100))
        self.assertAlmostEqual(live, 100 - 100 / (1 + 10 / 5))
        # Giá điển hình hôm nay thấp hơn hôm qua → cộng dòng tiền ÂM; cao hơn → cộng dòng tiền DƯƠNG
        _, live = conditions.mfi_now(st2, lv(1.2, high=1.25, low=1.15, volume=100))      # tp 1.2 < 1.2667
        self.assertAlmostEqual(live, 100 - 100 / (1 + 10 / (5 + 1.2 * 100)))
        _, live = conditions.mfi_now(st2, lv(1.4, high=1.45, low=1.35, volume=100))      # tp 1.4 > 1.2667
        self.assertAlmostEqual(live, 100 - 100 / (1 + (10 + 1.4 * 100) / 5))

    def test_mfi_thieu_cao_thap_trong_ngay_thi_lay_gia_hien_tai(self):
        st = {'lh': 11, 'll': 9, 'lc': 10, 'pmf': 5.0, 'nmf': 5.0, 'mfi': 50.0}
        a = conditions.mfi_now(st, lv(12, volume=10))
        b = conditions.mfi_now(st, lv(12, high=12, low=12, volume=10))
        self.assertEqual(a, b)

    def test_bollinger(self):
        st = {'lc': 10, 'p19': 10, 'p20': 10, 'sd19': 1, 'sd20': 1}      # biên trên phiên trước = 10 + 2×1 = 12
        s = sig('PriceCrossAboveBollingerBands', std=2)
        self.assertTrue(self.ev(s, st, lv(16)))
        self.assertFalse(self.ev(s, st, lv(11)))
        self.assertTrue(self.ev(sig('PriceAboveBollingerBands', std=2), st, lv(16)))
        self.assertTrue(self.ev(sig('PriceBelowBollingerBands', std=2), st, lv(5)))
        mid, sd = (10 * 19 + 16) / 20, (19 * 36 + 380) ** .5 / 20
        up, lo = conditions.bb_now(st, 16, 2)[1]
        self.assertAlmostEqual(up, mid + 2 * sd)
        self.assertAlmostEqual(lo, mid - 2 * sd)

    def test_macd(self):
        st = {'e12': 9.9, 'e26': 10.0, 'sig': 0.0}           # MACD hôm qua −0.1, dưới đường 0
        self.assertTrue(self.ev(sig('MACDCrossAboveZeroLine'), st, lv(12)))
        self.assertTrue(self.ev(sig('MACDAboveZeroLine'), st, lv(12)))
        self.assertFalse(self.ev(sig('MACDCrossAboveZeroLine'), st, lv(9)))
        self.assertTrue(self.ev(sig('MACDBelowZeroLine'), st, lv(9)))
        self.assertTrue(self.ev(sig('MACDCrossAboveSignalLine'), {**st, 'sig': 0.0}, lv(12)))
        self.assertIsNone(conditions.macd_now({'e12': None, 'e26': 1, 'sig': 1}, 5))

    def test_vuot_dinh_thung_day(self):
        st = {'hi1m': 20, 'lo1m': 8, 'hi1y': 30, 'lo1y': 5}
        self.assertTrue(self.ev(sig('AbovePreviousHigh', period='1m'), st, lv(21)))
        self.assertFalse(self.ev(sig('AbovePreviousHigh', period='1y'), st, lv(21)))
        self.assertTrue(self.ev(sig('BelowPreviousLow', period='1m'), st, lv(7)))
        self.assertFalse(self.ev(sig('BelowPreviousLow', period='1y'), st, lv(7)))

    def test_kl_du_kien_vuot_trung_binh(self):
        st = {'v4': 100}
        s = sig('EstimatedVolumeSurge', period=5, pct=50)    # TB5 = (100×4 + 200)/5 = 120; ngưỡng 180
        self.assertTrue(self.ev(s, st, lv(10, est=200)))
        self.assertFalse(self.ev(sig('EstimatedVolumeSurge', period=5, pct=100), st, lv(10, est=200)))
        self.assertFalse(self.ev(s, st, lv(10, est=None)))   # chưa có KL dự kiến (chưa mở cửa)

    def test_thieu_so_thi_khong_khop_va_khong_vo(self):
        s = sig('PriceCrossAboveSMA', period=5)
        self.assertFalse(self.ev(s, None, lv(11)))
        self.assertFalse(self.ev(s, {}, lv(11)))
        self.assertFalse(self.ev(s, {'lc': 10, 'p5': 10, 'p4': 10}, lv(0)))      # chưa có giá
        self.assertFalse(self.ev({'id': 'KhongCo'}, {'lc': 1}, lv(1)))

    def test_chuan_hoa_tin_hieu_tu_cai_dat(self):
        self.assertIsNone(conditions.normalize_signal({'id': 'KhongCo'}))
        self.assertIsNone(conditions.normalize_signal('rác'))
        self.assertEqual(conditions.normalize_signal({'id': 'PriceCrossAboveSMA'})['params'], {'period': 5})    # thiếu → mặc định
        self.assertEqual(sig('PriceCrossAboveSMA', period=7)['params'], {'period': 5})     # không có SMA(7) → mặc định
        self.assertEqual(sig('PriceCrossAboveSMA', period=10.0)['params'], {'period': 10})
        self.assertEqual(sig('RSIAboveOverBoughtLine', level=72.5)['params'], {'level': 72.5})   # ngưỡng nhập tự do
        self.assertEqual(sig('RSIAboveOverBoughtLine', level=500)['params'], {'level': 70})      # ngoài 0..100
        self.assertEqual(sig('PriceAboveBollingerBands', std='abc')['params'], {'std': 2})
        self.assertEqual(sig('ShortSMACrossAboveLongSMA', short=15, long=15)['params'], {'short': 5, 'long': 15})

    def test_mo_ta_tin_hieu(self):
        self.assertEqual(conditions.describe_signal(sig('PriceCrossAboveSMA', period=5)), 'Giá cắt lên SMA(5)')
        self.assertEqual(conditions.describe_signal(sig('AbovePreviousHigh', period='1m')), 'Giá vượt đỉnh 1 tháng')
        self.assertEqual(conditions.describe_signal(sig('RSICrossAboveOverBoughtLine', level=70)),
                         'RSI(14) đi vào vùng quá mua (trên 70)')
        self.assertEqual(conditions.describe_signal(sig('EstimatedVolumeSurge', period=5, pct=50)),
                         'KL dự kiến vượt TB 5 phiên tối thiểu 50%')
        self.assertEqual(conditions.describe_signal(sig('MACDCrossAboveZeroLine')), 'MACD cắt lên đường 0')

    def test_danh_muc_cho_bo_chon_dieu_kien(self):
        cat = conditions.catalog()
        self.assertEqual(list(cat), [g for g, _ in conditions.GROUPS])
        self.assertTrue(all(cat.values()))                                  # nhóm nào cũng có điều kiện
        self.assertEqual(sum(len(v) for v in cat.values()), 16 + 35)        # 16 cột số + 35 tín hiệu
        self.assertEqual(cat['price'][0], ('Thay đổi giá 1 tuần (%)', 'metric', 'change1w'))     # cột số trước tín hiệu
        self.assertIn(('Giá cắt lên SMA(…)', 'signal', 'PriceCrossAboveSMA'), cat['ma'])
        self.assertIn(('MACD cắt lên đường 0', 'signal', 'MACDCrossAboveZeroLine'), cat['macd'])
        self.assertEqual(conditions.param_text('1m'), '1 tháng')
        self.assertEqual(conditions.param_text(70.0), '70')
        self.assertEqual(conditions.param_text(3.5), '3.5')

    def test_danh_muc_du_35_tin_hieu(self):
        self.assertEqual(len(conditions.SIGNAL_LIST), 35)
        groups = {g for g, _ in conditions.GROUPS}
        for s in conditions.SIGNAL_LIST:
            self.assertIn(s.group, groups)
            for p in s.params:                           # mặc định phải nằm trong danh sách chọn
                self.assertIn(p.default, p.choices)


class CotSoKieuFireAnt(unittest.TestCase):
    def test_thay_doi_gia_nhieu_ky_va_chuoi_phien(self):
        st = {'px1w': 10, 'px1m': 8, 'streak': 2, 'v5': 500, 'v3m': 900}
        m = conditions.tech_metrics(st, 11, 0.5)
        self.assertAlmostEqual(m['change1w'], 10)
        self.assertAlmostEqual(m['change1m'], 37.5)
        self.assertIsNone(m['change1y'])                      # chưa đủ lịch sử
        self.assertEqual((m['upDays'], m['avgVol5'], m['avgVol3m']), (3, 500, 900))   # chuỗi 2 phiên + hôm nay
        self.assertIsNone(m['downDays'])
        # hôm nay giảm sau chuỗi tăng → "tăng liên tục trước khi đảo chiều"
        m = conditions.tech_metrics(st, 11, -0.5)
        self.assertEqual((m['upDaysBeforeDown'], m['upDays']), (2, None))
        m = conditions.tech_metrics({'streak': -3}, 11, -0.5)
        self.assertEqual(m['downDays'], 4)
        m = conditions.tech_metrics({'streak': -3}, 11, 0.5)
        self.assertEqual((m['downDaysBeforeUp'], m['downDays']), (3, None))
        self.assertEqual(conditions.tech_metrics({'streak': 2}, 11, 0)['upDays'], None)    # đứng giá hôm nay → không phiên nào
        self.assertTrue(all(v is None for v in conditions.tech_metrics(None, 11, 0.5).values()))

    def test_so_lay_thang_tu_quote(self):
        m = conditions.quote_metrics({'TotalVolume': 1000, 'TotalActiveBuyVolume': 600, 'BuyForeignQuantity': 300,
                                      'SellForeignQuantity': 100, 'BuyForeignValue': 6e9, 'SellForeignValue': 2.5e9})
        self.assertEqual((m['activeBuyPct'], m['foreignNetVol'], m['foreignNetValue']), (60, 200, 3.5))
        m = conditions.quote_metrics({'TotalVolume': 0})
        self.assertEqual((m['activeBuyPct'], m['foreignNetVol'], m['foreignNetValue']), (None, None, None))

    def test_dinh_dang_o(self):
        f = core.format_metric
        self.assertEqual(f(12.345, 'pct'), ('+12.35%', 'up'))
        self.assertEqual(f(-3.0, 'pct'), ('-3.00%', 'down'))
        self.assertEqual(f(None, 'pct'), ('--', 'muted'))
        self.assertEqual(f(3, 'int'), ('3', ''))
        self.assertEqual(f(1500000, 'vol'), ('1.5M', ''))
        self.assertEqual(f(-250000, 'svol'), ('-250.0K', 'down'))
        self.assertEqual(f(3.5, 'sbil'), ('+3.5 tỷ', 'up'))
        self.assertEqual(f(57.4, 'pct0'), ('57%', 'up'))
        self.assertEqual(core.format_cell({'change1w': 5.5}, 'change1w'), ('+5.50%', 'up'))


ROW_A = {'symbol': 'AAA', 'exchange': 'HSX', 'price': 11, 'change': 0.5, 'volume': 1000, 'value': 1.0,
         'change1w': 10.0, 'upDays': 3, 'foreignNetValue': None,
         '_tech': {'lc': 10, 'p5': 10.2, 'p4': 10}, '_live': lv(11)}
ROW_B = {'symbol': 'BBB', 'exchange': 'HSX', 'price': 9, 'change': -0.5, 'volume': 500, 'value': 0.5,
         'change1w': -4.0, 'upDays': None, 'foreignNetValue': 2.0,
         '_tech': {'lc': 10, 'p5': 10.2, 'p4': 10}, '_live': lv(9)}


class NoiVaoBoLoc(unittest.TestCase):
    def syms(self, rows):
        return [r['symbol'] for r in rows]

    def test_toan_tu_moi_ge_le_khoang(self):
        f = lambda op, v, v2=None: {'change1w': {'operator': op, 'value': v, 'value2': v2}}
        self.assertEqual(self.syms(core.apply_filters([ROW_A, ROW_B], f('ge', 10))), ['AAA'])        # ≥ lấy cả mốc
        self.assertEqual(self.syms(core.apply_filters([ROW_A, ROW_B], f('gt', 10))), [])
        self.assertEqual(self.syms(core.apply_filters([ROW_A, ROW_B], f('le', -4))), ['BBB'])
        self.assertEqual(self.syms(core.apply_filters([ROW_A, ROW_B], f('bt', -5, 11))), ['AAA', 'BBB'])
        self.assertEqual(self.syms(core.apply_filters([ROW_A, ROW_B], f('bt', 11, -5))), ['AAA', 'BBB'])   # nhập ngược vẫn đúng
        self.assertEqual(self.syms(core.apply_filters([ROW_A, ROW_B], f('bt', 0, 5))), [])
        # "trong khoảng" mà thiếu giá trị thứ hai thì chưa tính là đang lọc
        self.assertEqual(core.active_filter_keys(f('bt', 0, None)), [])
        self.assertEqual(core.active_filter_keys(f('ge', 0, None)), ['change1w'])

    def test_cot_moi_thieu_so_thi_loai_cot_cu_thieu_so_coi_nhu_0(self):
        f = {'foreignNetValue': {'operator': 'lt', 'value': 100}}      # cột mới: AAA chưa có số → không khớp
        self.assertEqual(self.syms(core.apply_filters([ROW_A, ROW_B], f)), ['BBB'])
        f = {'volRatio': {'operator': 'lt', 'value': 100}}            # cột cũ: thiếu coi như 0 (y bảng giá web)
        self.assertEqual(self.syms(core.apply_filters([ROW_A, ROW_B], f)), ['AAA', 'BBB'])
        self.assertEqual(core.active_filter_keys({'khongCoCot': {'operator': 'gt', 'value': 1}}), [])

    def test_loc_ca_cot_va_tin_hieu_phai_thoa_het(self):
        cfg = {'exchange': 'HSX', 'filters': {'change1w': {'operator': 'ge', 'value': -10}},
               'signals': [sig('PriceCrossAboveSMA', period=5)], 'sortColumn': 'value', 'sortDirection': 'desc'}
        self.assertEqual(self.syms(core.select_matches({'HSX': [ROW_A, ROW_B], 'HNX': [], 'UPCOM': []}, cfg)), ['AAA'])
        cfg['signals'] = [sig('PriceCrossAboveSMA', period=5), sig('PriceCrossBelowSMA', period=5)]
        self.assertEqual(core.select_matches({'HSX': [ROW_A, ROW_B], 'HNX': [], 'UPCOM': []}, cfg), [])
        cfg.pop('signals')                                           # không tín hiệu → như cũ
        self.assertEqual(len(core.select_matches({'HSX': [ROW_A, ROW_B], 'HNX': [], 'UPCOM': []}, cfg)), 2)

    def test_tieu_chi_mang_theo_tin_hieu(self):
        c = core.criteria_from_config({'criteria': [
            {'name': 'Cắt SMA', 'exchange': 'HSX', 'signals': [{'id': 'PriceCrossAboveSMA', 'params': {'period': 10}},
                                                               {'id': 'KhongCo'}, 'rác']},
            {'name': 'Thường', 'filters': {'price': {'operator': 'lt', 'value': 20}}}]})
        self.assertEqual(c[0]['signals'], [{'id': 'PriceCrossAboveSMA', 'params': {'period': 10}}])
        self.assertNotIn('signals', c[1])                            # tiêu chí cũ giữ nguyên dạng
        self.assertTrue(core.has_conditions(c[0]))                   # chỉ có tín hiệu vẫn là có điều kiện
        self.assertTrue(core.has_conditions(c[1]))
        self.assertFalse(core.has_conditions({'filters': {}}))
        # Đổi tham số tín hiệu = đổi bộ lọc (không báo "mã mới" giả); thêm tín hiệu cũng vậy
        other = dict(c[0], signals=[{'id': 'PriceCrossAboveSMA', 'params': {'period': 20}}])
        self.assertNotEqual(core.criterion_key(c[0]), core.criterion_key(other))
        self.assertEqual(core.criterion_key(c[1]), core.criterion_key({'exchange': 'HSX',
                                                                       'filters': {'price': {'operator': 'lt', 'value': 20}}}))

    def test_can_tai_lich_su_nam_chi_khi_dung_dieu_kien_ky_thuat(self):
        self.assertFalse(core.needs_tech({'filters': {'price': {'operator': 'lt', 'value': 20},
                                                      'foreignNetValue': {'operator': 'gt', 'value': 1}}}))
        self.assertTrue(core.needs_tech({'filters': {'change1m': {'operator': 'gt', 'value': 5}}}))
        self.assertTrue(core.needs_tech({'filters': {}, 'signals': [sig('MACDAboveZeroLine')]}))

    def test_cot_hien_ra_va_mo_ta(self):
        filters = {'price': {'operator': 'lt', 'value': 20}, 'change1m': {'operator': 'bt', 'value': 5, 'value2': 15},
                   'upDays': {'operator': 'ge', 'value': 3}}
        self.assertEqual([c[0] for c in core.compact_columns(filters)], ['symbol', 'price', 'change1m', 'upDays'])
        cfg = {'exchange': 'HSX', 'filters': filters}
        self.assertEqual(len(core.table_columns(cfg, True)), 13)                  # 11 cột + 2 cột đang lọc
        self.assertEqual(core.describe_filters(filters, [sig('PriceCrossAboveSMA', period=5)]),
                         'Giá < 20 · Thay đổi giá 1 tháng (%) từ 5 đến 15 · Số phiên tăng giá liên tục ≥ 3 · Giá cắt lên SMA(5)')
        self.assertEqual(core.HEAD_LABEL['change1m'], '% 1 tháng')
        # Tiêu chí có tín hiệu: thu gọn vẫn hiện Giá và % (tín hiệu không có cột riêng); không tín hiệu thì như cũ
        with_sig = {'exchange': 'HSX', 'filters': {'avgVol20': {'operator': 'ge', 'value': 1}},
                    'signals': [sig('MACDAboveZeroLine')]}
        self.assertEqual([c[0] for c in core.table_columns(with_sig, False)], ['symbol', 'price', 'changePercent', 'avgVol20'])
        self.assertEqual([c[0] for c in core.table_columns({'exchange': 'HSX', 'filters': {}, 'signals': [sig('MACDAboveZeroLine')]},
                                                           False)], ['symbol', 'price', 'changePercent'])
        self.assertEqual([c[0] for c in core.table_columns({'exchange': 'HSX', 'filters': {'avgVol20': {'operator': 'ge',
                                                                                                         'value': 1}}}, False)],
                         ['symbol', 'avgVol20'])
        self.assertEqual(len(core.table_columns(with_sig, True)), 12)               # đầy đủ: 11 cột + KLTB 20

    def test_quote_di_qua_transform_mang_du_so(self):
        bars, days = make_bars(60)
        today = (date.fromisoformat(days[-1]) + timedelta(days=1)).isoformat()
        st = tech.stats_from_bars(bars, today, keep)       # đóng cửa 60 hôm qua
        q = {'Symbol': 'AAA', 'Exchange': 'HOSTC', 'PriceCurrent': 66000, 'PriceChange': 6000, 'PriceHigh': 67000,
             'PriceLow': 61000, 'TotalVolume': 5000, 'TotalValue': 3e8, 'TotalActiveBuyVolume': 3000,
             'Date': '2026-10-14T08:00:00Z'}
        now = datetime(2026, 10, 14, 10, 0, tzinfo=VN)       # quote cùng ngày → ngoại suy theo giờ
        r = core.transform_quote(q, None, st, now)
        self.assertEqual((r['price'], r['change']), (66, 6))
        self.assertAlmostEqual(r['change1w'], (66 - 54) * 100 / 54)
        self.assertEqual((r['upDays'], r['activeBuyPct']), (60, 60))
        self.assertEqual(r['_live'], {'last': 66, 'high': 67, 'low': 61, 'volume': 5000, 'est': 5000 * 255 / 60})
        # Quote của phiên cũ (xem lại cuối tuần): đã đủ cả phiên, không ngoại suy
        r = core.transform_quote({**q, 'Date': '2026-10-09T08:00:00Z'}, None, st, now)
        self.assertEqual(r['_live']['est'], 5000)
        # Không có thống kê → cột kỹ thuật rỗng, tín hiệu không khớp, không lỗi
        r = core.transform_quote(q, None, None, now)
        self.assertIsNone(r['change1w'])
        self.assertEqual(core.apply_signals([r], [sig('MACDAboveZeroLine')]), [])


if __name__ == '__main__':
    unittest.main()
