#!/usr/bin/env python3
"""Generates assets/card-dark.svg and assets/card-light.svg from the GitHub API (needs GITHUB_TOKEN)."""
import html
import json
import os
import urllib.request
from datetime import datetime, timezone

USER = "qateralong"
OUT = os.path.dirname(os.path.abspath(__file__))
W, H = 1200, 244
SKIP_LANGS = {"G-code", "Makefile", "Dockerfile", "Batchfile", "Inno Setup"}  # not really languages
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    contributionsCollection { contributionCalendar { totalContributions } restrictedContributionsCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
      totalCount
      nodes {
        name
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
        releases(first: 1, orderBy: {field: CREATED_AT, direction: DESC}) { nodes { tagName publishedAt } }
      }
    }
  }
}"""


def fetch():
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
                                 headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"],
                                          "User-Agent": USER + "-profile"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]


def stats(u):
    cal = u["contributionsCollection"]
    langs, release = {}, None
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            if name in SKIP_LANGS:
                continue
            size, color = langs.get(name, (0, e["node"]["color"] or "#8b949e"))
            langs[name] = (size + e["size"], color)
        for rel in repo["releases"]["nodes"]:
            if rel["publishedAt"] and (not release or rel["publishedAt"] > release[2]):
                release = (repo["name"], rel["tagName"], rel["publishedAt"])
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]
    total = sum(s for _, (s, _) in top) or 1
    return {
        "contrib": cal["contributionCalendar"]["totalContributions"] + cal["restrictedContributionsCount"],
        "repos": u["repositories"]["totalCount"],
        "langs": [(n, s / total, c) for n, (s, c) in top],
        "release": release,
        "since": u["createdAt"][:4],
    }


def svg(st, dark):
    bg, fg, dim, line = ("#0b0d12", "#eceef4", "#868c9c", "#ffffff14") if dark else ("#f7f8fa", "#14161c", "#5b6170", "#0000001a")
    a1 = "#7dd3c0" if dark else "#1f9e86"
    e = html.escape
    year = datetime.now(timezone.utc).year

    def block(x, label, value, sub=""):
        return (f'<text x="{x}" y="70" class="lb">{e(label)}</text>'
                f'<text x="{x}" y="122" class="big">{e(value)}</text>'
                + (f'<text x="{x}" y="150" class="lb">{e(sub)}</text>' if sub else ""))

    parts = [block(48, f"~/contributions · {year}", str(st["contrib"])),
             block(330, "~/public repos", str(st["repos"]))]
    parts.append(block(950, "~/on github since", st["since"]))
    if st["release"]:
        repo, tag, at = st["release"]
        d = datetime.fromisoformat(at.replace("Z", "+00:00"))
        parts.append(block(560, "~/latest release", f"{repo} {tag}", f"{d.day} {MONTHS[d.month - 1]} {d.year}"))

    # language bar across the bottom
    x, bar = 48, []
    width = W - 96
    for i, (name, share, color) in enumerate(st["langs"]):
        w = max(width * share - 3, 2)
        bar.append(f'<rect x="{x:.1f}" y="176" width="{w:.1f}" height="8" rx="4" fill="{color}"/>')
        x += width * share
    legend, lx = [], 48
    for name, share, color in st["langs"]:
        label = f"{name} {share * 100:.0f}%"
        legend.append(f'<circle cx="{lx + 5}" cy="212" r="5" fill="{color}"/><text x="{lx + 17}" y="218" class="lg">{e(label)}</text>')
        lx += 17 + len(label) * 10.8 + 30

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="GitHub activity">
<style>
text{{font-family:ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,"Liberation Mono",monospace}}
.lb{{font-size:17px;fill:{dim}}} .big{{font-size:44px;font-weight:800;fill:{fg};letter-spacing:-1px}} .lg{{font-size:18px;fill:{dim}}}
</style>
<rect width="{W}" height="{H}" rx="18" fill="{bg}"/>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{line}"/>
<path d="M300 44 V150 M530 44 V150 M920 44 V150" stroke="{line}"/>
<g>{"".join(parts)}</g>
<g>{"".join(bar)}</g>
<g>{"".join(legend)}</g>
</svg>
'''


def main():
    st = stats(fetch())
    for dark in (True, False):
        name = "card-dark.svg" if dark else "card-light.svg"
        with open(os.path.join(OUT, name), "w") as fh:
            fh.write(svg(st, dark))
    print(json.dumps({k: v for k, v in st.items() if k != "langs"}), [n for n, _, _ in st["langs"]])


if __name__ == "__main__":
    main()
