{
  description = "Astacid Mono — a DejaVu-based programming font (reproducible dev + build env)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f (import nixpkgs { inherit system; }));
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.fontforge            # glyph editing + build.py scripting engine
            pkgs.nerd-font-patcher    # binary: `nerd-font-patcher` (bundles the Nerd Font glyph set)
            pkgs.ruff                 # Python linter/formatter for build.py
            pkgs.woff2                # woff2_compress for optional web artifact
            (pkgs.python3.withPackages (ps: [
              ps.fonttools            # merge + name-table surgery
              ps.ufolib2              # read the UFO override glyph sources
              ps.brotli               # WOFF2 support for fonttools
              ps.pillow               # `build.py render` preview images (dev only)
              ps.pytest               # test suite (tests/)
            ]))
          ];

          # Pristine DejaVu Sans Mono base
          DEJAVU_DIR = "${pkgs.dejavu_fonts}/share/fonts/truetype";

          shellHook = ''
            echo "Astacid dev shell:"
            echo "  fontforge         $(fontforge --version 2>&1 | grep -oiE 'fontforge [0-9]+' | head -1)"
            echo "  nerd-font-patcher $(nerd-font-patcher --version 2>/dev/null | head -1)"
            echo "  fonttools         $(python3 -c 'import fontTools; print(fontTools.version)')"
            echo "  ruff              $(ruff --version)"
            echo "  dejavu base       ${pkgs.dejavu_fonts.version}  ($DEJAVU_DIR)"
          '';
        };
      });

      packages = forAllSystems (pkgs: {
        default = pkgs.stdenv.mkDerivation {
          pname = "astacid-mono";
          version = "2.0.0";
          src = self;
          nativeBuildInputs = [
            pkgs.nerd-font-patcher
            (pkgs.python3.withPackages (ps: [ ps.fonttools ps.ufolib2 ps.brotli ]))
          ];
          DEJAVU_DIR = "${pkgs.dejavu_fonts}/share/fonts/truetype";
          buildPhase = "python3 build.py";
          installPhase = "install -Dm644 dist/*.ttf -t $out/share/fonts/truetype";
        };
      });
    };
}
