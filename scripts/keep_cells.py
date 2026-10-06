"""Make the Platane/snk snake walk the contribution grid without eating it.

snk fades every cell to empty as the snake passes and grows a bar of eaten cells under the grid.
This strips both from the generated SVG and colours the snake's segments blue to violet.

Usage: python3 scripts/keep_cells.py dist/snake.svg [more.svg ...]
"""
import pathlib
import re
import sys

BLUE, VIOLET = (0x70, 0xBE, 0xFA), (0xA7, 0x8B, 0xFA)
KEYFRAMES = r"@keyframes {name}[0-9a-z]+\{{(?:[^{{}}]*\{{[^{{}}]*\}})*\}}"


def keep_cells(svg):
    svg, cells = re.subn(r"(\.c\.c[0-9a-z]+\{[^}]*?);animation-name:c[0-9a-z]+\}", r"\1}", svg)
    svg, bar = re.subn(r'<rect class="u [^>]*/>', "", svg)
    # Fail instead of publishing an eating snake if snk ever changes its markup.
    if not cells or not bar:
        raise ValueError(f"unexpected snk markup: {cells} cell animations, {bar} bar segments found")
    for name in ("c", "u"):
        svg = re.sub(KEYFRAMES.format(name=name), "", svg)
    svg = re.sub(r"\.u(\.u[0-9a-z]+)?\{[^}]*\}", "", svg)
    return svg, cells


def colour_snake(svg):
    segments = sorted(set(re.findall(r'class="s (s[0-9a-z]+)"', svg)))
    if not segments:
        raise ValueError("unexpected snk markup: no snake segments found")
    rules = []
    for i, segment in enumerate(segments):
        t = i / max(len(segments) - 1, 1)
        colour = "".join(f"{round(a + (b - a) * t):02x}" for a, b in zip(BLUE, VIOLET))
        rules.append(f".s.{segment}{{fill:#{colour}}}")
    return svg.replace("</style>", "".join(rules) + "</style>", 1)


def main():
    for name in sys.argv[1:]:
        path = pathlib.Path(name)
        svg, cells = keep_cells(path.read_text())
        path.write_text(colour_snake(svg))
        print(f"{path}: kept {cells} cells lit")


if __name__ == "__main__":
    main()
