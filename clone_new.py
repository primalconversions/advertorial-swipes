#!/usr/bin/env python3
"""Clone only URLs from urls.txt that don't already have a valid index.html.

Skips already-cloned swipes so post-processing (shrink_images.py, scrub_secrets.py)
isn't undone by re-cloning.
"""
import subprocess, re
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).parent
URL_FILE = REPO / "urls.txt"
LOG = REPO / "clone.log"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/605.1.15"

def slug_for(url):
    p = urlparse(url)
    host = p.netloc
    if host.startswith('www.'): host = host[4:]
    host = re.sub(r'\.(com|me|org|shop|co|net|io|store|app)$', '', host)
    host = host.replace('.', '-')
    path_parts = [seg for seg in p.path.split("/") if seg and seg not in ("blogs", "review", "story", "a")]
    tail = "-".join(path_parts) if path_parts else "home"
    tail = re.sub(r"[^a-zA-Z0-9\-_]", "-", tail).strip("-")[:60]
    return f"{host}__{tail}".lower() if tail else host.lower()

urls = [u.strip() for u in URL_FILE.read_text().splitlines() if u.strip()]
seen, unique = set(), []
for u in urls:
    k = u.split("?")[0]
    if k not in seen:
        seen.add(k); unique.append(u)

todo = []
for url in unique:
    f = REPO / "swipes" / slug_for(url) / "index.html"
    if not (f.exists() and f.stat().st_size > 1000):
        todo.append(url)

print(f"Total: {len(unique)} | already cloned: {len(unique)-len(todo)} | to clone: {len(todo)}\n")
if not todo:
    print("Nothing to do."); raise SystemExit(0)

with LOG.open("a") as f:
    f.write(f"\n--- Incremental clone of {len(todo)} new URLs ---\n")

for i, url in enumerate(todo, 1):
    slug = slug_for(url)
    folder = REPO / "swipes" / slug
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / "index.html"
    (folder / "source.txt").write_text(url + "\n")
    try:
        r = subprocess.run(
            ["monolith", "--no-audio", "--no-video", "--quiet",
             "--user-agent", UA, "--timeout", "60",
             "--output", str(out), url],
            capture_output=True, text=True, timeout=150
        )
        size = out.stat().st_size if out.exists() else 0
        status = "OK" if r.returncode == 0 and size > 1000 else f"FAIL(rc={r.returncode},size={size})"
    except subprocess.TimeoutExpired:
        status = "TIMEOUT"
    except Exception as e:
        status = f"ERR({e})"
    print(f"[{i}/{len(todo)}] {status}  {slug}")
    with LOG.open("a") as f:
        f.write(f"[{i}/{len(todo)}] {status}  {slug}  <-  {url}\n")
