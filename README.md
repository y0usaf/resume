# Terminal grid

`generate.py` renders a small fixed character grid to static HTML or plain text. It has no runtime JavaScript and is suitable for embedding in the resume or another static page.

The coordinate API is zero based:

```python
from tui import Grid

grid = Grid(40, 8)
grid.box(0, 0, 40, 8, " STATUS ", "rule")
grid.text(3, 3, "ready", "accent strong")
grid.text(3, 5, "heading", "strong", scale=2)
grid.line(10, 3, 20, 3, "rule")
grid.image(30, 5, 6, 2, "assets/github.png", "logo")
html_fragment = grid.render()
plain_text = grid.plain()
```

JSON uses the same operations:

```sh
python generate.py example.json terminal-example.html
python generate.py example.json terminal-example.txt --format text
```

The HTML output links to `terminal.css` and the bundled Departure Mono font using paths relative to the output file. Keep those assets available when moving or publishing the HTML. Invalid JSON, unknown operations, missing images, and out-of-bounds drawing fail before the output file is created. Image paths in JSON are resolved relative to the spec file and rewritten relative to the output file.

Edit `resume.json`, then run `python build.py` to regenerate `index.html`. Both the resume and graphics CLI import `tui.Grid`; drawing rules live in `tui.py`, and surface styling lives in `terminal.css`. Other projects can import that module or invoke this CLI with their own JSON spec.

Resume projects use `{ "name": "...", "stack": "...", "description": "..." }`. Each gets a heading and a wrapped description in the selected projects section. The resume checks row capacity and rejects content that would overflow its single Letter page.

Run `nix build path:.` to build the static site in `result/`, or `nix flake check path:.` to verify it. The path form includes new files before they are tracked by Git. `python -m unittest discover` is the native fallback.

Open the generated HTML in a browser to print to PDF. To capture the example as a PNG with Chromium:

```sh
chromium --headless --screenshot=graphic.png --window-size=640,400 "file://$PWD/terminal-example.html"
```

Drawing uses fixed single-cell Unicode characters. Text covers line glyphs regardless of drawing order; underlying connections are retained. Scaled text reserves its rectangular footprint and emits its text once in plain output. Images reserve a rectangle and render as an escaped `<img>` element. Combining marks, controls, and wide Unicode characters are rejected because they do not have one terminal cell. Wrap `grid.render()` in `<pre class="terminal">` and set `--terminal-cols` and `--terminal-rows` to the grid dimensions when embedding it yourself.

HTML uses one CSS grid track per character, so font fallback and bold text cannot shift later columns. Keep the generated row/cell markup and `terminal.css` together; `grid.plain()` remains ordinary text.
