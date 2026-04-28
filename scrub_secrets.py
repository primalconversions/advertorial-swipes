#!/usr/bin/env python3
"""Scrub embedded secrets (FB access tokens, etc.) from cloned HTML pages.

These tokens are already public on the source page, but GitHub's push protection
blocks them and they shouldn't live in our repo regardless.
"""
import re
from pathlib import Path

PATTERNS = [
    # Facebook Graph API access token: EAA + 60-250 base64-ish chars in a string literal
    (re.compile(rb'(["\'])(EAA[A-Za-z0-9_-]{60,300})(["\'])'), rb'\1REDACTED_FB_TOKEN\3'),
    # Generic Bearer / sk-... API keys in obvious string contexts
    (re.compile(rb'(["\'])(sk-[A-Za-z0-9]{20,})(["\'])'), rb'\1REDACTED_API_KEY\3'),
    (re.compile(rb'(["\'])(AIza[A-Za-z0-9_-]{30,})(["\'])'), rb'\1REDACTED_GOOGLE_KEY\3'),
]

total = 0
for p in sorted(Path("swipes").glob("*/index.html")):
    raw = p.read_bytes()
    new = raw
    hits = 0
    for pat, repl in PATTERNS:
        new, n = pat.subn(repl, new)
        hits += n
    if hits:
        p.write_bytes(new)
        print(f"{p.parent.name:60s}  redacted {hits} secret(s)")
        total += hits

print(f"\nTotal redactions: {total}")
