# -*- coding: utf-8 -*-
"""Dựng video báo cáo chiến dịch Cốc Cốc (Mộc Việt Home) có giọng đọc + vietsub."""
import asyncio, csv, os, subprocess, wave, functools, shutil, glob
from PIL import Image, ImageDraw, ImageFont
import edge_tts

WORK = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(WORK, "_tts"); os.makedirs(TMP, exist_ok=True)

def find_ffmpeg():
    if os.environ.get("FFMPEG"): return os.environ["FFMPEG"]
    if shutil.which("ffmpeg"): return shutil.which("ffmpeg")
    hits = glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages",
                                  "Gyan.FFmpeg*", "*", "bin", "ffmpeg.exe"))
    if hits: return hits[0]
    raise SystemExit("Không tìm thấy ffmpeg. Cài bằng: winget install Gyan.FFmpeg")
FF = find_ffmpeg()
VOICE, RATE = "vi-VN-HoaiMyNeural", "-4%"
W, H, FPS = 1920, 1080, 30
OUT_MP4 = os.path.join(WORK, "mocviet_coccoc_video.mp4")
OUT_SRT = os.path.join(WORK, "mocviet_coccoc_video.srt")

# ---------------- colours & fonts ----------------
def hx(s): s = s.lstrip("#"); return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))
PAGE, SURF, SURF2 = hx("f6f7f4"), hx("ffffff"), hx("eeefea")
INK, INK2, MUTED = hx("0b0b0b"), hx("52514e"), hx("898781")
GRID, AXIS, BORDER = hx("e6e5df"), hx("c3c2b7"), hx("e3e2dc")
BRAND, BRAND_D, BROWN = hx("14833b"), hx("0f6a2f"), hx("6b4423")
UP, DOWN = hx("006300"), hx("b42318")
SERIES = [hx("2a78d6"), hx("eb6834"), hx("1baf7a"), hx("eda100")]

def mix(c, d, t): return tuple(round(a + (b - a) * t) for a, b in zip(c, d))

@functools.lru_cache(None)
def F(size, w="r"):
    path = {"r": "segoeui.ttf", "b": "segoeuib.ttf", "s": "seguisb.ttf"}[w]
    return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", path), size)

def ease(t): t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3

