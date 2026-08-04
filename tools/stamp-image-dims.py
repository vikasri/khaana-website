#!/usr/bin/env python3
"""Give every <img> its real pixel dimensions.

    python3 tools/stamp-image-dims.py

An <img> with no width and height has no intrinsic size until the file itself
arrives, so the browser lays the page out around a zero-height box and then
shoves everything down when the picture loads. On a recipe page that is the
whole method jumping under the reader's thumb, on a slow connection twice. It
is the single largest source of layout shift on this site: 1,365 images across
681 pages had no dimensions at all.

Setting width and height attributes gives the browser the aspect ratio up
front, so it reserves the right space before the bytes arrive. The attributes
are not a display size — every one of these images is sized by CSS, and CSS
wins. They exist only to state the shape.

Run late, after the page generators, before version-assets.py. Idempotent: an
existing width/height is replaced rather than duplicated, so re-running after
swapping a photograph corrects it.
"""
import glob, os, re, sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
SRC = re.compile(r'\bsrc="([^"]+)"')
DIM = re.compile(r'\s(?:width|height)="\d+"')

_size = {}


def svg_size(path):
    """An SVG has no pixels, but it has a viewBox, which is the same ratio."""
    head = open(path, encoding="utf-8", errors="replace").read(2000)
    m = re.search(r'viewBox\s*=\s*"[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)"', head)
    if m:
        return int(round(float(m.group(1)))), int(round(float(m.group(2))))
    w = re.search(r'\bwidth\s*=\s*"(\d+)', head)
    h = re.search(r'\bheight\s*=\s*"(\d+)', head)
    return (int(w.group(1)), int(h.group(1))) if w and h else None


def size_of(path):
    if path not in _size:
        try:
            if path.lower().endswith(".svg"):
                _size[path] = svg_size(path)
            else:
                with Image.open(path) as im:
                    _size[path] = im.size
        except Exception:
            _size[path] = None
    return _size[path]


def resolve(src, page_rel):
    if src.startswith(("http://", "https://", "data:", "//")):
        return None
    p = os.path.normpath(os.path.join(os.path.dirname(page_rel), src.split("?")[0]))
    full = os.path.join(ROOT, p)
    return full if os.path.exists(full) else None


def main():
    pages = (glob.glob(os.path.join(ROOT, "*.html"))
             + glob.glob(os.path.join(ROOT, "recipes", "*.html")))
    stamped = touched = missing = 0

    for path in pages:
        page_rel = os.path.relpath(path, ROOT)
        src_html = open(path, encoding="utf-8").read()

        def fix(m):
            nonlocal stamped, missing
            tag = m.group(0)
            s = SRC.search(tag)
            if not s:
                return tag
            full = resolve(s.group(1), page_rel)
            if not full:
                missing += 1
                return tag
            wh = size_of(full)
            if not wh:
                missing += 1
                return tag
            tag = DIM.sub("", tag)
            tag = tag[:-1].rstrip()
            if tag.endswith("/"):
                tag = tag[:-1].rstrip()
            stamped += 1
            return '%s width="%d" height="%d" />' % (tag, wh[0], wh[1])

        out = IMG_TAG.sub(fix, src_html)
        if out != src_html:
            open(path, "w", encoding="utf-8").write(out)
            touched += 1

    print("stamped %d images across %d pages (%d unresolved)"
          % (stamped, touched, missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
