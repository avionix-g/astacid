#!/usr/bin/env fontforge
"""Merge the Astacid override layers onto the pinned DejaVu base faces.

Stage 1 of the reproducible build. Outline-only: transplant the 16 override
glyphs of each face onto the corresponding pristine DejaVu Sans Mono 2.37 face
and emit an unpatched, DejaVu-named TTF per face into build/raw/. Metadata is
handled later (build_meta.py); Nerd glyphs are added in between (build.sh).

Base faces come from $DEJAVU_DIR (pinned nixpkgs dejavu_fonts).
"""
import fontforge, sys, os

RAW = sys.argv[1]                       # output dir for raw merged TTFs
DEJAVU = os.environ["DEJAVU_DIR"]
CELL = 1233

# base ttf, override sfd, raw output basename
FACES = [
    ("DejaVuSansMono.ttf",             "overrides.sfd",             "AstacidMono-Regular"),
    ("DejaVuSansMono-Bold.ttf",        "overrides-bold.sfd",        "AstacidMono-Bold"),
    ("DejaVuSansMono-Oblique.ttf",     "overrides-oblique.sfd",     "AstacidMono-Oblique"),
    ("DejaVuSansMono-BoldOblique.ttf", "overrides-boldoblique.sfd", "AstacidMono-BoldOblique"),
]

for base_ttf, ov_sfd, out in FACES:
    base = fontforge.open(os.path.join(DEJAVU, base_ttf))
    ov = fontforge.open("sources/" + ov_sfd)
    for g in ov.glyphs():
        cp = g.unicode
        ov.selection.select(("unicode",), cp)
        ov.copy()
        base.selection.select(("unicode",), cp)
        base.clear()
        base.paste()
        base[cp].width = CELL
    base.generate(os.path.join(RAW, out + ".ttf"))
    print("merged", out)
    base.close(); ov.close()
