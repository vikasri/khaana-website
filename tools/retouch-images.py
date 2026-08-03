#!/usr/bin/env python3
"""Even out exposure, colour cast and flatness across the recipe photographs.

    python3 tools/retouch-images.py --report        # what would change, nothing written
    python3 tools/retouch-images.py --sample 12     # before/after sheet to look at
    python3 tools/retouch-images.py --write         # apply

The photographs come from several hundred different people, cameras and
kitchens. Individually most are fine; together they read as a jumble, because
a phone snap under a tube light and a DSLR frame by a window are two different
pictures of food even when both are in focus. An image audit put 206 of them
in a "usable, but crop, brighten and colour-correct" bucket and called that
the cheapest available improvement, ahead of licensing anything new.

What this does, in order:

  1. White balance in ONE DIRECTION ONLY: towards warm, never away from it.

     This started as an ordinary grey-world correction and it was wrong. Food
     photographs are warm because food is warm — browned onion, ghee, chilli
     oil, a tandoor char. Grey-world reads all of that as a colour cast and
     dutifully launders it out, and every test frame came back looking like a
     canteen under a fluorescent tube. The correction now only ever adds red
     and removes blue. A green or blue kitchen light gets fixed; the warmth of
     the food itself is left alone, because it is the point.

  2. Percentile levels. Stretch so the darkest 0.5% sits at black and the
     brightest 0.5% at white, then apply only part of that stretch.

  3. Exposure towards a target, but asymmetric again: a dark photograph is
     lifted willingly, a bright one is pulled back only when it is close to
     blowing out. A white plate under a window legitimately reads bright and
     dragging it to mid-grey makes lunch look like an X-ray.

  4. Saturation and contrast, pushed with some confidence rather than
     tiptoeing. Flat is the most common fault in the set and the one that
     makes a dish look like leftovers.

  5. A small fixed warm tint, then an unsharp mask. Together these are what
     turns "correctly exposed" into "worth cooking".

Nothing here invents detail. The guard rails matter more than the adjustments:
a photograph that is already bright, warm and punchy gets almost nothing, and
MAX_* caps every step, so the worst case is a picture slightly better than it
was rather than one that has been mangled.

Run once per photograph, and only once. A second pass over an already-corrected
file would lift and saturate what has already been lifted and saturated, and
three runs would produce a postcard. The credit record carries a
"colour-corrected" note, and any file that has one is skipped — so this is safe
to re-run after adding photographs, which is the case it is actually for.

No separate copy of the originals is kept. They would be seventy megabytes of
duplicate JPEG in the repository to guard against something git already guards
against: `git checkout HEAD~1 -- assets/images/recipes/` puts every one of them
back, and credits.json records the source URL of each if it ever comes to
re-downloading.
"""
import argparse, json, os, sys

from PIL import Image, ImageEnhance, ImageFilter, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "assets", "images", "recipes")
RECIPES = os.path.join(ROOT, "data", "recipes.json")
CREDITS = os.path.join(ROOT, "assets", "images", "credits.json")

# How far towards a "perfect" correction to go.
STRENGTH = 0.55

# White balance, one-way. Red may be raised and blue lowered; neither may go
# the other way, so a warm photograph can never be cooled down. Green moves a
# little in both directions because a green cast is a lighting fault with no
# appetising reading at all.
WB_R = (1.00, 1.12)
WB_G = (0.96, 1.04)
WB_B = (0.90, 1.00)

MAX_LEVELS = 0.22      # fraction of the full black/white stretch to apply
MAX_SAT = 1.30
MAX_CONTRAST = 1.18
MAX_BRIGHT = 1.20      # lifting a dark photo
MAX_DARKEN = 1.06      # pulling back a bright one: much less latitude

# A fixed nudge on every frame, on top of the corrections above. Two per cent
# is not visible as a colour shift; it is visible as food looking cooked.
WARM_TINT = 0.02

# What "already fine" looks like, on 0-255 means and a 0-1 saturation ratio.
# The exposure target sits above mid-grey because a plate of food photographed
# well is a bright object, not an average one.
TARGET_MEAN = 138.0
BRIGHT_ENOUGH = 175.0  # above this, and only above this, pull back
TARGET_SAT = 0.46
TARGET_CONTRAST = 60.0
DEADZONE = 0.04        # relative miss below which nothing is done at all

TARGET_KB = 190


