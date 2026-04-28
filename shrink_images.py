#!/usr/bin/env python3
"""Shrink embedded base64 images in cloned HTML files so each file stays under GitHub's 100MB limit.

Re-encodes data:image/{png,jpeg,webp} URIs above MIN_BYTES as JPEG quality QUALITY,
optionally downscaling if the longest side exceeds MAX_DIM.
"""
import base64, io, re, sys
from pathlib import Path
from PIL import Image

MIN_BYTES = 50_000      # only touch images that decode to >=50KB raw base64 chunk
MAX_DIM = 1600          # downscale if longest side > this
QUALITY = 75            # JPEG quality

DATA_URI = re.compile(rb"data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=]+)")

def shrink_html(path: Path) -> tuple[int, int, int]:
    raw = path.read_bytes()
    before = len(raw)
    replaced = 0

    def repl(m):
        nonlocal replaced
        ext = m.group(1).decode()
        b64 = m.group(2)
        if len(b64) < MIN_BYTES * 4 // 3:  # skip small ones
            return m.group(0)
        try:
            data = base64.b64decode(b64)
            if len(data) < MIN_BYTES:
                return m.group(0)
            img = Image.open(io.BytesIO(data))
            # Convert palette/RGBA to RGB for JPEG
            if img.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Downscale if oversize
            w, h = img.size
            if max(w, h) > MAX_DIM:
                scale = MAX_DIM / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

            out = io.BytesIO()
            img.save(out, format="JPEG", quality=QUALITY, optimize=True, progressive=True)
            new_b64 = base64.b64encode(out.getvalue())
            # Only replace if we actually saved bytes
            if len(new_b64) < len(b64):
                replaced += 1
                return b"data:image/jpeg;base64," + new_b64
        except Exception:
            pass
        return m.group(0)

    new = DATA_URI.sub(repl, raw)
    after = len(new)
    if after < before:
        path.write_bytes(new)
    return before, after, replaced

if __name__ == "__main__":
    paths = [Path(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else \
            sorted(Path("swipes").glob("*/index.html"))
    for p in paths:
        before, after, n = shrink_html(p)
        mb_b, mb_a = before / 1024 / 1024, after / 1024 / 1024
        savings = (1 - after / before) * 100 if before else 0
        print(f"{p.parent.name:60s}  {mb_b:6.1f}MB → {mb_a:6.1f}MB  ({savings:+5.1f}%)  imgs={n}")
