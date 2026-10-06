"""Write assets/languages.svg from the hand-set language mix in SHARES.

The shares are Timur's own estimate of the code he writes, including work that is not on GitHub;
they are not measured from repositories. Edit SHARES and rerun to change the card.

Usage: python3 scripts/build_languages_card.py
"""
import pathlib

SHARES = [("TypeScript", 48), ("Python", 23), ("R", 10), ("JavaScript", 7), ("C/C++", 5),
          ("Swift", 4), ("CUDA", 1), ("Rust", 1), ("OCaml", 1)]
COLOURS = ["#70befa", "#a78bfa", "#4f8ff0", "#c4b5fd", "#8fa5fb", "#6d5fe0", "#b9dcfd", "#94a3b8",
           "#5b6fd0"]
WIDTH, HEIGHT = 1200, 132
BAR_X, BAR_WIDTH, GAP = 40, 1120, 4
OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "languages.svg"


def card_svg(shares):
    total = sum(share for _, share in shares)
    usable = BAR_WIDTH - GAP * (len(shares) - 1)
    bar, legend, x, lx = [], [], float(BAR_X), float(BAR_X)
    for (name, share), colour in zip(shares, COLOURS):
        width = usable * share / total
        bar.append(f'<rect x="{x:.1f}" y="60" width="{width:.1f}" height="14" rx="7" fill="{colour}"/>')
        x += width + GAP
        label = f"{name} {share}%"
        legend.append(f'<circle cx="{lx + 6:.1f}" cy="100" r="6" fill="{colour}"/>'
                      f'<text x="{lx + 22:.1f}" y="106" font-size="17" fill="#e6edf3">{name} '
                      f'<tspan fill="#8b949e">{share}%</tspan></text>')
        # Entries are spaced by their text length so nine of them fit on one row.
        lx += 40 + 9 * len(label)
    summary = ", ".join(f"{name} {share}%" for name, share in shares)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" role="img" aria-label="Languages: {summary}">
  <defs>
    <clipPath id="reveal"><rect x="{BAR_X}" y="54" width="{BAR_WIDTH}" height="26">
      <animate attributeName="width" from="0" to="{BAR_WIDTH}" dur="1.6s" fill="freeze" calcMode="spline" keySplines="0.2 0.7 0.2 1" keyTimes="0;1"/>
    </rect></clipPath>
  </defs>
  <rect width="{WIDTH}" height="{HEIGHT}" rx="16" fill="#0a0a0a"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
    <text x="{BAR_X}" y="38" font-size="20" font-weight="600" fill="#70befa">Languages</text>
    <g clip-path="url(#reveal)">{"".join(bar)}</g>
    {"".join(legend)}
  </g>
</svg>
'''


def main():
    if sum(share for _, share in SHARES) != 100:
        raise ValueError("SHARES must add up to 100")
    OUT.write_text(card_svg(SHARES))
    print(f"{OUT.name}: {SHARES}")


if __name__ == "__main__":
    main()