def stats(im):
    """(mean luminance 0-255, rms contrast 0-255, mean saturation 0-1)."""
    g = im.convert("L")
    st = ImageStat.Stat(g)
    hsv = im.convert("HSV")
    sat = ImageStat.Stat(hsv.split()[1]).mean[0] / 255.0
    return st.mean[0], st.stddev[0], sat


def white_balance(im):
    """Grey-world, damped, then clamped so it can only ever warm the frame."""
    r, g, b = ImageStat.Stat(im).mean
    grey = (r + g + b) / 3.0
    if grey <= 1:
        return im, (1.0, 1.0, 1.0)
    gains = []
    for c, (lo, hi) in zip((r, g, b), (WB_R, WB_G, WB_B)):
        want = grey / max(c, 1.0)
        want = 1.0 + (want - 1.0) * STRENGTH
        gains.append(max(lo, min(hi, want)))
    gains[0] *= 1 + WARM_TINT
    gains[2] *= 1 - WARM_TINT
    lut = []
    for gain in gains:
        lut += [min(255, int(v * gain + 0.5)) for v in range(256)]
    return im.point(lut), tuple(round(x, 3) for x in gains)


def levels(im):
    """Percentile black/white point stretch, applied at MAX_LEVELS strength."""
    g = im.convert("L")
    hist = g.histogram()
    total = sum(hist)
    lo_target, hi_target = total * 0.005, total * 0.995
    acc, lo, hi = 0, 0, 255
    for v, n in enumerate(hist):
        acc += n
        if acc <= lo_target:
            lo = v
        if acc <= hi_target:
            hi = v
    if hi - lo < 16:
        return im, (0, 255)
    # Only part of the way: a full stretch clips highlights on a bright dish.
    lo = int(lo * MAX_LEVELS)
    hi = int(255 - (255 - hi) * MAX_LEVELS)
    if hi <= lo:
        return im, (0, 255)
    scale = 255.0 / (hi - lo)
    lut = [max(0, min(255, int((v - lo) * scale + 0.5))) for v in range(256)]
    return im.point(lut * 3), (lo, hi)


def toward(current, target, cap, cap_down=None):
    """A multiplier moving current towards target, capped in each direction."""
    if current <= 0:
        return 1.0
    want = target / current
    if abs(want - 1.0) < DEADZONE:
        return 1.0
    want = 1.0 + (want - 1.0) * STRENGTH
    return max(1.0 / (cap_down or cap), min(cap, want))


# --- the gate ---------------------------------------------------------------
#
# Only photographs that fail one of these get touched at all. A picture that is
# already bright, warm and punchy is left byte-for-byte alone: running a
# standard correction over the whole set would drag the good ones towards the
# mean along with the bad, and the good ones are the reason the set works.
DARK = 118.0           # mean luminance below which a dish looks like leftovers
FLAT = 48.0            # rms contrast below which it looks like a photocopy
DULL = 0.32            # saturation below which the food looks grey
COLD = 1.03            # blue/red ratio above which the light was fluorescent
BLOWN = 205.0          # mean above which highlights are going


def faults(im):
    """Which quality bars this photograph fails, if any."""
    mean, contrast, sat = stats(im)
    r, g, b = ImageStat.Stat(im).mean
    out = []
    if mean < DARK:
        out.append("dark")
    if contrast < FLAT:
        out.append("flat")
    if sat < DULL:
        out.append("dull")
    if b / max(r, 1.0) > COLD:
        out.append("cold")
    if mean > BLOWN:
        out.append("blown")
    return out, (mean, contrast, sat)


def retouch(im):
    """Return (image, what_changed_dict)."""
    before = stats(im)
    im, gains = white_balance(im)
    im, lohi = levels(im)

    mean, contrast, sat = stats(im)
    # Lift a dark frame willingly; pull back a bright one only when it is
    # genuinely close to blowing out.
    target = TARGET_MEAN if mean < TARGET_MEAN else BRIGHT_ENOUGH
    b = 1.0 if mean < BRIGHT_ENOUGH and mean >= TARGET_MEAN else \
        toward(mean, target, MAX_BRIGHT, MAX_DARKEN)
    if b != 1.0:
        im = ImageEnhance.Brightness(im).enhance(b)
    s = toward(sat, TARGET_SAT, MAX_SAT)
    if s != 1.0:
        im = ImageEnhance.Color(im).enhance(s)
    c = toward(contrast, TARGET_CONTRAST, MAX_CONTRAST)
    if c != 1.0:
        im = ImageEnhance.Contrast(im).enhance(c)

    im = im.filter(ImageFilter.UnsharpMask(radius=1.1, percent=55, threshold=3))
    after = stats(im)
    return im, {"wb": gains, "levels": lohi, "brightness": round(b, 3),
                "saturation": round(s, 3), "contrast": round(c, 3),
                "before": [round(x, 1) for x in before],
                "after": [round(x, 1) for x in after]}


