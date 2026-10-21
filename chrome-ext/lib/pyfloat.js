// Phép tính số thực y hệt Python 3.12 — để số trong extension khớp từng chữ số với bản Python.
//   • sum() của Python 3.12 cộng số thực có bù sai số (Neumaier), không cộng thẳng như vòng for.
//   • round() làm tròn nửa về số chẵn trên đúng giá trị nhị phân; toFixed của JS làm tròn nửa lên.
// Dữ liệu nến VNDirect: giá luôn là số thực, khối lượng luôn là số nguyên (đã kiểm 10/2026).

// sum() trên danh sách số thực (Python 3.12+). Rỗng → 0.
export function fsum(a) {
  if (!a.length) return 0;
  let f = a[0], c = 0;
  for (let i = 1; i < a.length; i++) {
    const x = a[i], t = f + x;
    if (Math.abs(f) >= Math.abs(x)) c += (f - t) + x;
    else c += (x - t) + f;
    f = t;
  }
  if (c && Number.isFinite(c)) f += c;
  return f;
}

// sum() trên danh sách số nguyên: Python cộng chính xác; JS cũng chính xác khi tổng < 2^53 (khối lượng cỡ 1e10).
export function isum(a) {
  let s = 0;
  for (const x of a) s += x;
  return s;
}

export const fmean = (a) => fsum(a) / a.length;
export const imean = (a) => isum(a) / a.length;

// round(x) của Python: số nguyên gần nhất, đúng nửa thì về số chẵn.
export function pyRound(x) {
  const f = Math.floor(x), d = x - f;
  if (d > 0.5) return f + 1;
  if (d < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

// round(x, nd) của Python: như toFixed nhưng đúng nửa (trên giá trị nhị phân thật) thì về chữ số chẵn.
export function pyRoundTo(x, nd) {
  if (!Number.isFinite(x) || Math.abs(x) >= 1e21) return x;
  const exact = Math.abs(x).toFixed(100);
  const frac = exact.slice(exact.indexOf('.') + 1);
  if (frac[nd] === '5' && /^0*$/.test(frac.slice(nd + 1))) {
    // Đúng nửa: giữ phần cắt cụt nếu chữ số cuối chẵn, không thì làm tròn lên (toFixed làm tròn lên)
    const lastDigit = nd === 0 ? exact[exact.indexOf('.') - 1] : frac[nd - 1];
    if (Number(lastDigit) % 2 === 0) {
      const cut = exact.slice(0, exact.indexOf('.') + (nd ? nd + 1 : 0));
      return (x < 0 ? -1 : 1) * Number(cut);
    }
  }
  return Number(x.toFixed(nd));
}

// _fixed của core.py = Number.toFixed của JS (làm tròn nửa lên trên giá trị nhị phân thật)
export const fixed = (x, digits) => x.toFixed(digits);

// String(v) của JS = js_num của core.py (11.0 → '11', 13.5 → '13.5')
export const jsNum = (v) => String(Number(v));
