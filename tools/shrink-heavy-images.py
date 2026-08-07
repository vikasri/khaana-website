#!/usr/bin/env python3
"""Cap the handful of photographs that are far heavier than the page needs.

Not a blanket recompression pass. The 588 recipe thumbnails were measured
first and they are already close to optimal: re-encoding them at quality 78
saved 5% overall and made several of them *larger*, because they are already
at or below that quality. Their pixel dimensions are right too — a 1000px
source fills a 337px slot at 1.0-1.5x on the 2x and 3x phone screens this
site is mostly read on, which is what those screens want.

What is genuinely oversized is a small tail: cuisine hero and gallery shots
that came in at up to 1800px on the long edge and half a megabyte each. This
caps the long edge at 1600 and re-encodes at quality 82, and keeps the result
only when it is actually smaller, so running it twice is a no-op.

    python3 tools/shrink-heavy-images.py [--apply]

Without --apply it prints what it would do and writes nothing.
"""

import glob
import io
import os
import sys

from PIL import Image

THRESHOLD = 250 * 1024   # only look at files heavier than this
MAX_EDGE = 1600
QUALITY = 82


def main():
    apply = "--apply" in sys.argv
    root = os.path.join(os.path.dirname(__file__), "..")
    os.chdir(root)

    heavy = sorted(
        f for f in glob.glob("assets/images/**/*.jpg", recursive=True)
        if os.path.getsize(f) > THRESHOLD
    )

    before = after = 0
    changed = 0
    for f in heavy:
        original = os.path.getsize(f)
        im = Image.open(f)
        # EXIF orientation is applied on decode by browsers but not by PIL, so
        # a re-saved portrait shot can come back rotated. Bake it in first.
        try:
            from PIL import ImageOps
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass
        im = im.convert("RGB")

        w, h = im.size
        longest = max(w, h)
        if longest > MAX_EDGE:
            scale = MAX_EDGE / longest
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)

        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=QUALITY, optimize=True, progressive=True)

        before += original
        if buf.tell() < original:
            after += buf.tell()
            changed += 1
            print("  %-44s %6.0fK -> %6.0fK  %sx%s"
                  % (f, original / 1024, buf.tell() / 1024, im.width, im.height))
            if apply:
                with open(f, "wb") as out:
                    out.write(buf.getvalue())
        else:
            after += original   # already smaller than we would make it; left alone

    print("\n%d heavy files, %d rewritten: %.1f MB -> %.1f MB (-%.0f%%)"
          % (len(heavy), changed, before / 1048576, after / 1048576,
             100 * (1 - after / before) if before else 0))
    if not apply:
        print("dry run — pass --apply to write")


if __name__ == "__main__":
    main()
