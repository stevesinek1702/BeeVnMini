# Vẽ logo BeeMini (con ong làm từ 3 ô mật xếp chéo đi lên trong tổ ong). Chạy: python ve-logo.py → logoB.svg (logo.svg) + logoB16.svg (logo-small.svg).
# icon*.png chụp từ SVG bằng Chrome headless (nền trong suốt).
import math
def hexpts(cx, cy, r):
    return ' '.join(f'{cx + r*math.cos(math.radians(a)):.2f},{cy + r*math.sin(math.radians(a)):.2f}' for a in range(-90, 270, 60))
def logo(simple=False, bee='A'):
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">',
      '<!-- Logo BeeMini: tổ ong; 3 ô mật xếp chéo đi lên (giá tăng) thành con ong — ô trên cùng là đầu -->',
      '<defs>',
      '<linearGradient id="rim" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff1b8"/><stop offset=".35" stop-color="#fbbf24"/><stop offset="1" stop-color="#c2410c"/></linearGradient>',
      '<radialGradient id="body" cx=".5" cy=".38" r=".7"><stop offset="0" stop-color="#262650"/><stop offset="1" stop-color="#11112a"/></radialGradient>',
      '<linearGradient id="honey" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fffbe6"/><stop offset=".5" stop-color="#fcd34d"/><stop offset="1" stop-color="#f59e0b"/></linearGradient>',
      '<clipPath id="c2"><polygon points="CLIP2"/></clipPath><clipPath id="c3"><polygon points="CLIP3"/></clipPath>',
      '</defs>',
      f'<polygon points="{hexpts(64, 64, 57)}" fill="url(#body)" stroke="url(#rim)" stroke-width="10" stroke-linejoin="round"/>',
      f'<polygon points="{hexpts(64, 64, 49)}" fill="none" stroke="#fde68a" stroke-opacity=".18" stroke-width="2" stroke-linejoin="round"/>']
    if simple:
        honeyc = [(83, 47), (64, 64), (45, 81)]; dark = []; r = 14
    else:
        dx, dy = 23.5, 20.4
        honeyc = [(64 + dx/2, 64 - dy), (64, 64), (64 - dx/2, 64 + dy)]       # đầu → thân → đuôi
        dark = [(64 - dx/2, 64 - dy), (64 - dx, 64), (64 + dx, 64), (64 + dx/2, 64 + dy)]
        r = 12.2
    for cx, cy in dark:
        o.append(f'<polygon points="{hexpts(cx, cy, r)}" fill="#2b2b58" stroke="#45457e" stroke-width="1.4" stroke-linejoin="round"/>')
    (hx, hy), (bx, by), (tx, ty) = honeyc
    o[6] = o[6].replace('CLIP2', hexpts(bx, by, r)).replace('CLIP3', hexpts(tx, ty, r))
    if bee == 'B':     # râu vàng: 2 nét cong từ đỉnh ô đầu; cánh trong suốt trên ô thân
        sw = 2.2 if not simple else 3.4
        for sgn in (-1, 1):
            o.append(f'<path d="M{hx + sgn*3:.1f},{hy - r + 1.5:.1f} q{sgn*1.5:.1f},-6 {sgn*6.5:.1f},-8.5" fill="none" stroke="#fcd34d" stroke-width="{sw}" stroke-linecap="round"/>')
            o.append(f'<circle cx="{hx + sgn*9.5:.1f}" cy="{hy - r - 7:.1f}" r="{sw*1.1:.1f}" fill="#fde68a"/>')

    for i, (cx, cy) in enumerate(honeyc):
        o.append(f'<polygon points="{hexpts(cx, cy, r)}" fill="url(#honey)" stroke="#b45309" stroke-width="1.6" stroke-linejoin="round"/>')
        if bee == 'B' and i > 0 and not simple:      # sọc đen trên thân / đuôi
            o.append(f'<g clip-path="url(#c{i + 1})"><rect x="{cx - r}" y="{cy + r*0.05:.2f}" width="{2*r}" height="{r*0.22:.2f}" fill="#1c1c38" transform="rotate(30 {cx} {cy})"/></g>')
        if i > 0 or bee == 'B':
            o.append(f'<polygon points="{hexpts(cx - r*.18, cy - r*.28, r*.32)}" fill="#ffffff" fill-opacity=".55"/>' if i > 0 else '')
    if bee == 'B' and not simple:     # 2 cánh trong suốt trên lưng (phía trên-trái của thân)
        for ox, oy, ang, k in ((-5, -0.85, -30, 1), (-12.5, -0.3, -70, .85)):
            cx_, cy_ = bx + ox, by + r * oy
            o.append(f'<ellipse cx="{cx_:.1f}" cy="{cy_:.1f}" rx="{r*0.38*k:.1f}" ry="{r*0.72*k:.1f}" transform="rotate({ang} {cx_:.1f} {cy_:.1f})" fill="#e0f2fe" fill-opacity=".6" stroke="#ffffff" stroke-opacity=".9" stroke-width="1.1"/>')
    # mắt trên ô đầu
    er = r * (0.17 if not simple else 0.2)
    for sgn in (-1, 1):
        ex, ey = hx + sgn * r * 0.33, hy - r * 0.05
        o.append(f'<circle cx="{ex:.2f}" cy="{ey:.2f}" r="{er:.2f}" fill="#1c1c38"/>')
        o.append(f'<circle cx="{ex + er*.35:.2f}" cy="{ey - er*.35:.2f}" r="{er*.38:.2f}" fill="#ffffff"/>')
    o.append('</svg>')
    return '\n'.join(x for x in o if x)
for v in 'AB':
    open(f'logo{v}.svg', 'w', encoding='utf-8').write(logo(False, v))
    open(f'logo{v}16.svg', 'w', encoding='utf-8').write(logo(True, v))
row = lambda v: ''.join(f'<div style="background:{bg};padding:8px"><img src="{f}" width="{s}" height="{s}"></div>'
    for f, s, bg in [(f'logo{v}.svg',128,'#141428'),(f'logo{v}.svg',128,'#fff'),(f'logo{v}.svg',48,'#141428'),(f'logo{v}.svg',32,'#fff'),(f'logo{v}16.svg',16,'#fff'),(f'logo{v}16.svg',16,'#202124')])
html = '<html><body style="margin:0;background:#888;padding:12px;font:bold 20px Segoe UI;color:#fff">' + ''.join(
    f'<div style="display:flex;gap:12px;align-items:end;margin-bottom:12px"><span>{v}</span>{row(v)}</div>' for v in 'AB') + '</body></html>'
open('preview3.html', 'w').write(html)
