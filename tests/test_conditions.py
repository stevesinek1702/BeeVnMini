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


class MaDai(unittest.TestCase):
    """SMA / EMA 50, 100, 200."""
    def stats(self, n, close):
        return stats_of(n, close=close)[0]

    def test_gia_cat_len_ma_dai(self):
        # Giá đi ngang 10 suốt 250 phiên (đóng cửa hôm qua = 10 = đúng SMA) → hôm nay 11 là cắt lên cả 3 đường
        st = self.stats(250, lambda i: 10)
        for n in (50, 100, 200):
            self.assertAlmostEqual(st[f'p{n}'], 10)
            self.assertAlmostEqual(st[f'e{n}'], 10)
            for sid in ('PriceCrossAboveSMA', 'PriceCrossAboveEMA'):
                sig = {'id': sid, 'params': {'period': n}}
                self.assertTrue(conditions.eval_signal(sig, st, {'last': 11}), (sid, n))
                self.assertFalse(conditions.eval_signal(sig, st, {'last': 9}), (sid, n))
        # SMA50 cắt lên SMA200: chuẩn hoá giữ nguyên tham số mới
        s = conditions.normalize_signal({'id': 'ShortSMACrossAboveLongSMA', 'params': {'short': 50, 'long': 200}})
        self.assertEqual(s['params'], {'short': 50, 'long': 200})

    def test_chua_du_phien_thi_khong_tinh(self):
        st = self.stats(120, lambda i: 10)
        self.assertIsNotNone(st['p100'])
        self.assertIsNone(st['p200'])
        self.assertFalse(conditions.eval_signal({'id': 'PriceCrossAboveSMA', 'params': {'period': 200}}, st, {'last': 11}))


def ohlc_stats(closes, lows=None, highs=None, vols=None, history=False):
    """Thống kê từ chuỗi giá tự đặt (mặc định thấp / cao = đóng cửa ∓ 0.1, KL 1000), ngày bắt đầu 1/1/2026."""
    n = len(closes)
    days = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    bars = {'s': 'ok', 't': days, 'o': closes, 'h': highs or [c + .1 for c in closes],
            'l': lows or [c - .1 for c in closes], 'c': closes, 'v': vols or [1000] * n}
    today = (date.fromisoformat(days[-1]) + timedelta(days=1)).isoformat()
    return tech.stats_from_bars(bars, today, keep, history), days


