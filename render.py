#!/usr/bin/env python3
"""Preview images for the README (Pillow; dev-time, not part of the build).

    python3 render.py       # regenerate assets/sample.png + assets/diff.png

Reads the built fonts from dist/ and stock DejaVu from DEJAVU_DIR.
"""

import sys

from build import ASSETS, DIST, FACES, FAMILY, STYLES, dejavu_dir, face_filename

# codepoints that differ from stock DejaVu (the ~14 intentional edits)
CHANGED = [
    0x24, 0x25, 0x28, 0x29, 0x2A, 0x2D, 0x30, 0x5E,
    0x5F, 0x69, 0x6C, 0x7B, 0x7D, 0x7E, 0xA1, 0xBF,
]  # fmt: skip

SAMPLE = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
    "abcdefghijklmnopqrstuvwxyz\n"
    "0123456789 ~!@#$%^&?+*-=,;.:\n"
    "() [] {} \"\" '' \\/ <> -- __"
)

BG = (30, 30, 46)  # card background (reads on light + dark READMEs)
FG = (205, 214, 244)  # primary text
DIM = (127, 132, 156)  # labels
ACCENT = (243, 139, 168)  # DejaVu ghost in the diff overlay


def render():
    from PIL import Image, ImageDraw, ImageFont

    ASSETS.mkdir(exist_ok=True)
    if not (DIST / face_filename("Regular")).exists():
        sys.exit("no dist/ -- run `python3 build.py` first.")

    def face(style, size):
        return ImageFont.truetype(str(DIST / face_filename(style)), size)

    # --- sample.png: the four styles over the sample text ---
    sz, pad, lead, gap = 34, 44, 46, 34
    lines = SAMPLE.splitlines()
    label = ImageFont.truetype(str(DIST / face_filename("Bold")), 20)
    blocks = [
        (
            FAMILY if st == "Regular" else f"{FAMILY} {FACES[st].typographic}",
            face(st, sz),
        )
        for st in STYLES
    ]
    scratch = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    width = max(scratch.textlength(ln, font=f) for _, f in blocks for ln in lines)
    height = pad + len(blocks) * (28 + len(lines) * lead + gap)
    img = Image.new("RGB", (int(width) + 2 * pad, int(height)), BG)
    d = ImageDraw.Draw(img)
    y = pad
    for title, f in blocks:
        d.text((pad, y), title, font=label, fill=DIM, anchor="la")
        y += 28
        for ln in lines:
            d.text((pad, y), ln, font=f, fill=FG, anchor="la")
            y += lead
        y += gap
    img.save(ASSETS / "sample.png")
    print("  assets/sample.png")

    # --- diff.png: the 16 changed glyphs, DejaVu ghosted under Astacid ---
    gsz, cols = 128, 8
    cw, ch = 128, 172
    rows = (len(CHANGED) + cols - 1) // cols
    dv = ImageFont.truetype(str(dejavu_dir() / "DejaVuSansMono.ttf"), gsz)
    ast = face("Regular", gsz)
    img = Image.new("RGBA", (cols * cw, rows * ch + 40), BG + (255,))
    d = ImageDraw.Draw(img)
    d.text(
        (cw * cols // 2, 20),
        "changed glyphs -- DejaVu (pink) vs Astacid",
        font=label,
        fill=DIM,
        anchor="mm",
    )
    for i, cp in enumerate(CHANGED):
        cx = (i % cols) * cw + cw // 2
        base = 40 + (i // cols) * ch + int(ch * 0.62)
        ch_ = chr(cp)
        d.text((cx, base), ch_, font=dv, fill=ACCENT + (200,), anchor="ms")
        d.text((cx, base), ch_, font=ast, fill=FG + (255,), anchor="ms")
    img.convert("RGB").save(ASSETS / "diff.png")
    print("  assets/diff.png")


if __name__ == "__main__":
    render()
