import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path

import build
from generate import document, from_spec
from tui import Grid


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((build.ROOT / 'resume.json').read_text())

    def test_resume_retains_content_within_one_page(self):
        chunks = []
        parser = HTMLParser()
        parser.handle_data = chunks.append
        parser.feed(build.render(self.data))
        plain = ''.join(chunks)
        self.assertEqual(len(plain.splitlines()), build.LETTER_ROWS)
        prose = ' '.join(plain.translate(str.maketrans('', '', '│┌┐└┘─├┤┬┴┼→')).split())
        values = list(self.data['person'].values()) + list(self.data['speaking'].values())
        values += []
        for project in self.data['projects']:
            values += list(project.values())
        for job in self.data['experience']:
            values += [job[key] for key in ('title', 'company', 'period')]
            values += job['bullets']
        for value in values:
            with self.subTest(value=value):
                self.assertIn(' '.join(value.replace('-|', '-').replace('|', ' ').split()), prose)

    def test_resume_rejects_overflow(self):
        data = deepcopy(self.data)
        data['experience'] *= 3
        with self.assertRaisesRegex(ValueError, 'letter capacity'):
            build.render(data)
        with self.assertRaisesRegex(ValueError, 'wider'):
            build.wrapped('x' * 100, 86)
        data = deepcopy(self.data)
        data['experience'][0]['title'] = 'x' * 80
        with self.assertRaisesRegex(ValueError, 'overlap'):
            build.render(data)


class GridTests(unittest.TestCase):
    def test_bounds_and_overflow_are_errors(self):
        grid = Grid(4, 2)
        with self.assertRaises(ValueError): grid.text(3, 0, "xx")
        with self.assertRaises(ValueError): grid.line(0, 0, 4, 0)
        with self.assertRaises(ValueError): grid.box(0, 0, 5, 2)

    def test_crossing_lines_make_a_junction(self):
        grid = Grid(5, 5).line(0, 2, 4, 2).line(2, 0, 2, 4)
        self.assertEqual(grid.plain().splitlines()[2], "╶─┼─╴")

    def test_box_corners_and_reverse_lines_are_stable(self):
        box = Grid(6, 4).box(1, 1, 4, 2)
        self.assertEqual(box.plain().splitlines()[1], " ┌──┐ ")
        self.assertEqual(box.plain().splitlines()[2], " └──┘ ")
        forward = Grid(5, 1).line(0, 0, 4, 0).plain()
        reverse = Grid(5, 1).line(4, 0, 0, 0).plain()
        self.assertEqual(forward, reverse)

    def test_html_escapes_text_and_style(self):
        rendered = Grid(8, 1).text(0, 0, "<&", 'accent"x').render()
        self.assertIn("&lt;</span><span", rendered)
        self.assertIn("&amp;</span><span", rendered)
        self.assertIn('accent&quot;x', rendered)

    def test_html_assigns_one_fixed_cell_to_each_column(self):
        rendered = Grid(3, 1).text(0, 0, "ab", "accent").render()
        self.assertIn('<span class="terminal-row">', rendered)
        self.assertEqual(rendered.count('class="terminal-cell accent"'), 2)
        self.assertEqual(rendered.count('class="terminal-cell"'), 1)
        self.assertNotIn("<span class=\"accent\">", rendered)

    def test_scaled_text_keeps_plain_text_readable_and_reserves_area(self):
        grid = Grid(10, 4).text(1, 1, "OK", scale=2)
        self.assertIn("OK", grid.plain())
        with self.assertRaisesRegex(ValueError, "overlap"):
            grid.text(2, 2, "x")

    def test_scaled_text_rejects_overlap_in_either_order(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            Grid(10, 4).text(2, 2, "x").text(1, 1, "OK", scale=2)

    def test_scaled_text_rejects_invalid_scale_and_extent(self):
        for scale in (0, -1, True, "2"):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                Grid(8, 3).text(0, 0, "OK", scale=scale)
        with self.assertRaises(ValueError):
            Grid(3, 2).text(0, 0, "OK", scale=2)

    def test_image_and_scaled_text_overlap_in_either_order(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            Grid(8, 4).image(2, 1, 4, 2, "logo.png").text(1, 1, "OK", scale=2)
        with self.assertRaisesRegex(ValueError, "overlap"):
            Grid(8, 4).text(1, 1, "OK", scale=2).image(2, 1, 4, 2, "logo.png")

    def test_box_collision_does_not_partially_write(self):
        grid = Grid(5, 4).image(0, 1, 1, 2, "logo.png")
        before = grid.plain()
        with self.assertRaisesRegex(ValueError, "overlap"):
            grid.box(0, 0, 5, 4)
        self.assertEqual(grid.plain(), before)

    def test_image_html_escapes_attributes(self):
        rendered = Grid(4, 2).image(0, 0, 4, 2, 'a&".png', '<logo>').render()
        self.assertIn('src="a&amp;&quot;.png"', rendered)
        self.assertIn('alt="&lt;logo&gt;"', rendered)

    def test_spec_rejects_unknown_operation(self):
        with self.assertRaises(ValueError): from_spec({"width": 2, "height": 2, "operations": [{"op": "wat"}]})
        with self.assertRaises(ValueError): from_spec({"width": 2, "height": 2, "oops": []})

    def test_zero_width_combining_mark_is_rejected(self):
        for value in ["e\u0301", "x\ufe0f", "\t", "界"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                Grid(3, 1).text(0, 0, value)

    def test_document_preserves_the_grid_surface(self):
        grid = Grid(6, 3).box(0, 0, 6, 3)
        rendered = document(grid, Path('example.html'))
        self.assertIn(f'<pre class="terminal">{grid.render()}</pre>', rendered)
        self.assertIn('--terminal-cols:6', rendered)
        self.assertIn('--terminal-rows:3', rendered)

    def test_cli_bad_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "bad.json", root / "out.html"
            source.write_text(json.dumps({"width": 2, "height": 2, "operations": [{"op": "text", "x": 9, "y": 0, "text": "x"}]}))
            result = subprocess.run([sys.executable, "generate.py", str(source), str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_cli_missing_image_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "spec.json", root / "nested" / "out.html"
            source.write_text(json.dumps({"width": 2, "height": 2, "operations": [
                {"op": "image", "x": 0, "y": 0, "width": 2, "height": 2, "src": "missing.png"}
            ]}))
            result = subprocess.run([sys.executable, "generate.py", str(source), str(output)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())

    def test_cli_relocates_image_paths_from_spec_to_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()
            (assets / "logo.svg").write_text("<svg/>")
            source, output = root / "spec.json", root / "pages" / "out.html"
            source.write_text(json.dumps({"width": 2, "height": 2, "operations": [
                {"op": "image", "x": 0, "y": 0, "width": 2, "height": 2, "src": "assets/logo.svg", "alt": "logo"}
            ]}))
            result = subprocess.run([sys.executable, "generate.py", str(source), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('src="../assets/logo.svg"', output.read_text())

    def test_cli_keeps_https_image_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "spec.json", root / "out.html"
            source.write_text(json.dumps({"width": 2, "height": 2, "operations": [
                {"op": "image", "x": 0, "y": 0, "width": 2, "height": 2,
                 "src": "https://example.com/logo.png", "alt": "logo"}
            ]}))
            result = subprocess.run([sys.executable, "generate.py", str(source), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('src="https://example.com/logo.png"', output.read_text())


if __name__ == "__main__":
    unittest.main()