# ---------------- data ----------------
rows = []
with open(os.path.join(WORK, "mocviet_coccoc_campaign.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        for k in list(r):
            if k not in ("thang", "dinh_dang"): r[k] = int(r[k])
        rows.append(r)
MONTHS = sorted({r["thang"] for r in rows})
FMTS = list(dict.fromkeys(r["dinh_dang"] for r in rows))
def S(key, month=None, fmt=None):
    return sum(r[key] for r in rows if (month is None or r["thang"] == month) and (fmt is None or r["dinh_dang"] == fmt))
def mlabel(m): y, mm = m.split("-"); return f"T{int(mm)}"

def vn_int(n): return f"{int(round(n)):,}".replace(",", ".")
def vn_dec(x, d): return f"{x:.{d}f}".replace(".", ",")
def trim(x): s = f"{x:.2f}".rstrip("0").rstrip("."); return s.replace(".", ",")
def money(v):
    if v >= 1e9: return vn_dec(v / 1e9, 2) + " tỷ"
    if v >= 1e6: return vn_dec(v / 1e6, 1) + " tr"
    return vn_int(v) + " đ"
def compact(v):
    if v >= 1e9: return trim(v / 1e9) + " tỷ"
    if v >= 1e6: return trim(v / 1e6) + " tr"
    if v >= 1e3: return trim(v / 1e3) + "k"
    return vn_int(v)
def nice_max(v):
    import math
    p = 10 ** math.floor(math.log10(v)); n = v / p
    return (1 if n <= 1 else 2 if n <= 2 else 2.5 if n <= 2.5 else 5 if n <= 5 else 10) * p

# ---------------- drawing helpers ----------------
def text(d, xy, s, font, fill, anchor="la"): d.text(xy, s, font=font, fill=fill, anchor=anchor)

def wrap(d, s, font, maxw):
    lines, cur = [], ""
    for w_ in s.split():
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

def logo(d, x, y, s=1.0, dark=False):
    d.rounded_rectangle((x, y, x + 52 * s, y + 52 * s), radius=14 * s, fill=SURF)
    cx, cy, r = x + 24 * s, y + 24 * s, 12 * s
    d.ellipse((cx - r + 8 * s, cy - r + 8 * s, cx + r + 8 * s, cy + r + 8 * s), fill=BROWN)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BRAND)
    d.ellipse((cx - r + 8 * s, cy - r + 8 * s, cx + r + 8 * s, cy + r + 8 * s), outline=None)

def card(d, box, fill=SURF, r=26): d.rounded_rectangle(box, radius=r, fill=fill, outline=BORDER, width=2)

def chrome(title, kicker):
    img = Image.new("RGBA", (W, H), PAGE + (255,))
    d = ImageDraw.Draw(img)
    logo(d, 80, 44, 0.85)
    text(d, (138, 66), "Cốc Cốc Ads", F(30, "b"), INK, "lm")
    text(d, (W - 80, 66), "Mộc Việt Home  ·  Tổ ấm mùa thu  ·  T5–T10/2026", F(26), INK2, "rm")
    d.line((80, 112, W - 80, 112), fill=BORDER, width=2)
    text(d, (80, 150), kicker.upper(), F(24, "s"), BRAND, "la")
    text(d, (80, 182), title, F(56, "b"), INK, "la")
    return img, d

@functools.lru_cache(None)
def gradient():
    g = Image.new("RGB", (2, 2))
    g.putdata([BRAND, BRAND_D, hx("0c5a27"), hx("5a3a1e")])
    g = g.resize((W, H), Image.BILINEAR).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    od.ellipse((1380, -260, 2100, 460), fill=(255, 255, 255, 22))
    od.ellipse((1560, 520, 2160, 1120), fill=(255, 255, 255, 14))
    od.ellipse((-200, 760, 260, 1220), fill=(255, 255, 255, 12))
    return Image.alpha_composite(g, ov)

def chip(d, x, y, s, font):
    w = d.textlength(s, font=font) + 44
    d.rounded_rectangle((x, y, x + w, y + 54), radius=27, fill=(255, 255, 255, 40), outline=(255, 255, 255, 90), width=2)
    text(d, (x + 22, y + 27), s, font, (255, 255, 255), "lm")
    return x + w + 16

def triangle(d, x, y, up, color, s=11):
    pts = [(x, y + s * .5), (x + s * 1.2, y + s * .5), (x + s * .6, y - s * .6)] if up else \
          [(x, y - s * .5), (x + s * 1.2, y - s * .5), (x + s * .6, y + s * .6)]
    d.polygon(pts, fill=color)

# ---------------- scenes ----------------
def scene_title(p, k):
    img = gradient().convert("RGB"); d = ImageDraw.Draw(img, "RGBA")
    off = 60 * (1 - p); a = int(255 * p)
    logo(d, 120, 110, 1.2)
    text(d, (196, 142), "Cốc Cốc Ads", F(40, "b"), (255, 255, 255), "lm")
    text(d, (120, 330 + off), "BÁO CÁO HIỆU QUẢ CHIẾN DỊCH", F(34, "s"), (255, 255, 255, int(a * .85)))
    text(d, (120, 390 + off), "Mộc Việt Home", F(124, "b"), (255, 255, 255, a))
    text(d, (120, 560 + off), "Chiến dịch “Tổ ấm mùa thu”", F(60, "s"), (255, 255, 255, int(a * .92)))
    x = 120
    for s in ("Kỳ báo cáo: T5 – T10/2026", "4 định dạng quảng cáo", f"{vn_int(S('hien_thi'))} lượt hiển thị"):
        x = chip(d, x, 690 + off * 1.4, s, F(28))
    return img.convert("RGBA")

def scene_close(p, k):
    img = gradient().convert("RGB"); d = ImageDraw.Draw(img, "RGBA")
    a = int(255 * p); off = 40 * (1 - p)
    logo(d, W / 2 - 62, 250 + off, 2.4)
    text(d, (W / 2, 520 + off), "Cảm ơn quý khách!", F(110, "b"), (255, 255, 255, a), "mm")
    text(d, (W / 2, 640 + off), "Cốc Cốc Ads  ·  Đồng hành cùng thương hiệu Việt", F(40), (255, 255, 255, int(a * .9)), "mm")
    return img.convert("RGBA")

def kpi_data():
    last, prev = MONTHS[-1], MONTHS[-2]
    L = lambda k: S(k, last); P = lambda k: S(k, prev)
    cost, rev, conv, clk, imp = S("chi_phi_vnd"), S("doanh_thu_vnd"), S("chuyen_doi"), S("luot_click"), S("hien_thi")
    return [
        ("Tổng chi phí", cost, money, L("chi_phi_vnd") / P("chi_phi_vnd") - 1, True),
        ("Doanh thu ghi nhận", rev, money, L("doanh_thu_vnd") / P("doanh_thu_vnd") - 1, True),
        ("ROAS", rev / cost, lambda v: vn_dec(v, 1) + "x", (L("doanh_thu_vnd") / L("chi_phi_vnd")) / (P("doanh_thu_vnd") / P("chi_phi_vnd")) - 1, True),
        ("Chuyển đổi", conv, vn_int, L("chuyen_doi") / P("chuyen_doi") - 1, True),
        ("CPA trung bình", cost / conv, lambda v: vn_int(v) + " đ", (L("chi_phi_vnd") / L("chuyen_doi")) / (P("chi_phi_vnd") / P("chuyen_doi")) - 1, False),
        ("CTR trung bình", clk / imp, lambda v: vn_dec(v * 100, 2) + "%", (L("luot_click") / L("hien_thi")) / (P("luot_click") / P("hien_thi")) - 1, True),
    ]

def scene_kpi(p, k):
    img, d = chrome("Tổng quan kết quả", "Toàn kỳ T5 – T10/2026")
    gx, gy, gw, gh, gap = 80, 260, (W - 160 - 2 * 32) / 3, 270, 32
    hl = {0: {0, 3}, 1: {1, 3}, 2: {2}}.get(k, set())  # tile nhấn mạnh theo lời đọc
    hl = {0: set(), 1: {0, 1, 3}, 2: {2}}.get(k, set())
    for i, (lab, val, fmt, dl, up_good) in enumerate(kpi_data()):
        c, r = i % 3, i // 3
        x0 = gx + c * (gw + gap); y0 = gy + r * (gh + gap)
        card(d, (x0, y0, x0 + gw, y0 + gh), fill=hx("e9f5ec") if i in hl else SURF)
        if i in hl: d.rounded_rectangle((x0, y0, x0 + 10, y0 + gh), radius=5, fill=BRAND)
        text(d, (x0 + 44, y0 + 48), lab, F(32), INK2)
        text(d, (x0 + 44, y0 + 100), fmt(val * p), F(84, "b"), INK)
        good = (dl >= 0) == up_good
        col = UP if good else DOWN
        triangle(d, x0 + 46, y0 + 222, dl >= 0, col)
        s1 = vn_dec(abs(dl) * 100, 1) + "%"
        text(d, (x0 + 70, y0 + 222), s1, F(28, "b"), col, "lm")
        text(d, (x0 + 78 + d.textlength(s1, font=F(28, "b")), y0 + 222), "so với T9/2026", F(28), MUTED, "lm")
    return img

def stacked(d, box, key, p):
    x0, y0, x1, y1 = box
    # legend
    lx = x0
    for i, f_ in enumerate(FMTS):
        d.rounded_rectangle((lx, y0 + 4, lx + 26, y0 + 30), radius=6, fill=SERIES[i])
        text(d, (lx + 38, y0 + 17), f_, F(28), INK2, "lm")
        lx += 38 + d.textlength(f_, font=F(28)) + 48
    pt, pb, pl = y0 + 90, y1 - 50, x0 + 130
    ih = pb - pt
    totals = [S(key, m) for m in MONTHS]
    mx = nice_max(max(totals) * 1.08)
    for i in range(5):
        y = pb - ih * i / 4
        d.line((pl, y, x1, y), fill=AXIS if i == 0 else GRID, width=2)
        text(d, (pl - 18, y), "0" if i == 0 else compact(mx * i / 4), F(26), MUTED, "rm")
    band = (x1 - pl) / len(MONTHS); bw = min(130, band * 0.55)
    for mi, m in enumerate(MONTHS):
        g = ease(p * 1.5 - mi * 0.09)
        cx = pl + band * mi + band / 2; bx = cx - bw / 2; yc = pb
        n = len(FMTS)
        for fi, f_ in enumerate(FMTS):
            h = S(key, m, f_) / mx * ih * g
            if h < 1: continue
            top = yc - h; bot = yc - (3 if fi > 0 else 0)
            if bot - top < 2: yc = top; continue
            if fi == n - 1: d.rounded_rectangle((bx, top, bx + bw, bot), radius=10, fill=SERIES[fi], corners=(True, True, False, False))
            else: d.rectangle((bx, top, bx + bw, bot), fill=SERIES[fi])
            yc = top
        if g > 0.95: text(d, (cx, yc - 14), money(totals[mi]), F(30, "b"), INK2, "ms")
        text(d, (cx, pb + 38), mlabel(m), F(30), INK2, "ms")

def scene_cost(p, k):
    img, d = chrome("Chi phí theo tháng", "Phân bổ ngân sách theo định dạng")
    card(d, (80, 260, W - 80, 840))
    stacked(d, (130, 295, W - 130, 830), "chi_phi_vnd", p)
    return img

def scene_rev(p, k):
    img, d = chrome("Doanh thu theo tháng", "Doanh thu ghi nhận theo định dạng")
    card(d, (80, 260, W - 80, 840))
    stacked(d, (130, 295, W - 130, 830), "doanh_thu_vnd", p)
    return img

def hbars(d, box, title, sub, vals, fmt, p, hl):
    x0, y0, x1, y1 = box
    card(d, box)
    text(d, (x0 + 44, y0 + 40), title, F(40, "b"), INK)
    text(d, (x0 + 44, y0 + 96), sub, F(26), INK2)
    mx = max(vals); iw = x1 - x0 - 88 - 190
    for i, (f_, v) in enumerate(zip(FMTS, vals)):
        y = y0 + 170 + i * 105
        dim = hl and i not in hl
        col = mix(SERIES[i], SURF, 0.7) if dim else SERIES[i]
        text(d, (x0 + 44, y), f_, F(28, "s"), mix(INK2, SURF, .55) if dim else INK2)
        d.rounded_rectangle((x0 + 44, y + 42, x0 + 44 + iw, y + 72), radius=8, fill=SURF2)
        w = max(16, v / mx * iw * ease(p * 1.4 - i * 0.1))
        d.rounded_rectangle((x0 + 44, y + 42, x0 + 44 + w, y + 72), radius=8, fill=col)
        text(d, (x0 + 44 + iw + 22, y + 57), fmt(v), F(32, "b"), mix(INK, SURF, .55) if dim else INK, "lm")

def scene_eff(p, k):
    img, d = chrome("Hiệu quả theo định dạng", "So sánh toàn kỳ")
    roas = [S("doanh_thu_vnd", fmt=f_) / S("chi_phi_vnd", fmt=f_) for f_ in FMTS]
    cpa = [S("chi_phi_vnd", fmt=f_) / S("chuyen_doi", fmt=f_) for f_ in FMTS]
    hl = {0: {0}, 1: {1, 2}}.get(k)
    mid = W / 2
    hbars(d, (80, 260, mid - 16, 840), "ROAS", "Doanh thu / chi phí · càng cao càng tốt", roas, lambda v: vn_dec(v, 1) + "x", p, hl)
    hbars(d, (mid + 16, 260, W - 80, 840), "CPA", "Chi phí mỗi chuyển đổi · càng thấp càng tốt", cpa, lambda v: vn_int(v) + " đ", p, hl)
    return img

RECS = [
    ("01", "Tăng ngân sách Search Ads", "Tăng 20–30% ngân sách cho mùa mua sắm cuối năm – kênh có ROAS cao nhất (23,5x)."),
    ("02", "Mở rộng Native Ads", "Làm mới bộ hình ảnh và nội dung; ROAS gần 20x, còn dư địa tăng trưởng."),
    ("03", "Giữ độ phủ thương hiệu", "Duy trì Banner Display và New Tab Ads để thương hiệu luôn hiện diện."),
]
def scene_rec(p, k):
    img, d = chrome("Đề xuất cho quý tới", "Kế hoạch tối ưu Q1/2027")
    cw = (W - 160 - 2 * 32) / 3
    for i, (num, ttl, body) in enumerate(RECS):
        x0 = 80 + i * (cw + 32); y0, y1 = 260, 840
        on = k >= i + 1
        a = 1.0 if on else 0.0
        card(d, (x0, y0, x0 + cw, y1), fill=SURF if on else hx("f1f2ee"))
        if on: d.rounded_rectangle((x0, y0, x0 + cw, y0 + 12), radius=6, fill=BRAND)
        c_num = BRAND if on else mix(BRAND, PAGE, .75)
        c_t = INK if on else mix(INK, PAGE, .75)
        c_b = INK2 if on else mix(INK2, PAGE, .75)
        text(d, (x0 + 48, y0 + 60), num, F(96, "b"), c_num)
        yy = y0 + 210
        for ln in wrap(d, ttl, F(44, "b"), cw - 96):
            text(d, (x0 + 48, yy), ln, F(44, "b"), c_t); yy += 58
        yy += 20
        for ln in wrap(d, body, F(32), cw - 96):
            text(d, (x0 + 48, yy), ln, F(32), c_b); yy += 46
    return img

# (phụ đề, lời đọc) — lời đọc viết số bằng chữ để giọng đọc tự nhiên
SCENES = [
    (scene_title, [
        ("Kính chào quý khách hàng Mộc Việt Home.", None),
        ("Đây là báo cáo hiệu quả chiến dịch “Tổ ấm mùa thu” trên Cốc Cốc, từ tháng 5 đến tháng 10 năm 2026.",
         "Đây là báo cáo hiệu quả chiến dịch Tổ ấm mùa thu trên Cốc Cốc, từ tháng năm đến tháng mười, năm hai nghìn không trăm hai mươi sáu."),
    ]),
    (scene_kpi, [
        ("Sau sáu tháng, chiến dịch đạt hơn 52 triệu lượt hiển thị và hơn 435 nghìn lượt click.",
         "Sau sáu tháng, chiến dịch đạt hơn năm mươi hai triệu lượt hiển thị, và hơn bốn trăm ba mươi lăm nghìn lượt click."),
        ("Với chi phí khoảng 1 tỷ đồng, chiến dịch mang về 12.924 chuyển đổi và 19,07 tỷ đồng doanh thu.",
         "Với chi phí khoảng một tỷ đồng, chiến dịch mang về mười hai nghìn chín trăm hai mươi bốn chuyển đổi, và mười chín phẩy không bảy tỷ đồng doanh thu."),
        ("Chỉ số ROAS đạt 19 lần: mỗi đồng quảng cáo mang về 19 đồng doanh thu.",
         "Chỉ số rô át đạt mười chín lần, nghĩa là mỗi đồng quảng cáo mang về mười chín đồng doanh thu."),
    ]),
    (scene_cost, [
        ("Ngân sách được tăng dần qua từng tháng, từ 130,5 triệu trong tháng 5 lên hơn 208 triệu trong tháng 10.",
         "Ngân sách được tăng dần qua từng tháng, từ một trăm ba mươi triệu rưỡi trong tháng năm, lên hơn hai trăm lẻ tám triệu trong tháng mười."),
        ("Search Ads chiếm khoảng một nửa ngân sách, phần còn lại chia đều cho Native, Banner và New Tab Ads.", None),
    ]),
    (scene_rev, [
        ("Doanh thu tăng trưởng đều qua từng tháng.", None),
        ("Tháng 10 đạt 4,27 tỷ đồng, tăng 87% so với tháng 5.",
         "Riêng tháng mười đạt bốn phẩy hai mươi bảy tỷ đồng, tăng tám mươi bảy phần trăm so với tháng năm."),
    ]),
    (scene_eff, [
        ("Search Ads hiệu quả nhất, với ROAS 23,5 lần và chi phí khoảng 64 nghìn đồng mỗi chuyển đổi.",
         "Search Ads hiệu quả nhất, với rô át hai mươi ba phẩy năm lần, và chi phí khoảng sáu mươi tư nghìn đồng mỗi chuyển đổi."),
        ("Native Ads theo sát với ROAS gần 20 lần, còn Banner Display phù hợp hơn cho mục tiêu nhận diện thương hiệu.",
         "Native Ads theo sát với rô át gần hai mươi lần, còn Banner Display phù hợp hơn cho mục tiêu nhận diện thương hiệu."),
    ]),
    (scene_rec, [
        ("Cốc Cốc đề xuất ba hướng tối ưu cho quý tới.", None),
        ("Thứ nhất, tăng 20–30% ngân sách cho Search Ads trong mùa mua sắm cuối năm.",
         "Thứ nhất, tăng từ hai mươi đến ba mươi phần trăm ngân sách cho Search Ads trong mùa mua sắm cuối năm."),
        ("Thứ hai, mở rộng Native Ads với bộ hình ảnh và nội dung mới.", None),
        ("Thứ ba, duy trì Banner Display và New Tab Ads để giữ độ phủ thương hiệu.", None),
    ]),
    (scene_close, [
        ("Cảm ơn quý khách đã đồng hành cùng Cốc Cốc.", None),
        ("Hẹn gặp lại trong báo cáo tiếp theo!", None),
    ]),
]

# ---------------- TTS ----------------
async def tts_all(items):
    sem = asyncio.Semaphore(1)
    async def one(i, s):
        mp3 = os.path.join(TMP, f"l{i:02d}.mp3")
        key = mp3[:-4] + ".txt"
        if os.path.exists(mp3) and os.path.getsize(mp3) > 1000 and os.path.exists(key) \
                and open(key, encoding="utf-8").read() == s + RATE:
            return mp3  # đã có từ lần chạy trước
        async with sem:
            for attempt in range(25):
                try:
                    await edge_tts.Communicate(s, VOICE, rate=RATE).save(mp3)
                    open(key, "w", encoding="utf-8").write(s + RATE); break
                except Exception as e:
                    print("retry", i, type(e).__name__, flush=True)
                    if attempt == 24: raise
                    await asyncio.sleep(4)
            await asyncio.sleep(1.5)
        return mp3
    return await asyncio.gather(*(one(i, s) for i, s in enumerate(items)))

lines = [(sub, speech or sub) for _, ls in SCENES for sub, speech in ls]
mp3s = asyncio.run(tts_all([sp for _, sp in lines]))
SR = 24000
pcm = []
for m in mp3s:
    wv = m[:-4] + ".wav"
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", m, "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", wv], check=True)
    with wave.open(wv) as w_: pcm.append(w_.readframes(w_.getnframes()))
durs = [len(b) / 2 / SR for b in pcm]

# ---------------- timeline ----------------
LEAD, GAP, TAIL = 0.7, 0.45, 0.9
timeline = []  # (scene_fn, scene_start, scene_dur, [(start,end,sub)])
t, li = 0.0, 0
audio = bytearray()
def silence(sec): return b"\x00\x00" * int(round(sec * SR))
for fn, ls in SCENES:
    st = t; cur = LEAD; subs = []
    audio += silence(LEAD)
    for j in range(len(ls)):
        if j: audio += silence(GAP); cur += GAP
        subs.append((cur, cur + durs[li], lines[li][0]))
        audio += pcm[li]; cur += durs[li]; li += 1
    audio += silence(TAIL); cur += TAIL
    nfr = int(round(cur * FPS)); cur = nfr / FPS
    # khớp độ dài audio với số frame
    want = int(round((st + cur) * SR)) * 2
    if len(audio) < want: audio += b"\x00" * (want - len(audio))
    else: del audio[want:]
    timeline.append((fn, st, cur, subs)); t = st + cur
TOTAL = t
wav_path = os.path.join(TMP, "voice.wav")
with wave.open(wav_path, "wb") as w_:
    w_.setnchannels(1); w_.setsampwidth(2); w_.setframerate(SR); w_.writeframes(bytes(audio))

def ts(x):
    ms = int(round(x * 1000)); h_, ms = divmod(ms, 3600000); m_, ms = divmod(ms, 60000); s_, ms = divmod(ms, 1000)
    return f"{h_:02d}:{m_:02d}:{s_:02d},{ms:03d}"
with open(OUT_SRT, "w", encoding="utf-8") as f:
    n = 1
    for _, st, _, subs in timeline:
        for a, b, s in subs:
            f.write(f"{n}\n{ts(st + a)} --> {ts(st + b + 0.2)}\n{s}\n\n"); n += 1

# ---------------- subtitles overlay ----------------
@functools.lru_cache(None)
def sub_layer(s):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    font = F(42, "s"); ls = wrap(d, s, font, 1500)
    lh = 58; bh = lh * len(ls) + 34; bw = max(d.textlength(l, font=font) for l in ls) + 72
    y0 = H - 40 - bh
    d.rounded_rectangle(((W - bw) / 2, y0, (W + bw) / 2, y0 + bh), radius=18, fill=(10, 12, 10, 200))
    for i, l in enumerate(ls):
        text(d, (W / 2, y0 + 17 + lh * i + lh / 2), l, font, (255, 255, 255), "mm")
    return lay

# ---------------- render ----------------
ANIM = 1.3
enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-i", wav_path, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT_MP4], stdin=subprocess.PIPE)
prev_last = None; gframe = 0; XF = 12
for si, (fn, st, dur, subs) in enumerate(timeline):
    cache = {}; nfr = int(round(dur * FPS)); last = None
    for fi in range(nfr):
        tt = fi / FPS
        p = 1.0 if tt >= ANIM else ease(tt / ANIM)
        k = max([j for j, (a, _, _) in enumerate(subs) if tt >= a - 0.15] or [-1])
        sub = next((s for a, b, s in subs if a - 0.05 <= tt <= b + 0.25), None)
        key = (fi if tt < ANIM else -1, k, sub)
        if key not in cache:
            base = fn(p, k)
            if sub: base = Image.alpha_composite(base, sub_layer(sub))
            cache[key] = base.convert("RGB")
        fr = cache[key]
        if prev_last is not None and fi < XF:
            fr = Image.blend(prev_last, fr, (fi + 1) / XF)
        else:
            fr = fr.copy()
        d = ImageDraw.Draw(fr)
        d.rectangle((0, H - 8, W * (gframe + 1) / (TOTAL * FPS), H), fill=BRAND)
        enc.stdin.write(fr.tobytes()); gframe += 1; last = cache[key]
    prev_last = last
    print(f"scene {si + 1}/{len(timeline)} done ({dur:.1f}s)", flush=True)
enc.stdin.close(); enc.wait()
print("TOTAL", round(TOTAL, 1), "s - done")
