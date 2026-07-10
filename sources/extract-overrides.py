#!/usr/bin/env fontforge
"""Extract the intentional Astacid edits from the legacy monolithic SFD into a
minimal, self-contained override layer (sources/overrides.sfd).

Run once to (re)generate the override source from astacid-mono.sfd. After this,
overrides.sfd is the hand-edited source of truth and this script is not needed
in the normal build path.
"""
import fontforge, psMat

CELL = 1233  # DejaVu Sans Mono advance cell at 2048 UPM
# * and - were hand-drawn by eye and left with off-cell advances (1276 / 1183).
# Both shapes are internally symmetric, so re-center them rigidly on the cell.
RECENTER = {0x2A, 0x2D}

# The ~14 intentional design edits (see HANDOFF.md / README). Everything else in
# the legacy SFD is either pristine DejaVu or base-version drift and is dropped.
KEEP = {
    0x24,  # $  dollar        (Bront)
    0x25,  # %  percent       (Bront)
    0x28,  # (  parenleft
    0x29,  # )  parenright
    0x2A,  # *  asterisk
    0x2D,  # -  hyphen
    0x30,  # 0  zero          (slashed, Bront)
    0x5E,  # ^  asciicircum
    0x5F,  # _  underscore
    0x69,  # i  i             (Bront)
    0x6C,  # l  l             (Bront)
    0x7B,  # {  braceleft
    0x7D,  # }  braceright
    0x7E,  # ~  asciitilde
    0xA1,  # ¡  exclamdown
    0xBF,  # ¿  questiondown
}

src = fontforge.open("astacid-mono.sfd")

# Flatten any composites so each override glyph is self-contained (robust when
# merged onto a pristine base that may name/compose glyphs differently).
for cp in KEEP:
    if cp in src:
        g = src[cp]
        if g.references:
            g.unlinkRef()

# Remove everything not in the keep set.
for g in list(src.glyphs()):
    if g.unicode not in KEEP:
        src.removeGlyph(g)

# Normalize advances to one cell; re-center the two off-cell symmetric glyphs.
for g in src.glyphs():
    if g.unicode in RECENTER:
        bb = g.boundingBox()
        target_lsb = round((CELL - (bb[2] - bb[0])) / 2.0)
        g.transform(psMat.translate(target_lsb - bb[0], 0))
    g.width = CELL

present = sorted(g.unicode for g in src.glyphs())
missing = sorted(KEEP - set(present))
print("kept %d glyphs: %s" % (len(present), " ".join("U+%04X" % c for c in present)))
if missing:
    raise SystemExit("MISSING from source: %s" % " ".join("U+%04X" % c for c in missing))

src.familyname = "Astacid Overrides"
src.fontname = "AstacidOverrides"
src.fullname = "Astacid Overrides"
src.save("sources/overrides.sfd")
print("wrote sources/overrides.sfd")
