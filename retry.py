#!/usr/bin/env python3
"""Retry URLs that failed on the first pass."""
import subprocess, re
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).parent
LOG = REPO / "clone.log"
RETRY_LOG = REPO / "retry.log"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/605.1.15"

def slug_for(url: str) -> str:
    p = urlparse(url)
    host = p.netloc.replace("www.", "").replace(".com", "").replace(".me", "").replace(".org", "").replace(".shop", "").replace(".co", "").replace(".", "-")
    path_parts = [seg for seg in p.path.split("/") if seg and seg not in ("blogs", "review", "story", "a")]
    tail = "-".join(path_parts) if path_parts else "home"
    tail = re.sub(r"[^a-zA-Z0-9\-_]", "-", tail).strip("-")[:60]
    return f"{host}__{tail}".lower() if tail else host.lower()

# Parse failed URLs from clone.log
failed = []
for line in LOG.read_text().splitlines():
    if "FAIL" in line or "TIMEOUT" in line or "ERR" in line:
        m = re.search(r"<-\s+(https?://\S+)", line)
        if m:
            failed.append(m.group(1))

print(f"Retrying {len(failed)} failed URLs\n")
RETRY_LOG.write_text(f"Retry of {len(failed)} URLs\n\n")

# Oversized file — use a shrunken variant
OVERSIZED = "https://blog.well-being-review.com/lost-23-ibs-in-one-month"

results = []
for i, url in enumerate(failed, 1):
    slug = slug_for(url)
    folder = REPO / "swipes" / slug
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / "index.html"

    cmd = ["monolith", "--no-audio", "--no-video", "--quiet",
           "--user-agent", UA, "--timeout", "60",
           "--output", str(out), url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=150)
        size = out.stat().st_size if out.exists() else 0
        status = "OK" if r.returncode == 0 and size > 1000 else f"FAIL(rc={r.returncode},size={size})"
        if r.stderr and status != "OK":
            status += f" | {r.stderr.strip()[:80]}"
    except subprocess.TimeoutExpired:
        status = "TIMEOUT"
    except Exception as e:
        status = f"ERR({e})"

    print(f"[{i}/{len(failed)}] {status}  {slug}")
    with RETRY_LOG.open("a") as f:
        f.write(f"[{i}/{len(failed)}] {status}  {slug}  <-  {url}\n")
    results.append((slug, url, status))

# Re-clone the oversized file with --no-fonts --no-js to shrink
print("\nRe-cloning oversized file without fonts/js...")
slug = slug_for(OVERSIZED)
out = REPO / "swipes" / slug / "index.html"
r = subprocess.run(
    ["monolith", "--no-audio", "--no-video", "--no-fonts", "--no-js", "--quiet",
     "--user-agent", UA, "--timeout", "60", "--output", str(out), OVERSIZED],
    capture_output=True, text=True, timeout=150
)
size = out.stat().st_size if out.exists() else 0
print(f"Oversized: rc={r.returncode}, size={size/1024/1024:.1f}MB")
with RETRY_LOG.open("a") as f:
    f.write(f"\nOVERSIZED re-clone: rc={r.returncode} size={size} MB={size/1024/1024:.1f}\n")

ok = sum(1 for _,_,s in results if s == "OK")
print(f"\nRetry done. {ok}/{len(failed)} recovered.")