def source_path(name):
    return os.path.join(IMG_DIR, name)


def already_done(creds):
    """Files whose credit record says they have been through this already."""
    return {c["file"].split("/")[-1] for c in creds
            if "colour-corrected" in (c.get("note") or "")}


def save(im, dest):
    # Same ladder as tools/fetch-recipe-images.py, and it has to be: starting
    # at 86 instead of 82 put 27 photographs over the 190 KB budget and added
    # 8 MB to the site. Sharpening makes a file harder to compress, so this
    # steps further down than the fetcher needs to.
    for q in (82, 76, 70, 64, 58, 52):
        im.save(dest, "JPEG", quality=q, optimize=True, progressive=True)
        if os.path.getsize(dest) <= TARGET_KB * 1024:
            break
    return os.path.getsize(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--only", help="comma-separated recipe ids")
    args = ap.parse_args()

    creds = json.load(open(CREDITS, encoding="utf-8"))
    done = already_done(creds)

    names = sorted(f for f in os.listdir(IMG_DIR) if f.endswith(".jpg"))
    if args.only:
        want = {s.strip() + ".jpg" for s in args.only.split(",")}
        names = [n for n in names if n in want]
    redone = len([n for n in names if n in done])
    names = [n for n in names if n not in done]
    if redone:
        print("%d already corrected on an earlier run, skipped" % redone)

    results, skipped, tally = [], 0, {}
    for name in names:
        try:
            im = Image.open(source_path(name)).convert("RGB")
        except Exception as e:
            print("  ! %s %s" % (name, e))
            continue
        why, _ = faults(im)
        if not why:
            skipped += 1
            continue
        for f in why:
            tally[f] = tally.get(f, 0) + 1
        out, ch = retouch(im)
        ch["faults"] = why
        results.append((name, out, ch))

    print("%d photographs: %d already good and left alone, %d to correct"
          % (len(names), skipped, len(results)))
    for f in sorted(tally, key=lambda k: -tally[k]):
        print("    %-6s %3d" % (f, tally[f]))
    if args.report:
        print()
        for name, _, ch in results[:40]:
            print("  %-32s %-18s mean %5.1f->%5.1f  sat %.2f->%.2f"
                  % (name, ",".join(ch["faults"]), ch["before"][0], ch["after"][0],
                     ch["before"][2], ch["after"][2]))
        return 0

    if args.sample:
        picks = results[:: max(1, len(results) // args.sample)][:args.sample]
        cw, ch_ = 320, 250
        sheet = Image.new("RGB", (2 * cw, len(picks) * ch_), (250, 247, 240))
        for n, (name, out, _) in enumerate(picks):
            a = Image.open(source_path(name)).convert("RGB")
            for col, img in ((0, a), (1, out)):
                t = img.copy()
                t.thumbnail((cw - 10, ch_ - 10))
                sheet.paste(t, (col * cw + (cw - t.width) // 2,
                                n * ch_ + (ch_ - t.height) // 2))
        dest = os.path.join(ROOT, "tools", "_retouch_sample.jpg")
        sheet.save(dest, quality=90)
        print("before | after: %s" % os.path.relpath(dest, ROOT))
        for n, (name, _, c) in enumerate(picks):
            print("  %2d %-34s %s" % (n, name, c["wb"]))
        return 0

    if not args.write:
        print("nothing written; pass --write")
        return 0

    for name, out, _ in results:
        save(out, os.path.join(IMG_DIR, name))

    # CC BY-SA asks that changes be identified, and the credit record is where
    # this site says what it did to a file. It is also what stops a second run
    # correcting the same photograph twice.
    touched = {n for n, _, _ in results}
    for c in creds:
        if (c.get("file") or "").split("/")[-1] in touched:
            note = c.get("note") or ""
            c["note"] = (note + "; colour-corrected" if note
                         else "colour-corrected").strip("; ")
    json.dump(creds, open(CREDITS, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("rewrote %d photographs; credits note the correction"
          % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
