"""Test phần lõi — chạy: python -m unittest (đứng ở thư mục D:\\BeeVnMini)."""
import calendar
import unittest

import core

# Dữ liệu giống hình mẫu: VIB 14.2 +0.3 (+2.54%), KL 3.0M
VIB = {'symbol': 'VIB', 'price': 14.2, 'change': 0.3, 'changePercent': 2.54, 'volume': 3000000,
       'volRatio': 0, 'value': 42.9, 'demandStrength': 76}
FPT = {'symbol': 'FPT', 'price': 98.5, 'change': -1.2, 'changePercent': -1.2, 'volume': 5200000,
       'volRatio': 130, 'value': 512.3, 'demandStrength': 40}
HPG = {'symbol': 'HPG', 'price': 26.1, 'change': 0.4, 'changePercent': 1.56, 'volume': 800000,
       'volRatio': 90, 'value': 20.8, 'demandStrength': None}

FILTERS = {
    'price': {'operator': 'lt', 'value': 20},
    'changePercent': {'operator': 'gt', 'value': 2},
    'volume': {'operator': 'gt', 'value': 1000000},
}

# Quote FireAnt thật của VIB lúc 10:04 ngày 14/10/2026 (rút gọn trường).
VIB_Q = {
    'Symbol': 'VIB', 'Name': 'Ngân hàng TMCP Quốc tế Việt Nam', 'Exchange': 'HOSTC',
    'PriceCurrent': 14000, 'PriceChange': 200, 'PricePercentChange': 0.01449275362318847,
    'TotalVolume': 4505800, 'TotalValue': 63403235000,
    'TotalActiveBuyVolume': 2566950, 'PriceAverage': 14071.4712148786,
}


class LocGiongWeb(unittest.TestCase):
    def test_chi_giu_ma_thoa_het_dieu_kien(self):
        self.assertEqual([s['symbol'] for s in core.apply_filters([VIB, FPT, HPG], FILTERS)], ['VIB'])

    def test_bo_qua_loc_rong_thieu_gia_tri_coi_nhu_0(self):
        self.assertEqual(len(core.apply_filters([VIB, FPT], {'price': {'operator': 'gt', 'value': ''}})), 2)
        self.assertEqual(len(core.apply_filters([HPG], {'demandStrength': {'operator': 'lt', 'value': 1}})), 1)

    def test_thu_gon_hien_ma_va_cot_dang_loc(self):
        self.assertEqual([c[0] for c in core.compact_columns(FILTERS)], ['symbol', 'price', 'changePercent', 'volume'])
        self.assertEqual([c[0] for c in core.compact_columns({})], ['symbol'])

    def test_loc_theo_san_va_sap_xep(self):
        all_ = {'HSX': [VIB, HPG], 'HNX': [FPT], 'UPCOM': []}
        cfg = {'exchange': 'HSX', 'filters': {'volume': {'operator': 'gt', 'value': 0}},
               'sortColumn': 'value', 'sortDirection': 'desc'}
        self.assertEqual([s['symbol'] for s in core.select_matches(all_, cfg)], ['VIB', 'HPG'])
        self.assertEqual([s['symbol'] for s in core.select_matches(all_, {**cfg, 'exchange': 'ALL'})], ['FPT', 'VIB', 'HPG'])
        self.assertEqual([s['symbol'] for s in core.select_matches(all_, {**cfg, 'sortColumn': 'symbol', 'sortDirection': 'asc'})],
                         ['HPG', 'VIB'])
        # Cột thiếu số (None) luôn xuống cuối khi giảm dần
        self.assertEqual([s['symbol'] for s in core.sort_stocks([HPG, VIB], 'demandStrength', 'desc')], ['VIB', 'HPG'])

    def test_ca_3_san_them_cot_san(self):
        cfg = {'exchange': 'ALL', 'filters': FILTERS}
        self.assertEqual([c[0] for c in core.table_columns(cfg, False)],
                         ['symbol', 'exchange', 'price', 'changePercent', 'volume'])
        self.assertEqual(len(core.table_columns(cfg, True)), 12)
        self.assertNotIn('exchange', [c[0] for c in core.table_columns({**cfg, 'exchange': 'HSX'}, True)])
        self.assertEqual(core.format_cell({'exchange': 'UPCOM'}, 'exchange'), ('UpCom', 'muted'))

    def test_dinh_dang_giong_hang_vib(self):
        self.assertEqual(core.format_cell(VIB, 'price'), ('14.2', 'up'))
        self.assertEqual(core.format_cell(VIB, 'change')[0], '+0.3')
        self.assertEqual(core.format_cell(VIB, 'changePercent'), ('+2.54%', 'up'))
        self.assertEqual(core.format_cell(VIB, 'volume')[0], '3.0M')
        self.assertEqual(core.format_cell(VIB, 'value')[0], '42.9 tỷ')
        self.assertEqual(core.format_cell(VIB, 'demandStrength'), ('76%', 'up'))
        self.assertEqual(core.format_cell(FPT, 'changePercent'), ('-1.20%', 'down'))
        self.assertEqual(core.format_cell(HPG, 'demandStrength')[0], '—')
        self.assertEqual(core.format_cell({'ma10': 11.0}, 'ma10')[0], '11')

    def test_lam_tron_nhu_javascript(self):
        # 0.25 là số nhị phân chính xác: JS toFixed(1) → "0.3", round() của Python → 0.2
        self.assertEqual(core.format_price(0.25), '0.3')
        self.assertEqual(core.format_price(13.95), '13.9')   # 13.95 thật ra là 13.9499999…, JS cũng ra 13.9
        self.assertEqual(core.format_volume(999), '999')

    def test_mo_ta_bo_loc(self):
        self.assertEqual(core.describe_filters(FILTERS), 'Giá < 20 · % Thay đổi > 2 · KLGD > 1000000')

    def test_gio_giao_dich_theo_gio_vn(self):
        ts = lambda y, mo, d, h, mi: calendar.timegm((y, mo, d, h, mi, 0))
        self.assertTrue(core.is_trading_time(ts(2026, 10, 14, 3, 0)))    # thứ Tư 10:00 VN
        self.assertFalse(core.is_trading_time(ts(2026, 10, 14, 9, 0)))   # 16:00 VN
        self.assertFalse(core.is_trading_time(ts(2026, 10, 17, 3, 0)))   # thứ Bảy


