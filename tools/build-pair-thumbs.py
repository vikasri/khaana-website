#!/usr/bin/env python3
"""Cut a small square thumbnail for every dish in the matching game.

    python3 tools/build-pair-thumbs.py [--force]

The game shows a picture beside each dish name. The obvious thing is to point
those at the recipe photographs already in the repository, and the obvious
thing is wrong: they average 150 KB because they are made to fill a recipe
page, and the game deals four new dishes every round. A reader playing ten
rounds would pull about six megabytes to fill forty squares 48 pixels wide.

These are 112 pixels square — twice the display size, so they stay sharp on a
dense screen — centre-cropped and saved hard. They come out around 4 KB, so a
round costs less than a fifth of one recipe photograph.

Centre-cropped rather than letterboxed. Food photographs put the food in the
middle, and a square with bars down the side reads as a broken image.

Idempotent: a thumbnail newer than its source is left alone, so a rebuild that
changes nothing costs nothing. --force recuts everything, which is what to run
after changing SIZE or QUALITY.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from pair_pool import pair_pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "images", "pair")
SIZE = 112
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

    wanted, cut_now, missing = set(), 0, []
    for entries in pair_pool().values():
        for name, rid, img in entries:
            if not img:
                missing.append(name)
                continue
            src = os.path.join(ROOT, img)
            if not os.path.exists(src):
                missing.append(name)
                continue
            dest = os.path.join(OUT, rid + ".jpg")
            wanted.add(rid + ".jpg")
            if force or not os.path.exists(dest) or \
                    os.path.getmtime(dest) < os.path.getmtime(src):
                cut(src, dest)
                cut_now += 1

    # A dish that leaves the pool leaves its thumbnail behind, and a directory
    # that only ever grows is a directory nobody trusts.
    stale = [f for f in os.listdir(OUT) if f.endswith(".jpg") and f not in wanted]
    for f in stale:
        os.remove(os.path.join(OUT, f))

    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in wanted
                if os.path.exists(os.path.join(OUT, f)))
    print("pair thumbnails: %d in place (%d cut, %d removed), %d KB total"
          % (len(wanted), cut_now, len(stale), total / 1024))
    if missing:
        print("  %d dishes have no photograph and will show a plain square: %s"
              % (len(missing), ", ".join(sorted(missing))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
