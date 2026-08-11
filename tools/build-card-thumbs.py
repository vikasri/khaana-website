#!/usr/bin/env python3
"""Cut the cuisine-card picture for the home page.

    python3 tools/build-card-thumbs.py [--force]

The home page shows all 21 cuisines as cards. A card is 240 pixels wide with a
200-pixel picture on top, and it pointed at the cuisine hero photographs, which
are 1500 to 1600 pixels wide because that is what the cuisine page itself
needs. Twenty-one of them came to about 5.3 MB to fill a strip of thumbnails
six times smaller than the files behind them.

These are 480x400, twice the slot so they stay sharp on a dense screen, and
come out around 45 KB. The heroes are untouched: kerala.html still loads
kerala-hero.jpg at full size, which is the one place it is actually shown big.

Cropped to the slot's 6:5 rather than squeezed. The CSS was already
object-fit: cover on a fixed 240x200 box, so this is the crop a reader saw
anyway -- it only stops the browser fetching the parts it then discarded.

Idempotent: a thumbnail newer than its source is left alone. --force recuts
everything, which is what to run after changing SIZE or QUALITY.

index.html is hand-written, so it names these files directly rather than
falling back the way the generated tiles do. Keep this step in tools/rebuild.py
and the files will be there.
"""
import os, re, sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "images")
OUT = os.path.join(IMG, "cards")
# Twice .cuisine-card's 240x200 slot, so a 2x screen gets a whole pixel per
# pixel. The ratio has to match the slot or cover() would crop twice.
W, H = 480, 400
QUALITY = 72


def cut(src, dest):
    with Image.open(src) as im:
        im = im.convert("RGB")
        sw, sh = im.size
        # Widest box of the target ratio that fits, centred: the same crop
        # object-fit: cover was already doing in the browser.
        if sw / sh > W / H:
            side_w, side_h = int(sh * W / H), sh
        else:
            side_w, side_h = sw, int(sw * H / W)
        im = im.crop(((sw - side_w) // 2, (sh - side_h) // 2,
                      (sw + side_w) // 2, (sh + side_h) // 2))
        im = im.resize((W, H), Image.LANCZOS)
        im.save(dest, "JPEG", quality=QUALITY, optimize=True, progressive=True)


def main():
    force = "--force" in sys.argv
    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    # Driven by what the page actually asks for, so a card added or swapped in
    # index.html needs nothing changed here.
    src_html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    names = []
    for m in re.finditer(r'<div class="thumb"><img src="assets/images/(?:cards/)?([^"]+)"', src_html):
        names.append(os.path.basename(m.group(1)))

    wanted, cut_now, saved_from, missing = set(), 0, 0, []
    for name in names:
        src = os.path.join(IMG, name)
        if not os.path.exists(src):
            missing.append(name)
            continue
        dest = os.path.join(OUT, name)
        wanted.add(name)
        saved_from += os.path.getsize(src)
        if force or not os.path.exists(dest) or \
                os.path.getmtime(dest) < os.path.getmtime(src):
            cut(src, dest)
            cut_now += 1

    stale = [f for f in os.listdir(OUT) if f.lower().endswith(".jpg") and f not in wanted]
    for f in stale:
        os.remove(os.path.join(OUT, f))

    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in wanted)
    print("card thumbnails: %d in place (%d cut, %d removed), %d KB total"
          % (len(wanted), cut_now, len(stale), total / 1024))
    print("  the same %d pictures at full size are %d KB"
          % (len(wanted), saved_from / 1024))
    if missing:
        print("  no such source: %s" % ", ".join(sorted(set(missing))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
