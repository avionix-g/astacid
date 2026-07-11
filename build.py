#!/usr/bin/env python3
"""Astacid Mono build pipeline

    python3 build.py            # build all four faces into dist/
    python3 build.py render     # regenerate assets/ preview images

The font build patches override glyphs onto pristine DejaVu Sans Mono faces,
adds the Nerd Font glyph set, and writes an authoritative name table. It is
bit-for-bit reproducible.

Process:
1. Merge the UFO override outlines onto the base faces with fonttools.
2. Add Nerd Font glyphs via the external `nerd-font-patcher`.
3. Rewrite the name/OS-2/head tables with fonttools.

Engine imports are lazy so a plain `render` run only needs Pillow.

Environment:
    DEJAVU_DIR   dir holding the 4 pristine DejaVu Sans Mono TTFs
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import IntFlag

ROOT = os.path.dirname(os.path.abspath(__file__))

# --- identity ---
FAMILY = "Astacid Mono"
VENDOR = "AVNX"
VERSION = "2.000"
REVISION = float(VERSION)
CELL = 1233  # monospace advance width at 2048 UPM
EPOCH = 1786419187  # canonical build timestamp (head.created/modified)


class FsSelection(IntFlag):
    """OS/2 fsSelection bits we set."""

    ITALIC = 1 << 0
    BOLD = 1 << 5
    REGULAR = 1 << 6
    USE_TYPO_METRICS = 1 << 7


class MacStyle(IntFlag):
    """head macStyle bits."""

    BOLD = 1 << 0
    ITALIC = 1 << 1


COPYRIGHT = (
    "Astacid Mono (c) 2022-2026 avionix. A derivative of DejaVu Sans "
    "Mono. DejaVu (c) the DejaVu fonts team; Bitstream Vera Fonts "
    "(c) 2003 Bitstream, Inc. Bitstream Vera is a trademark of "
    "Bitstream, Inc."
)
LICENSE = (
    "Astacid changes are released under the same terms as DejaVu: the "
    "Bitstream Vera license plus public-domain additions. Use, "
    "modification, and redistribution are permitted; the Bitstream Vera "
    "and DejaVu names may not be used to promote derivatives without "
    "permission."
)
LICENSE_URL = "https://dejavu-fonts.github.io/License.html"


@dataclass(frozen=True)
class Face:
    base_ttf: str  # pristine DejaVu source
    override_ufo: str  # glyph override source
    subfamily: str  # RIBBI subfamily (name ID 2): Italic, not Oblique
    typographic: str  # typographic subfamily (name ID 17): Oblique

    @property
    def bold(self):
        return "Bold" in self.subfamily

    @property
    def italic(self):
        return "Italic" in self.subfamily


FACES = {
    "Regular": Face("DejaVuSansMono.ttf", "overrides.ufo", "Regular", "Regular"),
    "Bold": Face("DejaVuSansMono-Bold.ttf", "overrides-bold.ufo", "Bold", "Bold"),
    "Oblique": Face(
        "DejaVuSansMono-Oblique.ttf", "overrides-oblique.ufo", "Italic", "Oblique"
    ),
    "BoldOblique": Face(
        "DejaVuSansMono-BoldOblique.ttf",
        "overrides-boldoblique.ufo",
        "Bold Italic",
        "Bold Oblique",
    ),
}
STYLES = list(FACES)


# codepoints that differ from stock DejaVu (used only by `render`)
CHANGED = [
    0x24,
    0x25,
    0x28,
    0x29,
    0x2A,
    0x2D,
    0x30,
    0x5E,
    0x5F,
    0x69,
    0x6C,
    0x7B,
    0x7D,
    0x7E,
    0xA1,
    0xBF,
]


# --- stage 1: merge overrides onto base (fonttools + ufoLib2) ---
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
    for style, face in FACES.items():
        base = TTFont(os.path.join(dejavu, face.base_ttf))
        cmap, glyf, hmtx = base.getBestCmap(), base["glyf"], base["hmtx"]
        ufo = UFO.open(os.path.join(ROOT, "sources", face.override_ufo))
        for g in ufo:
            cp = g.unicode
            if cp is None or cp not in cmap:
                raise SystemExit(
                    f"override U+{cp or 0:04X} has no base glyph in {face.base_ttf}"
                )
            name = cmap[cp]
            pen = TTGlyphPen(None)
            g.draw(pen)
            tg = pen.glyph()
            tg.recalcBounds(glyf)
            glyf[name] = tg
            hmtx[name] = (CELL, tg.xMin)
        base.save(os.path.join(rawdir, f"AstacidMono-{style}.ttf"))
        base.close()
        print("  merged", style)


# --- stage 2: Nerd Font glyphs ---
def patch_nerd(rawdir, outdir):
    os.makedirs(outdir, exist_ok=True)
    for style in STYLES:
        tmp = os.path.join(outdir, style + ".d")
        os.makedirs(tmp, exist_ok=True)
        subprocess.run(
            [
                "nerd-font-patcher",
                "--complete",
                "--mono",
                "--quiet",
                "--no-progressbars",
                "--outputdir",
                tmp,
                os.path.join(rawdir, f"AstacidMono-{style}.ttf"),
            ],
            check=True,
        )
        (produced,) = [f for f in os.listdir(tmp) if f.endswith(".ttf")]
        os.replace(
            os.path.join(tmp, produced),
            os.path.join(outdir, f"AstacidMono-{style}.ttf"),
        )
        os.rmdir(tmp)
        print("  patched", style)


# --- stage 3: authoritative metadata (fonttools) ---
def apply_metadata(infile, outfile, style):
    """Runs last so it overrides the Nerd patcher's renaming."""
    from fontTools.misc.timeTools import epoch_diff
    from fontTools.ttLib import TTFont

    face = FACES[style]
    full = FAMILY if style == "Regular" else f"{FAMILY} {face.typographic}"
    ps = f"AstacidMono-{style}"

    f = TTFont(infile, recalcTimestamp=False)  # keep our explicit head.modified
    name = f["name"]
    for nid in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 14, 16, 17):
        name.removeNames(nameID=nid)

    def setname(nid, val):
        name.setName(val, nid, 3, 1, 0x409)  # Windows / Unicode BMP / en-US
        name.setName(val, nid, 1, 0, 0)  # Mac / Roman / en

    setname(0, COPYRIGHT)
    setname(1, FAMILY)  # RIBBI family (exactly 4 styles)
    setname(2, face.subfamily)  # RIBBI subfamily
    setname(3, f"{VERSION};{VENDOR};{ps}")
    setname(4, full)
    setname(5, f"Version {VERSION}")
    setname(6, ps)
    setname(8, "avionix")
    setname(9, "avionix; DejaVu fonts team; Bitstream, Inc.")
    setname(11, "https://github.com/avionix/astacid")
    setname(13, LICENSE)
    setname(14, LICENSE_URL)
    setname(16, FAMILY)  # typographic family
    setname(17, face.typographic)  # typographic subfamily (Oblique, not Italic)

    os2 = f["OS/2"]
    os2.achVendID = VENDOR
    fs = os2.fsSelection & ~FsSelection(
        FsSelection.ITALIC | FsSelection.BOLD | FsSelection.REGULAR
    )
    fs |= FsSelection.USE_TYPO_METRICS  # always
    if face.italic:
        fs |= FsSelection.ITALIC
    if face.bold:
        fs |= FsSelection.BOLD
    if not face.bold and not face.italic:
        fs |= FsSelection.REGULAR
    os2.fsSelection = fs

    head = f["head"]
    head.fontRevision = REVISION
    head.macStyle = (MacStyle.BOLD if face.bold else 0) | (
        MacStyle.ITALIC if face.italic else 0
    )
    head.created = head.modified = EPOCH - epoch_diff

    f.save(outfile)
    print("  meta", style)