class Pullback(unittest.TestCase):
    # Tăng đều 60 phiên (10 → 21.8, SMA20 hôm qua ≈ 20.47, đỉnh cách SMA ~10%) rồi chỉnh 5 phiên về sát SMA20
    RISE = [10 + .2 * i for i in range(60)]
    DIP = [21.2, 20.8, 20.5, 20.4, 20.5]

    def ev(self, id_, st, live, **params):
        return conditions.eval_signal(sig(id_, **params), st, live)

    def test_sma_dang_kiem_dinh(self):
        st, _ = ohlc_stats(self.RISE + self.DIP, vols=[1000] * 60 + [500] * 5)
        self.assertEqual(st['pb20']['pk'], 5)
        self.assertEqual(st['pb20']['vpb'], 500)
        ma = conditions.sma_live(st, 20.6, 20)                 # ≈ 20.55
        self.assertTrue(self.ev('PullbackToSMA', st, lv(20.6, low=20.45, est=500), period=20))
        self.assertTrue(self.ev('PullbackToSMA', st, lv(20.6, low=20.45, est=500), period=20, tol=1, dry='không'))
        self.assertFalse(self.ev('PullbackToSMA', st, lv(ma * .97, low=ma * .96, est=500), period=20))   # rơi khỏi vùng
        self.assertFalse(self.ev('PullbackToSMA', st, lv(21.5, low=21.3, est=500), period=20))         # còn xa SMA
        # KL không cạn (KL dự kiến hôm nay lớn kéo TB lên trên KLTB 20)
        self.assertFalse(self.ev('PullbackToSMA', st, lv(20.6, low=20.45, est=5000), period=20))
        self.assertTrue(self.ev('PullbackToSMA', st, lv(20.6, low=20.45, est=5000), period=20, dry='không'))
        self.assertTrue(self.ev('PullbackToSMA', st, lv(20.6, low=20.45, est=None), period=20))     # chưa mở cửa: KL sau đỉnh
        # Cột khoảng cách tới SMA20 (%)
        self.assertAlmostEqual(conditions.tech_metrics(st, 20.6, .1)['distSMA20'], (20.6 / ma - 1) * 100)

    def test_sma_khong_phai_xu_huong_tang(self):
        down, _ = ohlc_stats([30 - .2 * i for i in range(60)] + [17.9, 18.0, 18.1, 18.0, 18.1])
        self.assertFalse(self.ev('PullbackToSMA', down, lv(18.0, low=17.8, est=1000), period=20, dry='không'))
        flat, _ = ohlc_stats([10 + .01 * i for i in range(65)])     # dốc lên nhẹ, ôm sát MA → chưa từng "đi xa"
        last = conditions.sma_live(flat, 10.64, 20)
        self.assertFalse(self.ev('PullbackToSMA', flat, lv(last, low=last, est=1000), period=20, dry='không'))

    def test_sma_da_dong_cua_thung_sau_dinh(self):
        st, _ = ohlc_stats(self.RISE + [21.2, 19.0, 20.5, 20.4, 20.5])     # 1 phiên đóng cửa dưới SMA ~7%
        self.assertLess(st['pb20']['mr'], .95)
        self.assertFalse(self.ev('PullbackToSMA', st, lv(20.6, low=20.45, est=500), period=20, tol=5, dry='không'))

    def test_sma_bat_len(self):
        st, _ = ohlc_stats(self.RISE + self.DIP, vols=[1000] * 60 + [500] * 5)
        self.assertLess(st['pb20']['lr'], 1)                        # hôm qua giá thấp đã chạm SMA20
        live = lv(20.9, low=20.7, est=500)                          # hôm nay xanh, trên SMA, giá thấp không chạm lại
        self.assertTrue(self.ev('PullbackBounceSMA', st, live, period=20))
        self.assertFalse(self.ev('PullbackToSMA', st, live, period=20, tol=.5))
        self.assertFalse(self.ev('PullbackBounceSMA', st, lv(20.45, low=20.4, est=500), period=20))   # đỏ
        # Lần chạm cách đây 4 phiên, 2 phiên gần nhất đã bật xa khỏi vùng → không còn tính
        far, _ = ohlc_stats(self.RISE + [21.2, 20.6, 20.45, 21.4, 21.6], vols=[1000] * 60 + [500] * 5)
        self.assertGreater(far['pb20']['lr'], 1.02)
        self.assertFalse(self.ev('PullbackBounceSMA', far, lv(21.8, low=21.6, est=500), period=20))

    @staticmethod
    def dist(i, mid=1.5):
        """Khoảng cách giá đóng cửa tới đường: 0 ở ngày 10, 25, 40 (3 lần chạm), cao `mid` ở giữa (2 nhịp: số hoặc
        cặp số); sau đó xa dần tới 3 ở ngày 70 rồi quay về sát đường."""
        if i < 10:
            return .1 * (10 - i)
        if i <= 40:
            h = mid[min((i - 10) // 15, 1)] if isinstance(mid, tuple) else mid
            return h * (1 - abs((i - 10) % 15 - 7.5) / 7.5)
        if i <= 70:
            return .1 * (i - 40)
        return 3 - .1 * (i - 70)

    def zigzag(self, n=100, mid=1.5):
        """Giá đóng cửa chạm đường 10 + 0.05·i ở ngày 10, 25, 40, lên xa đường tới ngày 70 rồi chỉnh về sát đường.
        Trả (đóng cửa, thấp, cao)."""
        closes = [10 + .05 * i + self.dist(i, mid) for i in range(n)]
        return closes, [x - .05 for x in closes], [x + .05 for x in closes]

    def zigzag_down(self, n=100, mid=2):
        """Lật ngược zigzag: giá đóng cửa chạm đường 30 − 0.05·i ở ngày 10, 25, 40, xuống xa đường rồi hồi sát đường."""
        closes = [30 - .05 * i - self.dist(i, mid) for i in range(n)]
        return closes, [x - .05 for x in closes], [x + .05 for x in closes]

    def test_trendline_tu_ve(self):
        closes, lows, highs = self.zigzag()
        st, days = ohlc_stats(closes, lows, highs)
        tl = st['tl6m']
        self.assertEqual((tl['a'], tl['b'], tl['e']), (days[10], days[40], days[40]))
        self.assertAlmostEqual(tl['v'], 14.95)                     # 10 + 0.05·99
        self.assertAlmostEqual(tl['s'], .05)
        self.assertEqual(tl['t'], 3)
        self.assertEqual(tl['pk'], 29)                             # đỉnh ngày 70
        self.assertIsNone(st['tl3m'])                              # 60 phiên gần nhất chỉ còn 1 đáy
        # Hôm nay đường ở 15.0
        self.assertTrue(self.ev('PullbackToTrendline', st, lv(15.1, low=15.02), period='6m', dry='không'))
        self.assertFalse(self.ev('PullbackToTrendline', st, lv(15.1, low=15.02), period='6m'))       # KL không cạn
        self.assertFalse(self.ev('PullbackToTrendline', st, lv(14.5, low=14.4), period='6m', dry='không'))
        self.assertTrue(self.ev('PullbackBounceTrendline', st, lv(15.2, low=15.1), period='6m', dry='không'))
        self.assertFalse(self.ev('PullbackBounceTrendline', st, lv(15.0, low=14.98), period='6m', dry='không'))

    def test_trendline_bi_thung_hoac_thieu_phien(self):
        closes, lows, highs = self.zigzag()
        y = 10 + .05 * 97
        closes[97], lows[97] = y * .97, y * .96               # 1 phiên đóng cửa thủng đường 3%
        st, _ = ohlc_stats(closes, lows, highs)
        self.assertIsNone(st['tl6m'])
        st, _ = ohlc_stats(*self.zigzag(35))
        self.assertIsNone(st['tl6m'])
        # Chỉ 2 điểm chạm (bỏ lần chạm ngày 25) → chưa đủ 3 điểm, không vẽ
        closes, lows, highs = self.zigzag()
        for i in range(20, 31):
            closes[i] += 1
        st, _ = ohlc_stats(closes, lows, highs)
        self.assertIsNone(st['tl6m'])

    def test_trendline_lech_2_phan_tram_van_tinh(self):
        closes, lows, highs = self.zigzag()
        y = 10 + .05 * 25
        closes[25] = y * .985                                       # lần chạm thứ 3 xuyên đường 1,5% → vẫn là 1 đường
        st, days = ohlc_stats(closes, lows, highs)
        self.assertEqual((st['tl6m']['a'], st['tl6m']['b'], st['tl6m']['t']), (days[10], days[40], 3))

    def test_trendline_tang_can_dinh_cao_dan(self):
        # Đỉnh giữa các đáy ≈ 17.4 rồi 17.2, đỉnh sau đáy cuối chỉ ≈ 16.55 → đáy cao dần nhưng đỉnh thấp dần
        st, _ = ohlc_stats(*self.zigzag(mid=(7, 6)))
        self.assertIsNone(st['tl6m'])

    def test_vuot_len_trendline_giam(self):
        closes, lows, highs = self.zigzag_down()
        st, days = ohlc_stats(closes, lows, highs)
        td = st['td6m']
        self.assertEqual((td['a'], td['b'], td['t']), (days[10], days[40], 3))
        self.assertAlmostEqual(td['v'], 25.05)                     # 30 − 0.05·99
        self.assertAlmostEqual(td['s'], -.05)
        self.assertEqual(len(td['cr']), tech.TL_RECENT)
        self.assertIsNone(st['tl6m'])                              # đỉnh thấp dần → không có trendline tăng
        # Hôm nay đường ở 25.0: vượt ≥ 1% là từ 25.25
        brk = lambda last, est, **p: self.ev('BreakDownTrendline', st, lv(last, est=est), period='6m', **p)
        self.assertTrue(brk(25.3, 2000))
        self.assertFalse(brk(25.1, 2000))                         # mới nhích qua đường, chưa đủ 1%
        self.assertFalse(brk(25.3, 500))                          # KL thấp
        self.assertTrue(brk(25.3, 500, vol='không'))
        self.assertTrue(brk(25.1, 2000, brk=0))
        # Chưa vượt thì chưa có nhịp pullback sau vượt
        self.assertFalse(self.ev('PullbackBrokenDownTrendline', st, lv(25.1, low=25.0), period='6m'))
        # Giữa các lần chạm giá chỉ lùi dưới đường ~3% (chưa đủ 5%) → đường chưa có ý nghĩa, không vẽ
        st, _ = ohlc_stats(*self.zigzag_down(mid=.8))
        self.assertIsNone(st['td6m'])

    def retest(self, fail=False, history=False):
        """Trendline giảm như trên; ngày 95 đóng cửa vượt đường 3%, lùi về, ngày 98 giá thấp chạm lại đường."""
        closes, lows, highs = self.zigzag_down()
        y = lambda i: 30 - .05 * i
        for i, r in zip(range(93, 100), (.99, .995, 1.03, 1.04, .97 if fail else 1.025, 1.01, 1.012)):
            closes[i], lows[i], highs[i] = y(i) * r, y(i) * r - .05, y(i) * r + .05
        lows[98] = y(98) * 1.003
        return ohlc_stats(closes, lows, highs, history=history)

    def test_pullback_sau_khi_vuot_trendline_giam(self):
        st, days = self.retest()
        td = st['td6m']
        self.assertEqual((td['a'], td['b']), (days[10], days[40]))      # đỉnh mới sau khi vượt không làm điểm nối
        ev = lambda id_, last, low: self.ev(id_, st, lv(last, low=low), period='6m')
        # Hôm nay đường ở 25.0; hôm qua đóng cửa 25.35
        self.assertTrue(ev('BounceBrokenDownTrendline', 25.6, 25.3))        # hôm qua chạm, hôm nay xanh trên đường
        self.assertFalse(ev('BounceBrokenDownTrendline', 25.2, 25.1))       # đỏ
        self.assertTrue(ev('PullbackBrokenDownTrendline', 25.2, 25.1))      # đang về sát đường
        self.assertFalse(ev('PullbackBrokenDownTrendline', 26.0, 25.8))     # còn xa đường
        self.assertFalse(ev('PullbackBrokenDownTrendline', 24.0, 23.9))     # rơi lại dưới đường quá 2%
        self.assertFalse(self.ev('BreakDownTrendline', st, lv(26, est=5000), period='6m'))   # đã vượt từ trước
        # Vượt hụt: sau phiên vượt có phiên đóng cửa rơi xuống dưới đường 3%
        st, _ = self.retest(fail=True)
        self.assertFalse(self.ev('BounceBrokenDownTrendline', st, lv(25.6, low=25.3), period='6m'))
        self.assertFalse(self.ev('PullbackBrokenDownTrendline', st, lv(25.2, low=25.1), period='6m'))

    def test_quet_lui_phien_vuot_trendline_giam(self):
        st, days = self.retest(history=True)
        self.assertEqual((st['tb6m']['k'], st['tb6m']['d']), (5, days[95]))     # ngày 95 = 5 phiên trước hôm nay
        m = conditions.tech_metrics(st, 25.6, .2, 1000)
        self.assertEqual((m['brkTL6m'], m['brkTL6mDay']), (5, days[95][8:] + '/' + days[95][5:7]))
        self.assertEqual(core.format_cell(m, 'brkTL6m'), (days[95][8:] + '/' + days[95][5:7], ''))
        self.assertIsNone(m['brkTL3m'])                            # 60 phiên gần nhất không có trendline giảm
        # Giá vượt = giá đóng cửa ngày 95 (đường 25.25 × 1.03); % hiện tại so với giá đó
        self.assertAlmostEqual(m['brkTL6mPx'], 25.25 * 1.03)
        self.assertAlmostEqual(m['brkTL6mPct'], (25.6 / (25.25 * 1.03) - 1) * 100)
        self.assertEqual(core.format_cell(m, 'brkTL6mPct'), ('-1.57%', 'down'))
        self.assertIsNone(m['brkTL3mPx'])
        # Lọc 1 cột trong nhóm thì cả nhóm (phiên vượt · giá vượt · %) cùng hiện, đúng thứ tự
        cols = [k for k, _ in core.extra_columns({'brkTL6mPct': {'operator': 'le', 'value': 5}})]
        self.assertEqual(cols, ['brkTL6m', 'brkTL6mPx', 'brkTL6mPct'])
        self.assertTrue(core.needs_break_history({'filters': {'brkTL6mPx': {'operator': 'ge', 'value': 1}}}))
        # Phiên vượt KL thấp hơn KLTB 20 thì không tính
        closes, lows, highs = self.zigzag_down()
        y = lambda i: 30 - .05 * i
        closes[95] = y(95) * 1.03
        st, _ = ohlc_stats(closes, lows, highs, vols=[1000] * 95 + [500] + [1000] * 4, history=True)
        self.assertIsNone(st['tb6m'])
        # Chưa vượt phiên nào: hôm nay vượt (KL dự kiến đủ) → 0, hiện "hôm nay"; không bật quét lùi thì không có số cũ
        st, _ = ohlc_stats(*self.zigzag_down(), history=True)
        self.assertIsNone(st['tb6m'])
        m = conditions.tech_metrics(st, 25.3, .3, 2000)
        self.assertEqual(m['brkTL6m'], 0)
        self.assertEqual(core.format_cell(m, 'brkTL6m'), ('hôm nay', 'up'))
        self.assertEqual((m['brkTL6mPx'], m['brkTL6mPct']), (25.3, 0))          # vượt hôm nay: giá vượt = giá hiện tại
        self.assertIsNone(conditions.tech_metrics(st, 25.3, .3, 500)['brkTL6m'])
        self.assertNotIn('tb6m', ohlc_stats(*self.zigzag_down())[0])

    def test_tham_so_va_mo_ta(self):
        s = conditions.normalize_signal({'id': 'PullbackToSMA', 'params': {'period': 50, 'tol': 1.5, 'dry': 'không'}})
        self.assertEqual(s['params'], {'period': 50, 'tol': 1.5, 'dry': 'không'})
        self.assertEqual(sig('PullbackToSMA', period=7, dry='?')['params'], {'period': 20, 'tol': 2, 'dry': 'có'})
        self.assertEqual(conditions.describe_signal(s), 'Pullback về SMA(50), vùng ±1.5%, KL cạn: không')
        self.assertEqual(conditions.describe_signal(sig('PullbackBounceTrendline', period='3m')),
                         'Bật lên từ trendline tăng 3 tháng, vùng ±2%, KL cạn: có')
        self.assertIn(('Pullback về SMA(…), vùng ±…%, KL cạn: …', 'signal', 'PullbackToSMA'),
                      conditions.catalog()['pullback'])


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
        self.assertEqual(sum(len(v) for v in cat.values()), 43 + 79)        # 43 cột số + 79 tín hiệu
        self.assertEqual(cat['price'][0], ('Thay đổi giá 1 tuần (%)', 'metric', 'change1w'))     # cột số trước tín hiệu
        self.assertIn(('Giá cắt lên SMA(…)', 'signal', 'PriceCrossAboveSMA'), cat['ma'])
        self.assertIn(('MACD cắt lên đường 0', 'signal', 'MACDCrossAboveZeroLine'), cat['macd'])
        self.assertEqual(conditions.param_text('1m'), '1 tháng')
        self.assertEqual(conditions.param_text(70.0), '70')
        self.assertEqual(conditions.param_text(3.5), '3.5')

    def test_danh_muc_du_79_tin_hieu(self):
        self.assertEqual(len(conditions.SIGNAL_LIST), 79)
        groups = {g for g, _ in conditions.GROUPS}
        for s in conditions.SIGNAL_LIST:
            self.assertIn(s.group, groups)
            for p in s.params:                           # mặc định phải nằm trong danh sách chọn
                self.assertIn(p.default, p.choices)


class RsiTaoDay(unittest.TestCase):
    """RSI tạo đáy (luật Long hệ phái sinh của anh) + chọn khung 15 phút / ngày. Đã đối chiếu với code pandas bên hệ
    phái sinh trên nến 15 phút thật (9 mã × 120 nến, 0 lệch)."""
    # RSI 30 nến 15 phút đã chốt: rơi xuống đáy 23 (13 nến trước) rồi đi lên 44
    RS = [50] * 10 + [45, 40, 35, 30, 26, 24, 23, 25, 27, 29, 31, 33, 35, 37, 38, 39, 40, 41, 42, 44]

    def ev15(self, rs=None, lc=11, p10=10, **params):
        st = {'rs': self.RS if rs is None else rs, 'lc': lc, 'p10': p10}
        return conditions.eval_signal(sig('RSIBottom', tf='15m', **params), None, {**lv(lc), 'intra': {'15m': st}})

    def test_du_3_dau_hieu_khung_15_phut(self):
        self.assertTrue(self.ev15())
        self.assertFalse(self.ev15(look=8))                       # đáy 23 nằm ngoài 8 nến gần nhất
        self.assertFalse(self.ev15(rs=self.RS[:-1] + [29]))       # RSI chưa thoát vùng 30
        self.assertFalse(self.ev15(rs=self.RS[:-1] + [31]))       # thoát 30 nhưng tụt dưới Signal (WMA14 ≈ 36.3)
        self.assertFalse(self.ev15(lc=9.9))                       # giá dưới MA10
        self.assertTrue(self.ev15(level=25))                      # đáy 23 ≤ 25, RSI 44 > 25
        self.assertFalse(self.ev15(level=20))                     # đáy chưa xuống tới 20
        self.assertFalse(self.ev15(rs=self.RS[-10:]))             # thiếu nến (WMA14 cần 14 RSI)
        # Khung 15 phút chỉ đọc thống kê nến 15 phút: chưa tải (hoặc mã ít nến) thì không khớp
        s = sig('RSIBottom', tf='15m')
        self.assertFalse(conditions.eval_signal(s, {'rs': self.RS, 'lc': 11, 'p10': 10}, lv(11)))
        self.assertFalse(conditions.eval_signal(s, {'lc': 1}, {**lv(11), 'intra': {'15m': {}}}))

    def test_khung_ngay_ghep_gia_hien_tai_khop_voi_nen_da_chot(self):
        # Rơi đều 60 nến rồi tăng 3 nến (RSI ≈ 28.6): giá hiện tại quyết định nến thứ 4 có đủ 3 dấu hiệu không.
        # Khung ngày (ghép giá hiện tại) phải cho đúng kết quả như khi giá đó đã là nến chốt (cách tính khung 15 phút).
        closes = [60 - .5 * i for i in range(60)] + [30.5 + .8 * j for j in range(1, 4)]
        bars, days = make_bars(len(closes), close=lambda i: closes[i])
        st = tech.stats_from_bars(bars, (date.fromisoformat(days[-1]) + timedelta(days=1)).isoformat(), keep)
        seen = set()
        for live in (31.5, 32.4, 32.9, 33.3, 33.7, 35):
            c = closes + [live]
            intra = tech.intraday_stats({'s': 'ok', 't': list(range(len(c))), 'o': c, 'h': c, 'l': c, 'c': c,
                                         'v': [1] * len(c)})
            want = conditions.eval_signal(sig('RSIBottom', tf='15m'), None, {**lv(live), 'intra': {'15m': intra}})
            self.assertEqual(conditions.eval_signal(sig('RSIBottom', tf='D'), st, lv(live)), want, live)
            seen.add(want)
        self.assertEqual(seen, {True, False})                    # có cả ca khớp lẫn không khớp

    def test_rsi_tung_nen_khop_wilder(self):
        closes = [10 + (i % 7) - (i % 3) * .5 for i in range(60)]
        rs = tech.rsi_tail(closes)
        self.assertEqual(len(rs), tech.RSI_KEEP)
        self.assertAlmostEqual(rs[-1], tech.rsi_of(*tech.wilder_rsi_parts(closes)))
        self.assertAlmostEqual(rs[-2], tech.rsi_of(*tech.wilder_rsi_parts(closes[:-1])))
        self.assertEqual(tech.rsi_tail(closes[:14]), [])
        self.assertEqual(len(stats_of(60)[0]['rs']), tech.RSI_KEEP)        # nến ngày cũng giữ RSI từng nến

    def test_nen_15_phut_da_chot(self):
        at = lambda d, h, m: datetime(2026, 10, d, h, m, 30, tzinfo=VN)     # 29/10 thứ Năm, 31/10 thứ Bảy
        cut = lambda *a: tech.intraday_cutoff(at(*a))
        self.assertEqual(cut(29, 9, 7), at(29, 9, 0).replace(second=0))
        self.assertEqual(cut(29, 11, 29), at(29, 11, 15).replace(second=0))
        self.assertEqual(cut(29, 14, 50), at(29, 14, 45).replace(second=0))  # nến ATC chờ tới 15:00
        for a in ((29, 8, 50), (29, 11, 30), (29, 12, 59), (29, 15, 0), (31, 10, 0)):
            self.assertIsNone(cut(*a), a)
        key = lambda *a: tech.intraday_key(at(*a))
        self.assertEqual(key(29, 9, 7), '2026-10-29 09:00')
        self.assertEqual(key(29, 12, 0), '2026-10-29 11:30')                # nghỉ trưa: đã có nến 11:15 chốt
        self.assertEqual(key(29, 20, 0), '2026-10-29 15:00')
        self.assertEqual(key(29, 8, 0), '2026-10-29 00:00')
        self.assertEqual(key(31, 10, 0), '2026-10-31 00:00')
        # Nến có giờ mở từ cutoff trở đi (đang chạy) bị bỏ; None = mọi nến; quá ít nến → None
        c = [10 + i % 5 for i in range(70)]
        bars = {'s': 'ok', 't': [i * 900 for i in range(70)], 'o': c, 'h': c, 'l': c, 'c': c, 'v': [1] * 70}
        st = tech.intraday_stats(bars, 65 * 900)
        self.assertEqual((st['n'], st['lt'], st['lc']), (65, 64 * 900, c[64]))
        self.assertEqual(st['p10'], sum(c[55:65]) / 10)
        self.assertEqual(tech.intraday_stats(bars)['n'], 70)
        self.assertIsNone(tech.intraday_stats(bars, 50 * 900))
        self.assertIsNone(tech.intraday_stats({'s': 'no_data'}))

    def test_tham_so_mo_ta_va_noi_vao_bo_loc(self):
        self.assertEqual(sig('RSIBottom')['params'], {'tf': '15m', 'level': 30, 'look': 16})
        self.assertEqual(sig('RSIBottom', tf='4h', look=17)['params'], {'tf': '15m', 'level': 30, 'look': 16})
        self.assertEqual(conditions.describe_signal(sig('RSIBottom', tf='D')),
                         'RSI tạo đáy khung ngày: thoát quá bán 30 (đáy trong 16 nến), RSI trên Signal, giá trên MA10')
        self.assertEqual(conditions.param_text('15m'), '15 phút')
        m15, day = {'signals': [sig('RSIBottom')]}, {'signals': [sig('RSIBottom', tf='D')]}
        self.assertEqual((core.needs_intraday(m15), core.needs_tech(m15)), (True, False))   # khỏi tải nến ngày cả năm
        self.assertEqual((core.needs_intraday(day), core.needs_tech(day)), (False, True))
        self.assertFalse(core.needs_intraday({'signals': [sig('MACDAboveZeroLine')]}))
        q = {'Symbol': 'AAA', 'Exchange': 'HOSTC', 'PriceCurrent': 11000, 'TotalVolume': 0}
        st = {'rs': self.RS, 'lc': 11, 'p10': 10}
        row = core.transform_quote(q, intra={'15m': st})
        self.assertEqual(row['_live']['intra'], {'15m': st})
        self.assertEqual(core.apply_signals([row], m15['signals']), [row])
        self.assertNotIn('intra', core.transform_quote(q)['_live'])


class ChiBaoBoSung(unittest.TestCase):
    """Parabolic SAR, Stochastic, Williams %R, CCI, ADX / DMI, OBV, Ichimoku, giá so với MA, các cột số chỉ báo.
    Đã đối chiếu trên nến thật: SAR khớp hẳn bản chép ta.sar của TradingView; Stochastic / %R / CCI / ADX / ATR /
    Ichimoku khớp thư viện ta 0.11 (OBV theo cách chuẩn: phiên đứng giá không cộng KL)."""
    # Tăng đều: đóng cửa 1..60, cao = đóng + 0.5, thấp = đóng − 0.5, KL 1000
    ST = stats_of(60)[0]

    def ev(self, id_, live, st=None, **params):
        return conditions.eval_signal(sig(id_, **params), st or self.ST, live)

    def test_parabolic_sar(self):
        self.assertEqual(self.ST['sart'], 1)
        self.assertLess(self.ST['sar'], 59.5)                              # SAR dưới giá thấp
        self.assertTrue(self.ev('SARUptrend', lv(61, high=61.5, low=60.5)))
        self.assertFalse(self.ev('SARFlipDown', lv(61, high=61.5, low=60.5)))
        crash = lv(50, high=60, low=49)                                    # giá thấp hôm nay thủng SAR → đảo chiều giảm
        self.assertTrue(self.ev('SARFlipDown', crash))
        self.assertTrue(self.ev('SARDowntrend', crash))
        self.assertFalse(self.ev('SARUptrend', crash))
        self.assertFalse(self.ev('SARFlipUp', crash))
        # Một phiên: SAR mới = SAR + af·(EP − SAR); thủng thì nhảy về EP cũ (hoặc giá cao hôm nay nếu cao hơn)
        self.assertEqual(tech.sar_step(10, 20, .1, True, 21, 15), (11, 21, .1 + .02, True, False))
        self.assertEqual(tech.sar_step(10, 20, .1, True, 22, 9), (22, 9, .02, False, True))

    def test_stochastic_va_williams(self):
        # %K thô 14 phiên = (đóng − thấp nhất) / (cao nhất − thấp nhất) = 13.5 / 14
        self.assertAlmostEqual(self.ST['skr'][-1], 13.5 / 14 * 100, places=5)      # số lưu làm tròn 6 chữ số
        self.assertAlmostEqual(self.ST['skd'], 13.5 / 14 * 100, places=5)
        self.assertTrue(self.ev('StochAboveOverBoughtLine', lv(61, high=61.5), level=80))
        drop = lv(50, high=60, low=50)
        self.assertTrue(self.ev('StochKCrossBelowD', drop))                # %K tụt dưới %D
        self.assertTrue(self.ev('StochCrossBelowOverBoughtLine', drop, level=80))
        self.assertTrue(self.ev('WillRCrossBelowOverBoughtLine', drop, level=20))   # %R từ −3.6 xuống dưới −20
        self.assertFalse(self.ev('StochKCrossAboveD', drop))
        self.assertIsNone(tech.raw_k([(0, 1, 5, 5, 5, 1)] * 14, 13))       # cao nhất = thấp nhất → không tính

    def test_cci(self):
        self.assertAlmostEqual(tech.cci([1, 2, 3]), 100)                   # (3 − 2) / (0.015 × 2/3)
        self.assertIsNone(tech.cci([5, 5, 5]))
        self.assertTrue(self.ev('CCIAboveOverBoughtLine', lv(70, high=70, low=69), level=100))
        self.assertFalse(self.ev('CCIBelowOverSoldLine', lv(70, high=70, low=69), level=100))

    def test_adx_dmi(self):
        self.assertEqual(tech.dm_tr((0, 0, 11, 9, 10), (0, 0, 12, 10, 11)), (1, 0.0, 2))
        self.assertEqual(tech.dx_frac(0, 0), 0)
        r = conditions.dmi_now(self.ST, lv(61, high=61.5, low=60.5))
        self.assertGreater(r[2], r[3])                                     # tăng đều: +DI > −DI
        self.assertGreater(r[4], 25)
        self.assertTrue(self.ev('ADXStrongUptrend', lv(61, high=61.5, low=60.5), level=25))
        self.assertTrue(self.ev('ADXAboveLevel', lv(61, high=61.5, low=60.5), level=25))
        self.assertFalse(self.ev('DIPlusCrossAboveDIMinus', lv(61, high=61.5, low=60.5)))

    def test_obv(self):
        self.assertEqual((self.ST['obv'], self.ST['ob19'], self.ST['obm']), (59000, 950000, 49500))
        self.assertTrue(self.ev('OBVAboveMA', lv(61, est=1000)))
        self.assertTrue(self.ev('OBVCrossBelowMA', lv(50, est=50000)))     # OBV 59000 − 50000 < TB 47950
        self.assertFalse(self.ev('OBVCrossAboveMA', lv(61, est=1000)))

    def test_ichimoku(self):
        st = stats_of(100)[0]
        self.assertEqual(tech.mid_range(tech.closed_bars(make_bars(100)[0], '2099-01-01', keep), 99, 9), 96)   # (100 + 92) / 2
        self.assertTrue(self.ev('IchimokuAboveCloud', lv(101), st))
        self.assertFalse(self.ev('IchimokuBelowCloud', lv(101), st))
        self.assertTrue(self.ev('IchimokuBelowCloud', lv(1), st))
        self.assertFalse(self.ev('IchimokuAboveCloud', lv(1), self.ST))    # 60 phiên: chưa đủ để có mây

    def test_gia_so_voi_ma_va_ema_cat_nhau(self):
        self.assertTrue(self.ev('PriceAboveSMA', lv(61), period=20))
        self.assertFalse(self.ev('PriceBelowSMA', lv(61), period=20))
        self.assertTrue(self.ev('PriceBelowEMA', lv(40), period=20))
        self.assertTrue(self.ev('ShortSMAAboveLongSMA', lv(61), short=5, long=15))
        self.assertFalse(self.ev('ShortSMAAboveLongSMA', lv(61)))          # SMA200 chưa đủ phiên
        self.assertTrue(self.ev('ShortEMACrossBelowLongEMA', lv(1), short=10, long=20))
        self.assertFalse(self.ev('ShortEMACrossAboveLongEMA', lv(61), short=10, long=20))
        self.assertEqual(sig('ShortEMACrossAboveLongEMA', short=50, long=20)['params'], {'short': 10, 'long': 20})

    def test_cot_so_chi_bao(self):
        m = conditions.indicator_metrics(self.ST, lv(61, high=61.5, low=60, volume=1000))
        self.assertEqual(m['rsi14'], 100.0)                                # chưa phiên nào giảm
        self.assertAlmostEqual(m['fromHigh1m'], (61.5 - 61) / 61.5 * 100)  # đỉnh tính cả giá cao hôm nay
        self.assertAlmostEqual(m['willR'], m['stochK'] - 100, delta=5)
        for k in ('mfi14', 'stochK', 'cci20', 'bbWidth', 'adx14', 'atrPct', 'fromLow1y'):
            self.assertIsNotNone(m[k], k)
        self.assertTrue(all(v is None for v in conditions.indicator_metrics(None, lv(61)).values()))
        self.assertEqual((self.ST['v50'], self.ST['v100']), (1000, None))  # 60 phiên: chưa đủ KLTB 100
        self.assertAlmostEqual(self.ST['gv20'], 50.5 * 1000 / 1e6)        # GTTB 20: giá 41..60 × 1000 cp, tỷ đồng
        self.assertEqual(core.format_metric(12.345, 'upct'), ('12.3%', ''))
        self.assertEqual(core.format_metric(-45.67, 'num'), ('-45.7', ''))
        self.assertEqual(core.format_metric(3.46, 'bil'), ('3.5 tỷ', ''))


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
