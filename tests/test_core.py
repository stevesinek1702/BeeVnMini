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

    def test_bam_tieu_de_cot_de_sap_xep(self):
        self.assertEqual(core.next_sort('value', 'desc', 'value'), ('value', 'asc'))
        self.assertEqual(core.next_sort('value', 'asc', 'value'), ('value', 'desc'))
        self.assertEqual(core.next_sort('value', 'desc', 'changePercent'), ('changePercent', 'desc'))
        self.assertEqual(core.next_sort('value', 'desc', 'symbol'), ('symbol', 'asc'))
        # Xếp theo sàn: cùng sàn thì GTGD lớn trước
        rows = [{'symbol': 'A', 'exchange': 'HSX', 'value': 1}, {'symbol': 'B', 'exchange': 'HNX', 'value': 5},
                {'symbol': 'C', 'exchange': 'HSX', 'value': 9}]
        self.assertEqual([r['symbol'] for r in core.sort_stocks(rows, 'exchange', 'asc')], ['B', 'C', 'A'])

    def test_dinh_dang_giong_hang_vib(self):
        self.assertEqual(core.format_cell(VIB, 'symbol'), ('VIB', 'up'))       # mã cùng màu với giá
        self.assertEqual(core.format_cell(FPT, 'symbol'), ('FPT', 'down'))
        self.assertEqual(core.HEAD_LABEL['changePercent'], '%')
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

    def test_cau_doc_ma_moi(self):
        self.assertEqual(core.alert_text(['VIB', 'MBB']), ('Mã mới: V I B, M B B.', 'New: V I B, M B B.'))
        vi, en = core.alert_text(['A1', 'B2', 'C3', 'D4', 'E5', 'F6', 'G7'])
        self.assertEqual(vi, 'Mã mới: A 1, B 2, C 3, D 4, E 5, và 2 mã khác.')
        self.assertTrue(en.endswith('and 2 more.'))

    def test_so_phien_ban_va_ban_moi(self):
        self.assertGreater(core.version_tuple('1.10.0'), core.version_tuple('1.9.9'))
        self.assertEqual(core.version_tuple('v1.2'), (1, 2))
        good = {'version': '1.2.0', 'url': 'https://raw.githubusercontent.com/x/y/release/BeeVnMini.exe',
                'sha256': 'a' * 64, 'size': 123, 'notes': 'Sửa màu'}
        self.assertEqual(core.parse_update(good, '1.1.0')['version'], '1.2.0')
        self.assertIsNone(core.parse_update(good, '1.2.0'))                 # đã là bản mới nhất
        self.assertIsNone(core.parse_update(good, '1.3.0'))
        self.assertIsNone(core.parse_update({**good, 'url': 'http://x'}, '1.0'))  # không https → bỏ
        self.assertIsNone(core.parse_update({**good, 'sha256': 'abc'}, '1.0'))    # thiếu mã kiểm tra → bỏ
        self.assertIsNone(core.parse_update(None, '1.0'))

    def test_nhieu_tieu_chi(self):
        # Cài đặt cũ → Tiêu chí 1
        old = core.criteria_from_config({'exchange': 'ALL', 'filters': FILTERS})
        self.assertEqual(old, [{'name': 'Tiêu chí 1', 'exchange': 'ALL', 'filters': FILTERS, 'alert': 'speak'}])
        # Kiểu báo: tiêu chí có riêng thì dùng riêng, không thì theo kiểu chung cũ
        mixed = core.criteria_from_config({'alert': 'off', 'criteria': [{'name': 'A', 'alert': 'beep'}, {'name': 'B'},
                                                                         {'name': 'C', 'alert': 'lung tung'}]})
        self.assertEqual([c['alert'] for c in mixed], ['beep', 'off', 'off'])
        # Đổi kiểu báo không tính là đổi lọc
        self.assertEqual(core.criterion_key(mixed[0]), core.criterion_key({**mixed[0], 'alert': 'speak'}))
        new = core.criteria_from_config({'criteria': [{'name': 'Đột biến KL', 'exchange': 'HSX', 'filters': {}},
                                                      {'name': '  ', 'filters': FILTERS}]})
        self.assertEqual([c['name'] for c in new], ['Đột biến KL', 'Tiêu chí 2'])
        self.assertEqual(new[1]['exchange'], 'HSX')
        # Đổi tên không đổi khoá
        self.assertEqual(core.criterion_key({**new[0], 'name': 'X'}), core.criterion_key(new[0]))
        self.assertNotEqual(core.criterion_key(new[0]), core.criterion_key(new[1]))

    def test_cau_doc_nhieu_tieu_chi(self):
        self.assertEqual(core.alert_text_groups([('A', ['VIB'])])[0], 'Mã mới: V I B.')
        # Nhiều tiêu chí mà chỉ 1 cái có mã mới → vẫn đọc tên tiêu chí
        self.assertEqual(core.alert_text_groups([('bùng nổ KL', ['HHP'])], names=True)[0], 'bùng nổ KL: H H P.')
        vi, _ = core.alert_text_groups([('Đột biến KL', ['HHP', 'VEA']), ('Vượt MA20', ['MBB']), ('Trống', [])])
        self.assertEqual(vi, 'Đột biến KL: H H P, V E A. Vượt MA20: M B B.')
        vi, _ = core.alert_text_groups([('A', list('ABCDE')), ('B', list('FGHI'))])
        self.assertEqual(vi, 'A: A, B, C, D, E. B: F. Và 3 mã khác.')

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

    def test_nhan_link_hoac_id_sheet(self):
        sid = 'AbCdEfGhIjKlMnOpQrStUvWxYz_0123456789-xy'
        self.assertEqual(core.sheet_id_from(f'https://docs.google.com/spreadsheets/d/{sid}/edit?gid=0#gid=0'), sid)
        self.assertEqual(core.sheet_id_from('  ' + sid + ' '), sid)
        self.assertEqual(core.sheet_id_from('khong phai link'), '')
        self.assertEqual(core.sheet_id_from(''), '')

    def test_phan_hoi_rong_hoac_sai_la_cookie_het_han(self):
        for bad in ([], {'Message': 'Authorization has been denied for this request.'}, None):
            with self.assertRaises(core.CookieExpired):
                core.parse_trading_stats(bad)


if __name__ == '__main__':
    unittest.main()