# --- orchestration ---
def build():
    if "DEJAVU_DIR" not in os.environ:
        sys.exit("DEJAVU_DIR unset -- enter the flake devShell or `nix build`.")
    raw = os.path.join(ROOT, "build", "raw")
    patched = os.path.join(ROOT, "build", "patched")
    dist = os.path.join(ROOT, "dist")
    for d in (os.path.join(ROOT, "build"), dist):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(dist)

    print(">> stage 1: merge overrides onto base")
    merge(raw)
    print(">> stage 2: patch Nerd Font glyphs (--complete --mono)")
    patch_nerd(raw, patched)
    print(">> stage 3: authoritative metadata")
    for style in STYLES:
        apply_metadata(
            os.path.join(patched, f"AstacidMono-{style}.ttf"),
            os.path.join(dist, f"AstacidMono-{style}.ttf"),
            style,
        )
    print(">> done ->", dist)


# --- preview images (Pillow; dev-time, not part of the reproducible build) ---
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
    """Regenerate assets/sample.png and assets/diff.png from dist/ + DEJAVU_DIR."""
    from PIL import Image, ImageDraw, ImageFont

    dist = os.path.join(ROOT, "dist")
    assets = os.path.join(ROOT, "assets")
    os.makedirs(assets, exist_ok=True)
    if not os.path.exists(os.path.join(dist, "AstacidMono-Regular.ttf")):
        sys.exit("no dist/ -- run `python3 build.py` first.")

    def face(style, size):
        return ImageFont.truetype(os.path.join(dist, f"AstacidMono-{style}.ttf"), size)

    # --- sample.png: the four styles over the sample text ---
    sz, pad, lead, gap = 34, 44, 46, 34
    lines = SAMPLE.splitlines()
    label = ImageFont.truetype(os.path.join(dist, "AstacidMono-Bold.ttf"), 20)
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
    img.save(os.path.join(assets, "sample.png"))
    print("  assets/sample.png")

    # --- diff.png: the 16 changed glyphs, DejaVu ghosted under Astacid ---
    gsz, cols = 128, 8
    cw, ch = 128, 172
    rows = (len(CHANGED) + cols - 1) // cols
    dv = ImageFont.truetype(
        os.path.join(os.environ["DEJAVU_DIR"], "DejaVuSansMono.ttf"), gsz
    )
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
    img.convert("RGB").save(os.path.join(assets, "diff.png"))
    print("  assets/diff.png")


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
