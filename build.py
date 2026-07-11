#!/usr/bin/env python3
"""Astacid Mono build pipeline — one script, three stages, pure python3.

    python3 build.py            # build all four faces into dist/
    python3 build.py render     # regenerate docs/ preview images (needs Pillow)

The font build patches 16 hand-edited override glyphs onto pristine DejaVu Sans
Mono 2.37 faces, adds the Nerd Font glyph set, and writes an authoritative name
table. It is bit-for-bit reproducible given a fixed base and SOURCE_DATE_EPOCH.

Stages: (1) merge the UFO override outlines onto the base faces with fonttools;
(2) add Nerd Font glyphs via the external `nerd-font-patcher`; (3) rewrite the
name/OS-2/head tables with fonttools. FontForge is never imported — the glyph
sources are UFO, which fonttools reads directly. Engine imports are lazy so a
plain `render` run only needs Pillow.

Environment:
    DEJAVU_DIR         dir holding the 4 pristine DejaVu Sans Mono 2.37 TTFs
    SOURCE_DATE_EPOCH  deterministic timestamp (default 1980-01-01)
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# ── identity ────────────────────────────────────────────────────────────────
FAMILY = "Astacid Mono"
VENDOR = "AVNX"
VERSION = "2.000"
REVISION = 2.0
CELL = 1233                       # monospace advance width at 2048 UPM
MAC_EPOCH_OFFSET = 2082844800     # 1970-01-01 -> 1904-01-01

COPYRIGHT = ("Astacid Mono (c) 2022-2026 avionix. A derivative of DejaVu Sans "
             "Mono. DejaVu (c) the DejaVu fonts team; Bitstream Vera Fonts "
             "(c) 2003 Bitstream, Inc. Bitstream Vera is a trademark of "
             "Bitstream, Inc.")
LICENSE = ("Astacid changes are released under the same terms as DejaVu: the "
           "Bitstream Vera license plus public-domain additions. Use, "
           "modification, and redistribution are permitted; the Bitstream Vera "
           "and DejaVu names may not be used to promote derivatives without "
           "permission.")
LICENSE_URL = "https://dejavu-fonts.github.io/License.html"

# style -> (base TTF, override UFO, RIBBI subfamily, typographic subfamily, bold, italic)
FACES = {
    "Regular":     ("DejaVuSansMono.ttf",             "overrides.ufo",             "Regular",     "Regular",      False, False),
    "Bold":        ("DejaVuSansMono-Bold.ttf",        "overrides-bold.ufo",        "Bold",        "Bold",         True,  False),
    "Oblique":     ("DejaVuSansMono-Oblique.ttf",     "overrides-oblique.ufo",     "Italic",      "Oblique",      False, True),
    "BoldOblique": ("DejaVuSansMono-BoldOblique.ttf", "overrides-boldoblique.ufo", "Bold Italic", "Bold Oblique", True,  True),
}
STYLES = list(FACES)

# codepoints that differ from stock DejaVu (used only by `render`)
CHANGED = [0x24, 0x25, 0x28, 0x29, 0x2A, 0x2D, 0x30, 0x5E,
           0x5F, 0x69, 0x6C, 0x7B, 0x7D, 0x7E, 0xA1, 0xBF]


# ── stage 1: merge overrides onto base (fonttools + ufoLib2) ─────────────────
def merge(rawdir):
    """Transplant each UFO override glyph's outline onto its base face.

    Pure fonttools: read the quadratic contours from the .ufo, replay them onto
    a TTGlyphPen, and drop the resulting glyf + hmtx onto the base glyph reached
    via the base cmap (matched by codepoint, not glyph name). Overrides are
    composite-free and already quadratic, so the transplant is a clean swap.
    """
    from fontTools.ttLib import TTFont
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from ufoLib2 import Font as UFO
    dejavu = os.environ["DEJAVU_DIR"]
    os.makedirs(rawdir, exist_ok=True)
    for style, (base_ttf, ov_ufo, *_ ) in FACES.items():
        base = TTFont(os.path.join(dejavu, base_ttf))
        cmap, glyf, hmtx = base.getBestCmap(), base["glyf"], base["hmtx"]
        ufo = UFO.open(os.path.join(ROOT, "sources", ov_ufo))
        for g in ufo:
            cp = g.unicode
            if cp is None or cp not in cmap:
                raise SystemExit("override U+%04X has no base glyph in %s" % (cp or 0, base_ttf))
            name = cmap[cp]
            pen = TTGlyphPen(None)
            g.draw(pen)
            tg = pen.glyph()
            tg.recalcBounds(glyf)
            glyf[name] = tg
            hmtx[name] = (CELL, tg.xMin)
        base.save(os.path.join(rawdir, "AstacidMono-%s.ttf" % style))
        base.close()
        print("  merged", style)


# ── stage 2: Nerd Font glyphs ────────────────────────────────────────────────
def patch_nerd(rawdir, outdir):
    os.makedirs(outdir, exist_ok=True)
    for style in STYLES:
        tmp = os.path.join(outdir, style + ".d")
        os.makedirs(tmp, exist_ok=True)
        subprocess.run([
            "nerd-font-patcher", "--complete", "--mono", "--quiet",
            "--no-progressbars", "--outputdir", tmp,
            os.path.join(rawdir, "AstacidMono-%s.ttf" % style),
        ], check=True)
        (produced,) = [f for f in os.listdir(tmp) if f.endswith(".ttf")]
        os.replace(os.path.join(tmp, produced),
                   os.path.join(outdir, "AstacidMono-%s.ttf" % style))
        os.rmdir(tmp)
        print("  patched", style)


# ── stage 3: authoritative metadata (fonttools) ──────────────────────────────
def apply_metadata(infile, outfile, style):
    """Runs last so it overrides the Nerd patcher's renaming."""
    from fontTools.ttLib import TTFont
    _, _, sub, typo, bold, ital = FACES[style]
    full = FAMILY if style == "Regular" else "%s %s" % (FAMILY, typo)
    ps = "AstacidMono-%s" % style

    f = TTFont(infile)
    name = f["name"]
    for nid in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 14, 16, 17):
        name.removeNames(nameID=nid)

    def setname(nid, val):
        name.setName(val, nid, 3, 1, 0x409)   # Windows / Unicode BMP / en-US
        name.setName(val, nid, 1, 0, 0)       # Mac / Roman / en

    setname(0, COPYRIGHT)
    setname(1, FAMILY)                         # RIBBI family (exactly 4 styles)
    setname(2, sub)                            # RIBBI subfamily
    setname(3, "%s;%s;%s" % (VERSION, VENDOR, ps))
    setname(4, full)
    setname(5, "Version %s" % VERSION)
    setname(6, ps)
    setname(8, "avionix")
    setname(9, "avionix; DejaVu fonts team; Bitstream, Inc.")
    setname(11, "https://github.com/avionix/astacid")
    setname(13, LICENSE)
    setname(14, LICENSE_URL)
    setname(16, FAMILY)                        # typographic family
    setname(17, typo)                          # typographic subfamily (Oblique, not Italic)

    os2 = f["OS/2"]
    os2.achVendID = VENDOR
    fs = os2.fsSelection & ~0b11100001         # clear ITALIC, BOLD, REGULAR
    fs &= ~(1 << 7)                            # clear USE_TYPO_METRICS
    if ital:
        fs |= (1 << 0)
    if bold:
        fs |= (1 << 5)
    if not bold and not ital:
        fs |= (1 << 6)
    fs |= (1 << 7)                             # always USE_TYPO_METRICS
    os2.fsSelection = fs

    head = f["head"]
    head.fontRevision = REVISION
    head.macStyle = (0b01 if bold else 0) | (0b10 if ital else 0)
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "315532800")) + MAC_EPOCH_OFFSET
    head.created = head.modified = epoch

    f.save(outfile)
    print("  meta", style)


