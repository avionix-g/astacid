# Astacid Mono

A DejaVu-based monospace font for programming: DejaVu Sans Mono 2.37 with 16
hand-tuned glyphs, four styles, patched with the full
[Nerd Font](https://github.com/ryanoasis/nerd-fonts) set.

![Astacid Mono — four styles](assets/sample.png)

## Changed glyphs

![Astacid vs DejaVu](assets/diff.png)

| glyph | change |
|-------|--------|
| `( ) { }` | untapered parens, enlarged braces (Ubuntu Mono forms) |
| `*` | weight and size of `+`, raised |
| `-` | widened toward `_`, still clearly a hyphen |
| `^` | larger, more sharply angled |
| `~` | curlier |
| `$ % 0 _ i l ¡ ¿` | legibility and balance refinements |

## Build

Bit-for-bit reproducible via Nix:

```sh
nix build              # → result/share/fonts/truetype/*.ttf
nix develop            # dev shell: fontforge, nerd-font-patcher, fonttools
python build.py        # → dist/
python build.py render # regenerate the assets/ previews
```

Prebuilt faces are committed in [`dist/`](dist) — `nix build` reproduces them
byte-for-byte. Glyph sources are editable UFO under [`sources/`](sources); the
merge, Nerd patch, and metadata all live in a single [`build.py`](build.py).

## Credits & license

Astacid borrows from [DejaVu](https://dejavu-fonts.github.io/) (a Bitstream Vera
derivative, © 2003 Bitstream, Inc.),
[DejaVu Sans Mono Bront](https://github.com/chrismwendt/bront),
[Ubuntu Mono](https://fonts.google.com/specimen/Ubuntu+Mono),
[Hack](https://github.com/source-foundry/Hack), and
[Nerd Fonts](https://github.com/ryanoasis/nerd-fonts). Astacid's own work is MIT;
bundled glyphs retain their upstream licenses. See [LICENSE](LICENSE).
