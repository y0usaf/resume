{
  description = "Static HTML TUI graphics and resume";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      eachSystem = nixpkgs.lib.genAttrs systems;
      src = nixpkgs.lib.fileset.toSource {
        root = ./.;
        fileset = nixpkgs.lib.fileset.unions [
          ./tui.py ./generate.py ./build.py ./test_tui.py
          ./resume.json ./example.json ./index.template.html
          ./terminal.css ./assets
        ];
      };
      build = system:
        let pkgs = nixpkgs.legacyPackages.${system};
        in pkgs.runCommand "html-tui" { nativeBuildInputs = [ pkgs.python3 ]; } ''
          cp -r ${src} source
          chmod -R u+w source
          cd source
          export PYTHONDONTWRITEBYTECODE=1
          python -m unittest discover -v
          python build.py
          python generate.py example.json terminal-example.html
          mkdir -p $out
          cp index.html terminal-example.html terminal.css $out/
          cp -r assets $out/
        '';
    in {
      packages = eachSystem (system: { default = build system; });
      checks = eachSystem (system: { site = self.packages.${system}.default; });
    };
}