class NguonDuLieu(unittest.TestCase):
    def test_doi_quote_fireant_sang_hang_bang_gia(self):
        r = core.transform_quote(VIB_Q, {'ma10': 13.7, 'ma20': 13.6, 'ma45': 13.4, 'avgVol': 4505800 / 2})
        self.assertEqual((r['symbol'], r['exchange'], r['price'], r['change']), ('VIB', 'HSX', 14, 0.2))
        self.assertEqual((r['changePercent'], r['volume'], r['value'], r['volRatio']), (1.45, 4505800, 63.4, 200))
        self.assertEqual(r['ma10'], 13.7)
        self.assertEqual(r['demandStrength'], 57)   # 2.566.950 × 14.071 / 63,4 tỷ

    def test_thieu_lich_su_khong_vo(self):
        r = core.transform_quote(VIB_Q, None)
        self.assertIsNone(r['ma10'])
        self.assertIsNone(r['volRatio'])
        self.assertEqual(core.format_cell(r, 'volRatio'), ('--', 'muted'))
        # Lọc vẫn theo kiểu web: thiếu số coi như 0
        self.assertEqual(core.apply_filters([r], {'volRatio': {'operator': 'lt', 'value': 1}}), [r])

    def test_luc_cau_bo_ma_nhieu(self):
        self.assertIsNone(core.luc_cau({**VIB_Q, 'TotalValue': 50_000_000}))
        self.assertIsNone(core.luc_cau({**VIB_Q, 'TotalVolume': 20_000}))
        self.assertIsNone(core.luc_cau({**VIB_Q, 'TotalActiveBuyVolume': 4_000_000}))

    def test_gom_theo_san_bo_otc(self):
        rows = [core.transform_quote({**VIB_Q, 'Symbol': f'X{i}', 'Exchange': ex})
                for i, ex in enumerate(['HOSTC', 'HASTC', 'UPCOM', 'OTC'])]
        g = core.group_by_exchange(rows)
        self.assertEqual([len(g['HSX']), len(g['HNX']), len(g['UPCOM'])], [1, 1, 1])

    def test_ma_tren_phien_da_dong_bo_nen_hom_nay(self):
        start = calendar.timegm((2026, 8, 1, 0, 0, 0))   # 07:00 giờ VN
        n = 50
        t = [start + i * 86400 for i in range(n)]
        c = list(range(1, n + 1))
        v = [1000] * n
        c[-1], v[-1] = 999, 999999          # nến "hôm nay" — phải bị bỏ
        s = core.hist_stats({'s': 'ok', 't': t, 'c': c, 'v': v}, core.vn_date(t[-1]))
        self.assertEqual((s['ma10'], s['ma20'], s['ma45'], s['avgVol']), (44.5, 39.5, 27, 1000))

    def test_lich_su_ngan_hoac_khong_co(self):
        s = core.hist_stats({'s': 'ok', 't': [1, 2, 3], 'c': [1, 2, 3], 'v': [1, 1, 1]}, '2099-01-01')
        self.assertIsNone(s['ma45'])
        self.assertEqual(s['avgVol'], 0)
        self.assertIsNone(core.hist_stats({'s': 'no_data'}, '2099-01-01'))
        self.assertIsNone(core.hist_stats(None, '2099-01-01'))



class FireAntCookie(unittest.TestCase):
    def test_doc_trading_statistic_giong_server_bee(self):
        data = [{'Symbol': 'VIB', 'AvgPrice10d': 13585.0, 'AvgPrice20d': 13520.0, 'AvgPrice45d': 13470.0,
                 'AvgVolume45d': 4728061.0},
                {'Symbol': 'XYZ', 'AvgPrice10d': 0, 'AvgVol45': 1000}]
        out = core.parse_trading_stats(data)
        self.assertEqual(out['VIB'], {'ma10': 13.59, 'ma20': 13.52, 'ma45': 13.47, 'avgVol': 4728061.0})
        self.assertEqual(out['XYZ']['ma10'], None)
        self.assertEqual(out['XYZ']['avgVol'], 1000)
        r = core.transform_quote(VIB_Q, out['VIB'])
        self.assertEqual(r['volRatio'], 95)        # 4.505.800 / 4.728.061

    def test_phan_hoi_rong_hoac_sai_la_cookie_het_han(self):
        for bad in ([], {'Message': 'Authorization has been denied for this request.'}, None):
            with self.assertRaises(core.CookieExpired):
                core.parse_trading_stats(bad)


if __name__ == '__main__':
    unittest.main()
