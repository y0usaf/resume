#!/usr/bin/env python3
"""JSON CLI for the reusable :class:`tui.Grid` drawing API."""
import argparse
import json
import os
from urllib.parse import quote, urlparse
from pathlib import Path
from tui import Grid

ROOT = Path(__file__).parent

def from_spec(spec, spec_dir=None, output_dir=None):
    """Build a grid from a JSON object.

    ``spec_dir`` and ``output_dir`` are used for local image operations.  The
    grid itself remains filesystem agnostic: it receives the URL that will be
    valid from the eventual output document.
    """
    if not isinstance(spec, dict): raise ValueError("spec must be an object")
    unknown = set(spec) - {"width", "height", "operations"}
    if unknown: raise ValueError(f"unknown spec keys: {sorted(unknown)}")
    grid = Grid(spec.get("width"), spec.get("height"))
    operations = spec.get("operations", [])
    if not isinstance(operations, list): raise ValueError("operations must be an array")
    allowed_map = {
        "text": {"op", "x", "y", "text", "style", "scale"},
        "line": {"op", "x1", "y1", "x2", "y2", "style"},
        "box": {"op", "x", "y", "width", "height", "title", "style"},
        "image": {"op", "x", "y", "width", "height", "src", "alt"},
    }
    for op in operations:
        if not isinstance(op, dict) or not isinstance(op.get("op"), str): raise ValueError("each operation needs an op")
        kind = op["op"]
        if kind not in allowed_map: raise ValueError(f"unknown operation: {kind}")
        extra = set(op) - allowed_map[kind]
        if extra: raise ValueError(f"unknown {kind} keys: {sorted(extra)}")
        style = op.get("style", "")
        if kind == "text": grid.text(op.get("x"), op.get("y"), op.get("text"), style, op.get("scale", 1))
        elif kind == "line": grid.line(op.get("x1"), op.get("y1"), op.get("x2"), op.get("y2"), style)
        elif kind == "box": grid.box(op.get("x"), op.get("y"), op.get("width"), op.get("height"), op.get("title"), style)
        else:
            src = op.get("src")
            if spec_dir is not None:
                parsed = urlparse(src) if isinstance(src, str) else None
                if parsed is None or parsed.scheme.lower() != "https":
                    source = Path(src) if isinstance(src, str) else Path("")
                    if not source.is_absolute(): source = Path(spec_dir) / source
                    if not source.is_file(): raise ValueError(f"image source does not exist: {src!r}")
                    if output_dir is None: output_dir = spec_dir
                    src = quote(os.path.relpath(source, output_dir), safe="/:")
            grid.image(op.get("x"), op.get("y"), op.get("width"), op.get("height"), src, op.get("alt", ""))
    return grid

def document(grid, output):
    css = quote(os.path.relpath(ROOT / "terminal.css", output.parent))
    font = quote(os.path.relpath(ROOT / "assets" / "DepartureMono-Regular.ttf", output.parent))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Terminal grid</title>
<link rel="stylesheet" href="{css}"><style>@font-face{{font-family:"Departure Mono";src:url("{font}") format("truetype")}}body{{margin:32px;background:#e4e3dc}}.terminal{{--terminal-cols:{grid.width};--terminal-rows:{grid.height};font-family:"Departure Mono",monospace}}</style></head>
<body><pre class="terminal">{grid.render()}</pre></body></html>
'''

def main(argv=None):
    parser = argparse.ArgumentParser(description="render a terminal grid JSON spec")
    parser.add_argument("spec", type=Path); parser.add_argument("output", type=Path)
    parser.add_argument("--format", choices=("html", "text"), help="output format (defaults from extension)")
    args = parser.parse_args(argv)
    try:
        spec = json.loads(args.spec.read_text())
        grid = from_spec(spec, args.spec.parent, args.output.parent)
        fmt = args.format or ("text" if args.output.suffix == ".txt" else "html")
        rendered = grid.plain() + "\n" if fmt == "text" else document(grid, args.output)
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(rendered)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        parser.error(str(error))

if __name__ == "__main__": main()