# ── orchestration ────────────────────────────────────────────────────────────
def build():
    if "DEJAVU_DIR" not in os.environ:
        sys.exit("DEJAVU_DIR unset — enter the flake devShell or `nix build`.")
    os.environ.setdefault("SOURCE_DATE_EPOCH", "315532800")
    raw = os.path.join(ROOT, "build", "raw")
    patched = os.path.join(ROOT, "build", "patched")
    dist = os.path.join(ROOT, "dist")
    for d in (os.path.join(ROOT, "build"), dist):
        subprocess.run(["rm", "-rf", d], check=True)
    os.makedirs(dist)

    print(">> stage 1: merge overrides onto base")
    merge(raw)
    print(">> stage 2: patch Nerd Font glyphs (--complete --mono)")
    patch_nerd(raw, patched)
    print(">> stage 3: authoritative metadata")
    for style in STYLES:
        apply_metadata(os.path.join(patched, "AstacidMono-%s.ttf" % style),
                       os.path.join(dist, "AstacidMono-%s.ttf" % style), style)
    print(">> done ->", dist)


# ── preview images (Pillow; dev-time, not part of the reproducible build) ────
SAMPLE = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
          "abcdefghijklmnopqrstuvwxyz\n"
          "0123456789 ~!@#$%^&?+*-=,;.:\n"
          "() [] {} \"\" '' \\/ <> -- __")

