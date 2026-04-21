#!/usr/bin/env python3
"""Build the final README and remove empty folders for dead URLs."""
import re, shutil
from pathlib import Path
from urllib.parse import quote

REPO = Path(__file__).parent
URLS = [u.strip() for u in (REPO / "urls.txt").read_text().splitlines() if u.strip()]

def slug_for(url):
    from urllib.parse import urlparse
    p = urlparse(url)
    host = p.netloc.replace("www.", "").replace(".com", "").replace(".me", "").replace(".org", "").replace(".shop", "").replace(".co", "").replace(".", "-")
    path_parts = [seg for seg in p.path.split("/") if seg and seg not in ("blogs", "review", "story", "a")]
    tail = "-".join(path_parts) if path_parts else "home"
    tail = re.sub(r"[^a-zA-Z0-9\-_]", "-", tail).strip("-")[:60]
    return f"{host}__{tail}".lower() if tail else host.lower()

# Dedupe preserving order
seen, unique = set(), []
for u in URLS:
    key = u.split("?")[0]
    if key not in seen:
        seen.add(key); unique.append(u)

alive, dead = [], []
for url in unique:
    slug = slug_for(url)
    f = REPO / "swipes" / slug / "index.html"
    if f.exists() and f.stat().st_size > 1000:
        alive.append((slug, url, f.stat().st_size))
    else:
        dead.append((slug, url))
        # Remove empty folder so repo stays clean
        folder = REPO / "swipes" / slug
        if folder.exists() and not any(p.stat().st_size > 1000 for p in folder.glob("index.html")):
            shutil.rmtree(folder, ignore_errors=True)

PAGES = "https://primalconversions.github.io/advertorial-swipes"

lines = [
    "# Advertorial Swipe File\n\n",
    f"Full-page clones of {len(alive)} advertorials + {len(dead)} dead links for reference when writing new advertorials for clients.\n\n",
    f"**Live site:** {PAGES}/\n\n",
    "## How to use\n\n",
    "Each folder under `swipes/` contains:\n",
    "- `index.html` — self-contained page (HTML + CSS + images embedded via `monolith`). Click the **view** link below to see it rendered via GitHub Pages, or feed the raw file to an AI for analysis.\n",
    "- `source.txt` — the original URL.\n\n",
    "Paste the raw `index.html` content (or a link to it) into a Claude conversation when drafting a new advertorial — the AI can reference hook structure, pacing, proof elements, CTAs, and visual layout.\n\n",
    "## Regenerating / adding new swipes\n\n",
    "```bash\n",
    "brew install monolith\n",
    "# Add URLs to urls.txt, then:\n",
    "python3 clone.py\n",
    "python3 build_readme.py\n",
    "```\n\n",
    f"## Live swipes ({len(alive)})\n\n",
    "Click **view** to open the rendered page, **raw** to download the file, or **source** to open the original URL.\n\n",
]
for slug, url, size in alive:
    mb = size / 1024 / 1024
    enc = quote(slug, safe="_-")
    view = f"{PAGES}/swipes/{enc}/index.html"
    raw = f"https://raw.githubusercontent.com/primalconversions/advertorial-swipes/main/swipes/{enc}/index.html"
    lines.append(f"- `{slug}` ({mb:.1f} MB) — [view]({view}) · [raw]({raw}) · [source]({url})\n")

if dead:
    lines.append(f"\n## Dead links ({len(dead)})\n\n")
    lines.append("Source advertorials no longer exist (404). Try the Wayback Machine link for each — many advertorials are archived there.\n\n")
    for slug, url in dead:
        wayback = f"https://web.archive.org/web/*/{url}"
        lines.append(f"- `{slug}` — [source (404)]({url}) · [wayback]({wayback})\n")

(REPO / "README.md").write_text("".join(lines))
print(f"README written: {len(alive)} alive, {len(dead)} dead")
