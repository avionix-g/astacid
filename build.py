#!/usr/bin/env python3
"""Astacid Mono build pipeline

    python3 build.py     # build all four faces into dist/

Patches override glyphs onto pristine DejaVu Sans Mono faces, adds the Nerd
Font glyph set, and writes an authoritative name table. Bit-for-bit
reproducible. README preview images live in render.py.

Process:
1. Merge the UFO override outlines onto the base faces with fonttools.
2. Add Nerd Font glyphs via the external `nerd-font-patcher`.
3. Rewrite the name/OS-2/head tables with fonttools.

Environment:
    DEJAVU_DIR   dir holding the 4 pristine DejaVu Sans Mono TTFs
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import IntFlag
from pathlib import Path

# --- layout ---
ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
RAW = BUILD / "raw"
PATCHED = BUILD / "patched"

# --- identity ---
FAMILY = "Astacid Mono"
STEM = FAMILY.replace(" ", "")  # filename / PostScript prefix
VENDOR = "AVNX"
# Versioning is major.minor only; semver is pointless for a font. The canonical
# string lives in the VERSION file so build.py and flake.nix can't drift.
MAJOR, MINOR = (int(n) for n in (ROOT / "VERSION").read_text().strip().split("."))
VERSION = f"{MAJOR}.{MINOR:03d}"  # name-table string, e.g. "2.000"
REVISION = MAJOR + MINOR / 1000  # head.fontRevision (16.16 fixed)
CELL = 1233  # monospace advance width at 2048 UPM
# Fixed so builds are bit-reproducible. The value is the repo's initial commit
# (2022-07-09); the exact instant is arbitrary — only its constancy matters.
EPOCH = 1657375334


def face_filename(style):
    return f"{STEM}-{style}.ttf"


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


def dejavu_dir():
    d = os.environ.get("DEJAVU_DIR")
    if not d:
        sys.exit("DEJAVU_DIR unset -- enter the flake devShell or `nix build`.")
    return Path(d)


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

    dejavu = dejavu_dir()
    rawdir.mkdir(parents=True, exist_ok=True)
    for style, face in FACES.items():
        base = TTFont(dejavu / face.base_ttf)
        cmap, glyf, hmtx = base.getBestCmap(), base["glyf"], base["hmtx"]
        ufo = UFO.open(SOURCES / face.override_ufo)
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
        base.save(str(rawdir / face_filename(style)))
        base.close()
        print("  merged", style)


# --- stage 2: Nerd Font glyphs ---
def patch_nerd(rawdir, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    for style in STYLES:
        tmp = outdir / f"{style}.d"
        tmp.mkdir(exist_ok=True)
        subprocess.run(
            [
                "nerd-font-patcher",
                "--complete",
                "--mono",
                "--quiet",
                "--no-progressbars",
                "--outputdir",
                str(tmp),
                str(rawdir / face_filename(style)),
            ],
            check=True,
        )
        produced = list(tmp.glob("*.ttf"))
        if len(produced) != 1:
            sys.exit(f"expected 1 patched TTF for {style}, got {len(produced)}")
        produced[0].replace(outdir / face_filename(style))
        tmp.rmdir()
        print("  patched", style)


# --- stage 3: authoritative metadata (fonttools) ---
def apply_metadata(infile, outfile, style):
    """Runs last so it overrides the Nerd patcher's renaming."""
    from fontTools.misc.timeTools import epoch_diff
    from fontTools.ttLib import TTFont

    face = FACES[style]
    full = FAMILY if style == "Regular" else f"{FAMILY} {face.typographic}"
    ps = f"{STEM}-{style}"

    f = TTFont(str(infile), recalcTimestamp=False)  # keep our explicit head.modified
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

    f.save(str(outfile))
    print("  meta", style)


# --- orchestration ---
def build():
    dejavu_dir()  # fail early if unset
    for d in (BUILD, DIST):
        shutil.rmtree(d, ignore_errors=True)
    DIST.mkdir()

    print(">> stage 1: merge overrides onto base")
    merge(RAW)
    print(">> stage 2: patch Nerd Font glyphs (--complete --mono)")
    patch_nerd(RAW, PATCHED)
    print(">> stage 3: authoritative metadata")
    for style in STYLES:
        apply_metadata(
            PATCHED / face_filename(style),
            DIST / face_filename(style),
            style,
        )
    print(">> done ->", DIST)


if __name__ == "__main__":
    build()
