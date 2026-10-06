"""Write the activity card: contributions, active days and longest streak over the last year.

Every number comes from the contribution calendar, the one activity source that includes private
work when the profile shares it; the ring fills to the share of days with a contribution.

Usage: GITHUB_TOKEN=... python3 scripts/build_activity_card.py <login> <out.svg>
"""
import json
import math
import os
import pathlib
import sys
import urllib.request

QUERY = """query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount } }
      }
    }
  }
}"""
RING_RADIUS = 46


def fetch_daily_counts(login, token):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-activity-card"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(f"GitHub API error: {payload['errors']}")
    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    counts = [day["contributionCount"] for week in calendar["weeks"] for day in week["contributionDays"]]
    return calendar["totalContributions"], counts


def longest_streak(counts):
    best = run = 0
    for count in counts:
        run = run + 1 if count else 0
        best = max(best, run)
    return best


def card_svg(total, counts):
    active = sum(1 for count in counts if count)
    circumference = 2 * math.pi * RING_RADIUS
    filled = circumference * active / len(counts)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 495 195" width="495" height="195" role="img" aria-label="{total:,} contributions in the last year; active on {active} of {len(counts)} days; longest streak {longest_streak(counts)} days">
  <defs>
    <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#70befa"/>
      <stop offset="1" stop-color="#a78bfa"/>
    </linearGradient>
  </defs>
  <rect width="495" height="195" rx="10" fill="#0a0a0a"/>
  <g stroke="#30363d"><line x1="165" y1="34" x2="165" y2="161"/><line x1="330" y1="34" x2="330" y2="161"/></g>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" text-anchor="middle">
    <text x="82.5" y="88" font-size="30" font-weight="700" fill="#ffffff">{active}</text>
    <text x="82.5" y="116" font-size="14" fill="#70befa">Active days</text>
    <text x="82.5" y="137" font-size="12" fill="#8b949e">of the last {len(counts)}</text>

    <circle cx="247.5" cy="78" r="{RING_RADIUS}" fill="none" stroke="#1c2330" stroke-width="6"/>
    <circle cx="247.5" cy="78" r="{RING_RADIUS}" fill="none" stroke="url(#ring)" stroke-width="6" stroke-linecap="round" transform="rotate(-90 247.5 78)" stroke-dasharray="{filled:.1f} {circumference:.1f}">
      <animate attributeName="stroke-dasharray" from="0 {circumference:.1f}" to="{filled:.1f} {circumference:.1f}" dur="1.8s" fill="freeze" calcMode="spline" keySplines="0.2 0.7 0.2 1" keyTimes="0;1"/>
    </circle>
    <text x="247.5" y="87" font-size="25" font-weight="700" fill="#ffffff">{total:,}</text>
    <text x="247.5" y="152" font-size="14" font-weight="600" fill="#a78bfa">Contributions</text>
    <text x="247.5" y="171" font-size="12" fill="#8b949e">in the last year</text>

    <text x="412.5" y="88" font-size="30" font-weight="700" fill="#ffffff">{longest_streak(counts)}</text>
    <text x="412.5" y="116" font-size="14" fill="#70befa">Longest streak</text>
    <text x="412.5" y="137" font-size="12" fill="#8b949e">days in a row</text>
  </g>
</svg>
'''


def main():
    login, out = sys.argv[1], pathlib.Path(sys.argv[2])
    total, counts = fetch_daily_counts(login, os.environ["GITHUB_TOKEN"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(card_svg(total, counts))
    print(f"{out}: {total} contributions over {len(counts)} days")


if __name__ == "__main__":
    main()
