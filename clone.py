#!/usr/bin/env python3
"""Clone each URL in urls.txt into its own folder as a self-contained index.html via monolith."""
import subprocess
import sys
import re
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).parent
URL_FILE = REPO / "urls.txt"
LOG = REPO / "clone.log"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"

def slug_for(url: str) -> str:
    p = urlparse(url)
    host = p.netloc.replace("www.", "").replace(".com", "").replace(".me", "").replace(".org", "").replace(".shop", "").replace(".co", "").replace(".", "-")
    path_parts = [seg for seg in p.path.split("/") if seg and seg not in ("blogs", "review", "story", "a")]
    tail = "-".join(path_parts) if path_parts else "home"
    tail = re.sub(r"[^a-zA-Z0-9\-_]", "-", tail).strip("-")[:60]
    slug = f"{host}__{tail}" if tail else host
    return slug.lower()

def main():
    urls = [u.strip() for u in URL_FILE.read_text().splitlines() if u.strip()]
    seen = set()
    unique = []
    for u in urls:
        key = u.split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        unique.append(u)

    print(f"Total: {len(urls)} → unique: {len(unique)}")
    LOG.write_text(f"Cloning {len(unique)} URLs\n\n")

    index_rows = []
    for i, url in enumerate(unique, 1):
        slug = slug_for(url)
        folder = REPO / "swipes" / slug
        folder.mkdir(parents=True, exist_ok=True)
        out = folder / "index.html"
        meta = folder / "source.txt"
        meta.write_text(url + "\n")

        print(f"[{i}/{len(unique)}] {slug}")
        try:
            r = subprocess.run(
                ["monolith", "--no-audio", "--no-video", "--quiet",
                 "--user-agent", UA, "--timeout", "45",
                 "--output", str(out), url],
                capture_output=True, text=True, timeout=120
            )
            size = out.stat().st_size if out.exists() else 0
            status = "OK" if r.returncode == 0 and size > 1000 else f"FAIL(rc={r.returncode},size={size})"
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
        except Exception as e:
            status = f"ERR({e})"

        with LOG.open("a") as f:
            f.write(f"[{i}/{len(unique)}] {status}  {slug}  <-  {url}\n")
        index_rows.append((slug, url, status))

    # Write README
    ok = [r for r in index_rows if r[2] == "OK"]
    fail = [r for r in index_rows if r[2] != "OK"]
    readme = ["# Advertorial Swipe File\n",
              "Full-page clones of advertorials. Each folder under `swipes/` contains a self-contained `index.html` (images/CSS embedded) plus `source.txt` with the original URL.\n",
              "\nOpen any `index.html` in a browser to view, or feed it to an AI for analysis.\n",
              f"\n## Index ({len(ok)} successful / {len(fail)} failed)\n"]
    for slug, url, status in index_rows:
        mark = "✅" if status == "OK" else "⚠️"
        readme.append(f"- {mark} [`{slug}`](swipes/{slug}/index.html) — [source]({url})" + (f" _{status}_" if status != "OK" else "") + "\n")
    (REPO / "README.md").write_text("".join(readme))
    print(f"\nDone. {len(ok)} OK, {len(fail)} failed. See {LOG}")

if __name__ == "__main__":
    main()
