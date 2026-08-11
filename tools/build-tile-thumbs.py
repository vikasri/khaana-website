#!/usr/bin/env python3
"""Cut a small square thumbnail for every recipe shown as a tile.

    python3 tools/build-tile-thumbs.py [--force]

The 21 cuisine pages and the 8 collection pages list recipes as tiles, and a
tile's picture is a 74-pixel square. They pointed at the recipe photographs,
which are made to fill a recipe page and average about 150 KB. So the
gluten-free page held 524 of them: a reader who scrolled to the bottom pulled
somewhere near 80 MB to fill squares the size of a postage stamp. Lazy loading
kept that off the first paint but not off the reader -- it only decided when
the bytes arrived, not how many.

These are 148 pixels square, twice the display size so they stay sharp on a
dense screen, centre-cropped and saved hard. They come out around 6 KB, so the
same page costs about 3 MB fully scrolled instead of 80.

This is the argument tools/build-pair-thumbs.py already makes for the matching
game, which is where the numbers and the method come from. It is the same fix
applied to the other place the site shows a photograph small.

Centre-cropped rather than letterboxed. Food photographs put the food in the
middle, and a square with bars down the side reads as a broken image. It also
matches what the tile did before: the CSS was already object-fit: cover on a
square box, so the crop is what a reader saw anyway -- this only stops the
browser downloading the parts it was throwing away.

Idempotent: a thumbnail newer than its source is left alone, so a rebuild that
changes nothing costs nothing. --force recuts everything, which is what to run
after changing SIZE or QUALITY.

Run before tools/build-cuisine-recipes.py and tools/build-collections.py, which
point the tiles at whatever this leaves behind.
"""
import json, os, sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "images", "tiles")
REL = "assets/images/tiles"
# Twice .tile-thumb's 74px, so a 2x screen gets a whole pixel per pixel.
SIZE = 148
QUALITY = 72


def cut(src, dest):
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        side = min(w, h)
        im = im.crop(((w - side) // 2, (h - side) // 2,
                      (w + side) // 2, (h + side) // 2))
        im = im.resize((SIZE, SIZE), Image.LANCZOS)
        im.save(dest, "JPEG", quality=QUALITY, optimize=True, progressive=True)


def main():
    force = "--force" in sys.argv
    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    db = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))
    wanted, cut_now, saved_from = set(), 0, 0
    for r in db["recipes"]:
        img = (r.get("image") or {}).get("src")
        if not img:
            continue                      # tile-noimg: a letter, and no request
        src = os.path.join(ROOT, img)
        if not os.path.exists(src):
            continue
        dest = os.path.join(OUT, r["id"] + ".jpg")
        wanted.add(r["id"] + ".jpg")
        saved_from += os.path.getsize(src)
        if force or not os.path.exists(dest) or \
                os.path.getmtime(dest) < os.path.getmtime(src):
            cut(src, dest)
            cut_now += 1

    # A recipe that loses its photograph leaves its thumbnail behind, and a
    # directory that only ever grows is a directory nobody trusts.
    stale = [f for f in os.listdir(OUT) if f.endswith(".jpg") and f not in wanted]
    for f in stale:
        os.remove(os.path.join(OUT, f))

    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in wanted
                if os.path.exists(os.path.join(OUT, f)))
    print("tile thumbnails: %d in place (%d cut, %d removed), %d KB total"
          % (len(wanted), cut_now, len(stale), total / 1024))
    print("  the same %d pictures at full size are %d KB"
          % (len(wanted), saved_from / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
