"""Write assets/languages.svg: share of owned repositories by primary language.

Counted per repository rather than per byte, because byte counts are dominated by bundled and
generated files. Private repositories are included, so this needs the owner's own token and is run
by hand; the daily workflow's token only sees public repositories.

Usage: GITHUB_TOKEN=$(gh auth token) python3 scripts/build_languages_card.py
"""
import collections
import json
import os
import pathlib
import urllib.request

QUERY = """query($cursor: String) {
  viewer {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes { primaryLanguage { name } }
    }
  }
}"""
COLOURS = ["#70befa", "#a78bfa", "#4f8ff0", "#c4b5fd", "#8fa5fb", "#6d5fe0", "#b9dcfd", "#94a3b8"]
BAR_X, BAR_WIDTH, GAP = 32, 431, 3
OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "languages.svg"


def fetch_primary_languages(token):
    languages, cursor = [], None
    while True:
        request = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": QUERY, "variables": {"cursor": cursor}}).encode(),
            headers={"Authorization": f"bearer {token}", "User-Agent": "profile-languages-card"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
        if payload.get("errors"):
            raise RuntimeError(f"GitHub API error: {payload['errors']}")
        page = payload["data"]["viewer"]["repositories"]
        languages += [node["primaryLanguage"]["name"] for node in page["nodes"] if node["primaryLanguage"]]
        if not page["pageInfo"]["hasNextPage"]:
            return languages
        cursor = page["pageInfo"]["endCursor"]


def card_svg(languages):
    ranked = collections.Counter(languages).most_common(len(COLOURS))
    total = len(languages)
    usable = BAR_WIDTH - GAP * (len(ranked) - 1)
    bar, legend, x = [], [], float(BAR_X)
    for i, ((name, count), colour) in enumerate(zip(ranked, COLOURS)):
        width = usable * count / sum(n for _, n in ranked)
        bar.append(f'<rect x="{x:.1f}" y="62" width="{width:.1f}" height="12" rx="6" fill="{colour}"/>')
        x += width + GAP
        lx, ly = (32, 247.5)[i % 2], 104 + 26 * (i // 2)
        legend.append(f'<circle cx="{lx + 5}" cy="{ly - 5}" r="5" fill="{colour}"/>'
                      f'<text x="{lx + 20}" y="{ly}" font-size="14" fill="#e6edf3">{name}</text>'
                      f'<text x="{lx + 190}" y="{ly}" font-size="14" text-anchor="end" fill="#8b949e">'
                      f'{100 * count / total:.0f}%</text>')
    height = 104 + 26 * ((len(ranked) + 1) // 2)
    summary = ", ".join(f"{name} {100 * count / total:.0f}%" for name, count in ranked)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 495 {height}" width="495" height="{height}" role="img" aria-label="Primary language across {total} repositories: {summary}">
  <defs>
    <clipPath id="reveal"><rect x="{BAR_X}" y="56" width="{BAR_WIDTH}" height="24">
      <animate attributeName="width" from="0" to="{BAR_WIDTH}" dur="1.6s" fill="freeze" calcMode="spline" keySplines="0.2 0.7 0.2 1" keyTimes="0;1"/>
    </rect></clipPath>
  </defs>
  <rect width="495" height="{height}" rx="10" fill="#0a0a0a"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif">
    <text x="32" y="38" font-size="16" font-weight="600" fill="#70befa">Languages</text>
    <text x="463" y="38" font-size="12" text-anchor="end" fill="#8b949e">primary language across {total} repositories</text>
    <g clip-path="url(#reveal)">{"".join(bar)}</g>
    {"".join(legend)}
  </g>
</svg>
'''


def main():
    languages = fetch_primary_languages(os.environ["GITHUB_TOKEN"])
    OUT.write_text(card_svg(languages))
    print(f"{OUT.name}: {collections.Counter(languages).most_common()}")


if __name__ == "__main__":
    main()
