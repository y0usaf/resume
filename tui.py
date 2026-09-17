"""A tiny fixed-cell drawing surface for static HTML terminal graphics."""

from dataclasses import dataclass
from html import escape
import unicodedata
from urllib.parse import urlparse


_GLYPHS = {
    0: " ", 1: "╵", 2: "╶", 3: "└", 4: "╷", 5: "│", 6: "┌",
    7: "├", 8: "╴", 9: "┘", 10: "─", 11: "┴", 12: "┐", 13: "┤",
    14: "┬", 15: "┼",
}


@dataclass
class _Cell:
    char: str = ""
    style: str = ""
    connections: int = 0
    reservation: object = None


@dataclass
class _Reservation:
    kind: str
    x: int
    y: int
    width: int
    height: int
    value: object


class Grid:
    """A bounded, zero-based, fixed-width grid.

    Drawing methods raise ``ValueError`` for anything that cannot be represented
    without clipping. ``render`` returns HTML for a ``<pre class="terminal">``
    surface; ``plain`` returns the same drawing as text.
    """

    def __init__(self, width: int, height: int):
        if isinstance(width, bool) or not isinstance(width, int) or width < 1:
            raise ValueError("width must be a positive integer")
        if isinstance(height, bool) or not isinstance(height, int) or height < 1:
            raise ValueError("height must be a positive integer")
        self.width = width
        self.height = height
        self._cells = [[_Cell() for _ in range(width)] for _ in range(height)]

    def _point(self, x: int, y: int) -> None:
        if isinstance(x, bool) or not isinstance(x, int) or isinstance(y, bool) or not isinstance(y, int):
            raise ValueError("coordinates must be integers")
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise ValueError(f"coordinate ({x}, {y}) is outside {self.width}×{self.height} grid")

    def _style(self, style: str) -> str:
        if not isinstance(style, str):
            raise ValueError("style must be a string")
        return style

    @staticmethod
    def _cell_text(value: str) -> None:
        for character in value:
            category = unicodedata.category(character)
            if category.startswith("C") or category.startswith("M"):
                raise ValueError(f"unsupported control or zero-width character: {character!r}")
            if unicodedata.east_asian_width(character) in ("W", "F"):
                raise ValueError(f"unsupported multi-cell character: {character!r}")

    def text(self, x: int, y: int, text: str, style: str = "", scale: int = 1) -> "Grid":
        """Place text; it covers a connection glyph while retaining its edges."""
        self._point(x, y)
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        self._cell_text(text)
        self._style(style)
        if isinstance(scale, bool) or not isinstance(scale, int) or scale < 1:
            raise ValueError("scale must be a positive integer")
        if not text:
            return self
        if x + len(text) * scale > self.width or y + scale > self.height:
            raise ValueError("text extends beyond the grid")
        if scale > 1 and text:
            reservation = _Reservation("text", x, y, len(text) * scale, scale, text)
            cells = self._rectangle(reservation)
            if any(cell.char or cell.connections or cell.reservation for cell in cells):
                raise ValueError("text overlaps existing content")
            for cell in cells:
                cell.reservation = reservation
        elif scale == 1 and any(self._cells[y][x + offset].reservation for offset in range(len(text))):
            raise ValueError("text overlaps existing content")
        for offset, character in enumerate(text):
            cell = self._cells[y][x + offset * scale]
            cell.char = character
            cell.style = style
        return self

    def image(self, x: int, y: int, width: int, height: int, src: str, alt: str = "") -> "Grid":
        """Reserve a rectangle and place an image anchored at its top-left cell."""
        self._point(x, y)
        if isinstance(width, bool) or not isinstance(width, int) or width < 1:
            raise ValueError("image width must be a positive integer")
        if isinstance(height, bool) or not isinstance(height, int) or height < 1:
            raise ValueError("image height must be a positive integer")
        if x + width > self.width or y + height > self.height:
            raise ValueError("image extends beyond the grid")
        if not isinstance(src, str) or not src or any(ord(character) < 32 or ord(character) == 127 for character in src):
            raise ValueError("image src must be a safe relative path or HTTPS URL")
        parsed = urlparse(src)
        if parsed.scheme:
            if parsed.scheme.lower() != "https" or not parsed.netloc:
                raise ValueError("image src must be a safe relative path or HTTPS URL")
        elif src.startswith("//"):
            raise ValueError("image src must be a safe relative path or HTTPS URL")
        if not isinstance(alt, str):
            raise ValueError("image alt must be a string")
        reservation = _Reservation("image", x, y, width, height, (src, alt))
        cells = self._rectangle(reservation)
        if any(cell.char or cell.connections or cell.reservation for cell in cells):
            raise ValueError("image overlaps existing content")
        for cell in cells:
            cell.reservation = reservation
        return self

    def _rectangle(self, reservation: _Reservation):
        return [
            self._cells[row][column]
            for row in range(reservation.y, reservation.y + reservation.height)
            for column in range(reservation.x, reservation.x + reservation.width)
        ]

    def _assert_drawable(self, coordinates) -> None:
        if any(self._cells[y][x].reservation for x, y in coordinates):
            raise ValueError("drawing overlaps reserved content")

    def _connect(self, x: int, y: int, mask: int, style: str = "") -> None:
        self._point(x, y)
        cell = self._cells[y][x]
        cell.connections |= mask
        if style and not cell.char:
            cell.style = style

    def line(self, x1: int, y1: int, x2: int, y2: int, style: str = "") -> "Grid":
        self._point(x1, y1)
        self._point(x2, y2)
        self._style(style)
        if x1 != x2 and y1 != y2:
            raise ValueError("line endpoints must share an x or y coordinate")
        if x1 == x2:
            low, high = sorted((y1, y2))
            coordinates = [(x1, y) for y in range(low, high + 1)]
        else:
            low, high = sorted((x1, x2))
            coordinates = [(x, y1) for x in range(low, high + 1)]
        self._assert_drawable(coordinates)
        if x1 == x2:
            for y in range(low, high + 1):
                mask = (1 if y > low else 0) | (4 if y < high else 0)
                self._connect(x1, y, mask, style)
        else:
            for x in range(low, high + 1):
                mask = (8 if x > low else 0) | (2 if x < high else 0)
                self._connect(x, y1, mask, style)
        return self

    def box(self, x: int, y: int, width: int, height: int, title: str | None = None, style: str = "") -> "Grid":
        if isinstance(width, bool) or not isinstance(width, int) or isinstance(height, bool) or not isinstance(height, int):
            raise ValueError("box width and height must be integers")
        if width < 2 or height < 2:
            raise ValueError("box width and height must be at least 2")
        self._point(x, y)
        self._point(x + width - 1, y + height - 1)
        self._style(style)
        if title is not None:
            if not isinstance(title, str):
                raise ValueError("title must be a string or None")
            self._cell_text(title)
            if len(title) > width - 4:
                raise ValueError("box title does not fit without clipping")
        perimeter = (
            [(column, y) for column in range(x, x + width)]
            + [(column, y + height - 1) for column in range(x, x + width)]
            + [(x, row) for row in range(y + 1, y + height - 1)]
            + [(x + width - 1, row) for row in range(y + 1, y + height - 1)]
        )
        self._assert_drawable(perimeter)
        self.line(x, y, x + width - 1, y, style)
        self.line(x, y + height - 1, x + width - 1, y + height - 1, style)
        self.line(x, y, x, y + height - 1, style)
        self.line(x + width - 1, y, x + width - 1, y + height - 1, style)
        if title:
            self.text(x + 2, y, title, style)
        return self

    def _rows(self):
        for row in self._cells:
            yield [cell.char or _GLYPHS[cell.connections] for cell in row]

    def plain(self) -> str:
        rows = []
        for y, row in enumerate(self._rows()):
            output = []
            x = 0
            while x < self.width:
                character = row[x]
                reservation = self._cells[y][x].reservation
                if reservation and reservation.kind == "text" and y == reservation.y and x == reservation.x:
                    output.extend(str(reservation.value))
                    output.extend(" " * (reservation.width - len(str(reservation.value))))
                    x += reservation.width
                    continue
                elif reservation and reservation.kind == "text":
                    output.append(" ")
                elif reservation and reservation.kind == "image":
                    output.append(" ")
                else:
                    output.append(character)
                x += 1
            rows.append("".join(output))
        return "\n".join(rows)

    def render(self) -> str:
        rendered = []
        for y, row in enumerate(self._rows()):
            cells = []
            x = 0
            while x < self.width:
                character = row[x]
                reservation = self._cells[y][x].reservation
                if reservation and reservation.kind == "image" and x == reservation.x and y == reservation.y:
                    src, alt = reservation.value
                    classes = "terminal-image"
                    cells.append(
                        f'<img class="{classes}" style="--terminal-span-x:{reservation.width};--terminal-span-y:{reservation.height}" src="{escape(src, quote=True)}" alt="{escape(alt, quote=True)}">'
                    )
                    x += reservation.width
                    continue
                if reservation and reservation.kind == "text" and y == reservation.y and x == reservation.x:
                    style = self._cells[y][x].style
                    for glyph in str(reservation.value):
                        classes = f"terminal-cell terminal-scaled-glyph {style}" if style else "terminal-cell terminal-scaled-glyph"
                        cells.append(f'<span class="{escape(classes, quote=True)}" style="--terminal-scale:{reservation.height};grid-column:span {reservation.height}">{escape(glyph)}</span>')
                    x = reservation.x + reservation.width
                    continue
                style = self._cells[y][x].style
                classes = f"terminal-cell {style}" if style else "terminal-cell"
                cells.append(
                    f'<span class="{escape(classes, quote=True)}">{escape(character)}</span>'
                )
                x += 1
            rendered.append(f'<span class="terminal-row">{"".join(cells)}</span>')
        return "\n".join(rendered)
