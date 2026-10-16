"""Renders LocumDoc's share image and icon set from the logo and the site's own fonts.

    python tools/make_brand_assets.py

Writes into locumdoc/static/img/: og-en.png (1200x630), favicon.ico (16/32/48),
favicon-32.png, apple-touch-icon.png (180), icon-192.png, icon-512.png, icon-maskable-512.png.
Needs Playwright with Chromium, and Pillow.
"""
import io
import os
import pathlib

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = ROOT / "locumdoc" / "static"
IMG = STATIC / "img"
FONTS = (STATIC / "fonts").as_uri()

MARK = """<svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
<rect x="1" y="4" width="30" height="27" rx="7" fill="#7a1631"/>
<rect x="8" y="1" width="3.5" height="7" rx="1.75" fill="#e4d4b7"/>
<rect x="20.5" y="1" width="3.5" height="7" rx="1.75" fill="#e4d4b7"/>
<path d="M13.5 10.5h5v5h5v5h-5v5h-5v-5h-5v-5h5z" fill="#fff"/></svg>"""

# The logo mark, recoloured for the maroon band: deep-maroon block, sand pins, white cross.
BAND_MARK = ('<svg class="mark" viewBox="0 0 32 32" aria-hidden="true">'
             '<rect x="1" y="4" width="30" height="27" rx="7" fill="#5b0f23"/>'
             '<rect x="8" y="1" width="3.5" height="7" rx="1.75" fill="#e4d4b7"/>'
             '<rect x="20.5" y="1" width="3.5" height="7" rx="1.75" fill="#e4d4b7"/>'
             '<path d="M13.5 10.5h5v5h5v5h-5v5h-5v-5h-5v-5h5z" fill="#fff"/></svg>')

FONT_CSS = f"""
@font-face {{ font-family: Adventor; src: url({FONTS}/adventor-700.woff); font-weight: 700; }}
@font-face {{ font-family: Inter; src: url({FONTS}/inter-500.woff); font-weight: 500; }}
@font-face {{ font-family: Inter; src: url({FONTS}/inter-600.woff); font-weight: 600; }}
"""

COPY = {
    "en": dict(dir="ltr", head="Locum jobs for doctors in Qatar and the Gulf",
               sub="Every specialty. Verified facilities. Free for doctors.",
               tag="Now placing doctors in Qatar", font="Adventor", body="Inter"),
}


def og_html(lang):
    c = COPY[lang]
    return f"""<!doctype html><html dir="{c['dir']}"><head><meta charset="utf-8"><style>{FONT_CSS}
* {{ margin: 0; box-sizing: border-box; }}
body {{ width: 1200px; height: 630px; background: #f3f5f6; font-family: {c['body']}; color: #15202b; display: flex; overflow: hidden; }}
.copy {{ flex: 1; padding: 64px 56px 56px 72px; display: flex; flex-direction: column; }}
[dir=rtl] .copy {{ padding: 64px 72px 56px 56px; }}
.brand {{ display: flex; align-items: center; gap: 16px; font-family: Adventor; font-weight: 700; font-size: 40px; letter-spacing: -0.5px; direction: ltr; }}
[dir=rtl] .brand {{ align-self: flex-start; }}
.brand svg {{ width: 56px; height: 56px; }}
.brand b {{ color: #7a1631; }}
.tag {{ margin-top: 54px; display: inline-flex; align-self: flex-start; gap: 10px; align-items: center; font-weight: 600; font-size: 22px; color: #7a1631; background: #f6e9ed; padding: 10px 18px; border-radius: 999px; }}
h1 {{ margin-top: 22px; font-family: {c['font']}; font-weight: 700; font-size: {66 if lang == 'en' else 64}px; line-height: 1.08; letter-spacing: {'-1.5px' if lang == 'en' else '0'}; max-width: 700px; }}
p {{ margin-top: 22px; font-size: 26px; line-height: 1.4; color: #4b5764; font-weight: 500; max-width: 720px; }}
.url {{ margin-top: auto; font-family: Inter; font-weight: 600; font-size: 24px; color: #7a1631; direction: ltr; align-self: flex-start; }}
.band {{ width: 330px; background: #7a1631; position: relative; display: flex; align-items: center; justify-content: center; }}
.band .mark {{ width: 176px; height: 176px; }}
</style></head><body>
<div class="copy">
  <div class="brand">{MARK.replace('<svg ', '<svg aria-hidden="true" ')}<span>locum<b>doc</b></span></div>
  <div class="tag">{c['tag']}</div>
  <h1>{c['head']}</h1>
  <p>{c['sub']}</p>
  <div class="url">locumdoc.me</div>
</div>
<div class="band">{BAND_MARK}</div>
</body></html>"""


def icon_html(size, pad=0.0, bg="transparent"):
    inner = size * (1 - 2 * pad)
    return f"""<!doctype html><html><body style="margin:0;width:{size}px;height:{size}px;background:{bg};display:flex;align-items:center;justify-content:center">
<div style="width:{inner}px;height:{inner}px">{MARK.replace('<svg ', '<svg width="100%" height="100%" ')}</div></body></html>"""


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()

        tmp = STATIC / "_render.html"  # loaded from disk so the file:// fonts are allowed

        def shot(html, w, h, path=None, transparent=False):
            pg = b.new_page(viewport={"width": w, "height": h})
            tmp.write_text(html, encoding="utf8")
            pg.goto(tmp.as_uri(), wait_until="networkidle")
            pg.evaluate("document.fonts.ready.then(() => document.fonts.size)")
            data = pg.screenshot(omit_background=transparent, type="png")
            pg.close()
            if path:
                pathlib.Path(path).write_bytes(data)
            return data

        shot(og_html("en"), 1200, 630, IMG / "og-en.png")
        shot(icon_html(180, 0.12, "#ffffff"), 180, 180, IMG / "apple-touch-icon.png")
        shot(icon_html(192, 0.04), 192, 192, IMG / "icon-192.png", transparent=True)
        shot(icon_html(512, 0.04), 512, 512, IMG / "icon-512.png", transparent=True)
        shot(icon_html(512, 0.2, "#ffffff"), 512, 512, IMG / "icon-maskable-512.png")
        big = Image.open(io.BytesIO(shot(icon_html(256, 0.0), 256, 256, transparent=True))).convert("RGBA")
        big.resize((32, 32), Image.LANCZOS).save(IMG / "favicon-32.png")
        big.save(IMG / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
        b.close()
        tmp.unlink()
    for f in sorted(os.listdir(IMG)):
        print(f, os.path.getsize(IMG / f))


if __name__ == "__main__":
    main()
