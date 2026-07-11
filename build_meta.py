#!/usr/bin/env python3
"""Stage 3: authoritative metadata pass (fonttools).

Runs last, after the Nerd patch, so it overrides the patcher's renaming. Sets
the Astacid name table (RIBBI + typographic IDs 16/17), OS/2 vendor + selection
bits (incl. USE_TYPO_METRICS), head revision/macStyle, and deterministic
timestamps from SOURCE_DATE_EPOCH. Outlines and hinting are untouched.

Usage: build_meta.py <in.ttf> <out.ttf> <Regular|Bold|Oblique|BoldOblique>
"""
import sys, os
from fontTools.ttLib import TTFont

FAMILY = "Astacid Mono"
VENDOR = "AVNX"
VERSION = "2.000"
REVISION = 2.0
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
MAC_EPOCH_OFFSET = 2082844800   # 1970-01-01 -> 1904-01-01

STYLES = {
    "Regular":     dict(sub="Regular",     typo="Regular",      bold=False, ital=False),
    "Bold":        dict(sub="Bold",        typo="Bold",         bold=True,  ital=False),
    "Oblique":     dict(sub="Italic",      typo="Oblique",      bold=False, ital=True),
    "BoldOblique": dict(sub="Bold Italic", typo="Bold Oblique", bold=True,  ital=True),
}

infile, outfile, style = sys.argv[1], sys.argv[2], sys.argv[3]
s = STYLES[style]
full = FAMILY if style == "Regular" else "%s %s" % (FAMILY, s["typo"])
ps = "AstacidMono-%s" % style

f = TTFont(infile)
name = f["name"]

# Wipe managed name IDs on both Windows and Mac platforms, then set fresh so no
# DejaVu/Nerd leftovers survive.
for nid in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 14, 16, 17):
    name.removeNames(nameID=nid)

def setname(nid, val):
    name.setName(val, nid, 3, 1, 0x409)   # Windows / Unicode BMP / en-US
    name.setName(val, nid, 1, 0, 0)       # Mac / Roman / en

setname(0, COPYRIGHT)
setname(1, FAMILY)                        # RIBBI family (exactly 4 styles)
setname(2, s["sub"])                      # RIBBI subfamily (Regular/Bold/Italic/Bold Italic)
setname(3, "%s;%s;%s" % (VERSION, VENDOR, ps))
setname(4, full)
setname(5, "Version %s" % VERSION)
setname(6, ps)
setname(8, "avionix")
setname(9, "avionix; DejaVu fonts team; Bitstream, Inc.")
setname(11, "https://github.com/avionix/astacid")
setname(13, LICENSE)
setname(14, LICENSE_URL)
setname(16, FAMILY)                       # typographic family
setname(17, s["typo"])                    # typographic subfamily (Oblique, not Italic)

# OS/2 selection + vendor
os2 = f["OS/2"]
os2.achVendID = VENDOR
fs = os2.fsSelection & ~0b11100001        # clear ITALIC, BOLD, REGULAR, USE_TYPO(bit7 handled below)
fs &= ~(1 << 7)
if s["ital"]:
    fs |= (1 << 0)
if s["bold"]:
    fs |= (1 << 5)
if not s["bold"] and not s["ital"]:
    fs |= (1 << 6)
fs |= (1 << 7)                            # USE_TYPO_METRICS
os2.fsSelection = fs

# head revision + macStyle + deterministic timestamps
head = f["head"]
head.fontRevision = REVISION
mac = 0
if s["bold"]:
    mac |= 0b01
if s["ital"]:
    mac |= 0b10
head.macStyle = mac
epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "315532800")) + MAC_EPOCH_OFFSET
head.created = epoch
head.modified = epoch

f.save(outfile)
print("meta", style, "->", os.path.basename(outfile))
