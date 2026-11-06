{
  description = "Sami Ansari's résumé as HTML and PDF";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      eachSystem = nixpkgs.lib.genAttrs systems;
      src = nixpkgs.lib.fileset.toSource {
        root = ./.;
        fileset = nixpkgs.lib.fileset.unions [
          ./build.py ./resume.json ./index.template.html ./index.html ./resume.pdf ./assets
        ];
      };
      build = system:
        let pkgs = nixpkgs.legacyPackages.${system};
        in pkgs.runCommand "resume" { nativeBuildInputs = [ pkgs.python3 ]; } ''
          cp -r ${src} source
          chmod -R u+w source
          cd source
          cp index.html committed.html
          export PYTHONDONTWRITEBYTECODE=1
          python build.py
          cmp index.html committed.html || { echo "index.html is stale: run python build.py"; exit 1; }
          mkdir -p $out
          cp index.html resume.pdf $out/
          cp -r assets $out/
        '';
    in {
      packages = eachSystem (system: { default = build system; });
      checks = eachSystem (system: { site = self.packages.${system}.default; });
    };
}