BG = (30, 30, 46)          # card background (reads on light + dark READMEs)
FG = (205, 214, 244)       # primary text
DIM = (127, 132, 156)      # labels
ACCENT = (243, 139, 168)   # DejaVu ghost in the diff overlay


def render():
    """Regenerate docs/sample.png and docs/diff.png from dist/ + DEJAVU_DIR."""
    from PIL import Image, ImageDraw, ImageFont
    dist = os.path.join(ROOT, "dist")
    docs = os.path.join(ROOT, "docs")
    os.makedirs(docs, exist_ok=True)
    if not os.path.exists(os.path.join(dist, "AstacidMono-Regular.ttf")):
        sys.exit("no dist/ — run `python3 build.py` first.")

    def face(style, size):
        return ImageFont.truetype(os.path.join(dist, "AstacidMono-%s.ttf" % style), size)

    # ── sample.png: the four styles over the sample text ──
    sz, pad, lead, gap = 34, 44, 46, 34
    lines = SAMPLE.splitlines()
    label = ImageFont.truetype(os.path.join(dist, "AstacidMono-Bold.ttf"), 20)
    blocks = [(FAMILY if st == "Regular" else "%s %s" % (FAMILY, FACES[st][3]), face(st, sz))
              for st in STYLES]
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
    img.save(os.path.join(docs, "sample.png"))
    print("  docs/sample.png")

    # ── diff.png: the 16 changed glyphs, DejaVu ghosted under Astacid ──
    gsz, cols = 128, 8
    cw, ch = 128, 172
    rows = (len(CHANGED) + cols - 1) // cols
    dv = ImageFont.truetype(
        os.path.join(os.environ["DEJAVU_DIR"], "DejaVuSansMono.ttf"), gsz)
    ast = face("Regular", gsz)
    img = Image.new("RGBA", (cols * cw, rows * ch + 40), BG + (255,))
    d = ImageDraw.Draw(img)
    d.text((cw * cols // 2, 20), "changed glyphs — DejaVu (pink) vs Astacid",
           font=label, fill=DIM, anchor="mm")
    for i, cp in enumerate(CHANGED):
        cx = (i % cols) * cw + cw // 2
        base = 40 + (i // cols) * ch + int(ch * 0.62)
        ch_ = chr(cp)
        d.text((cx, base), ch_, font=dv, fill=ACCENT + (200,), anchor="ms")
        d.text((cx, base), ch_, font=ast, fill=FG + (255,), anchor="ms")
    img.convert("RGB").save(os.path.join(docs, "diff.png"))
    print("  docs/diff.png")


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "build"
    if arg == "build":
        build()
    elif arg == "render":
        render()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
