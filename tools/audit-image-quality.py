#!/usr/bin/env python3
"""Score every recipe photograph and write the list worth replacing.

    python3 tools/audit-image-quality.py

Writes tools/IMAGE-BACKLOG.md and tools/_image_quality.json.

This is the standing list of what to fix next, and it is measured rather than
remembered: 433 photographs were brightened and colour-corrected in one pass,
so any list written before that is describing a site that no longer exists.
Re-run it after adding or replacing photographs and the backlog re-sorts
itself.

Five things are measured, all of them cheap and none of them a judgement about
beauty:

  resolution   pixels. A 500x500 file is soft on a phone before anything else
               is wrong with it.
  sharpness    variance of a Laplacian-ish edge pass. Catches motion blur and
               heavy JPEG mush, which no amount of correction recovers.
  exposure     how far the mean sits from a well-lit plate of food.
  contrast     rms spread. Flat photographs read as leftovers.
  saturation   grey food looks uncooked.

A photograph that is still dark or flat AFTER the retouch pass is one the
correction could not save, which is a much stronger signal than being dark
before it. That is the whole reason this runs afterwards.

What it cannot see is composition, clutter, a hand in frame, a plastic tub, or
whether the dish is the right dish. tools/audit-image-subjects.py covers the
last of those. The rest still needs eyes, so this is a shortlist to look at,
not a verdict.
"""
import json, os, sys
from collections import Counter

from PIL import Image, ImageFilter, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "assets", "images", "recipes")
RECIPES = os.path.join(ROOT, "data", "recipes.json")
SUBJECTS = os.path.join(ROOT, "tools", "_image_subjects.json")
OUT_JSON = os.path.join(ROOT, "tools", "_image_quality.json")
OUT_MD = os.path.join(ROOT, "tools", "IMAGE-BACKLOG.md")

# Below these a photograph goes on the list. Set from the distribution of the
# current set, not from theory: roughly the worst tenth on each axis.
MIN_PIXELS = 500_000        # e.g. 800x625. Under this it is soft on a phone.
MIN_SHARP = 120.0
MIN_MEAN, MAX_MEAN = 105.0, 200.0
MIN_CONTRAST = 44.0
MIN_SAT = 0.26


def measure(path):
    im = Image.open(path).convert("RGB")
    g = im.convert("L")
    st = ImageStat.Stat(g)
    sharp = ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES)).stddev[0] ** 2
    sat = ImageStat.Stat(im.convert("HSV").split()[1]).mean[0] / 255.0
    return {
        "w": im.width, "h": im.height, "pixels": im.width * im.height,
        "kb": round(os.path.getsize(path) / 1024),
        "sharpness": round(sharp, 1),
        "mean": round(st.mean[0], 1),
        "contrast": round(st.stddev[0], 1),
        "saturation": round(sat, 2),
    }


def faults(m):
    out = []
    if m["pixels"] < MIN_PIXELS:
        out.append("low resolution (%dx%d)" % (m["w"], m["h"]))
    if m["sharpness"] < MIN_SHARP:
        out.append("soft or blurred")
    if m["mean"] < MIN_MEAN:
        out.append("still dark after correction")
    if m["mean"] > MAX_MEAN:
        out.append("blown highlights")
    if m["contrast"] < MIN_CONTRAST:
        out.append("flat")
    if m["saturation"] < MIN_SAT:
        out.append("colourless")
    return out


def main():
    doc = json.load(open(RECIPES, encoding="utf-8"))
    recipes = doc["recipes"]
    subjects = (json.load(open(SUBJECTS, encoding="utf-8"))
                if os.path.exists(SUBJECTS) else {"unverified": [], "wrong": []})
    unverified = {e["id"] for e in subjects.get("unverified", [])}
    wrong = {e["id"] for e in subjects.get("wrong", [])}

    missing, weak, borrowed, ok = [], [], [], 0
    for r in recipes:
        if not r.get("image"):
            missing.append({"id": r["id"], "name": r["name"], "region": r["region"]})
            continue
        # Points at a cuisine hero or gallery file rather than its own. The
        # photograph is fine; it is just doing two jobs, so the dish shows up
        # twice to anyone browsing that cuisine.
        if not r["image"]["src"].startswith("assets/images/recipes/"):
            borrowed.append({"id": r["id"], "name": r["name"], "region": r["region"],
                             "src": r["image"]["src"]})
        path = os.path.join(ROOT, r["image"]["src"])
        if not os.path.exists(path):
            missing.append({"id": r["id"], "name": r["name"], "region": r["region"],
                            "note": "image file listed but not on disk"})
            continue
        m = measure(path)
        f = faults(m)
        if r["id"] in wrong:
            f.append("subject may be wrong")
        if not f:
            ok += 1
            continue
        weak.append({"id": r["id"], "name": r["name"], "region": r["region"],
                     "faults": f, "credit": r["image"].get("credit"),
                     "license": r["image"].get("license"),
                     "source": r["image"].get("sourceUrl"), **m})

    # Worst first: how many ways it fails, then how soft it is.
    weak.sort(key=lambda x: (-len(x["faults"]), x["sharpness"]))
    missing.sort(key=lambda x: (x["region"], x["name"]))

    borrowed.sort(key=lambda x: (x["region"], x["name"]))
    json.dump({"weak": weak, "missing": missing, "borrowed": borrowed, "clean": ok,
               "unverified_subject": sorted(unverified)},
              open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    tally = Counter(f.split(" (")[0] for w in weak for f in w["faults"])
    L = []
    L.append("# Image backlog\n")
    L.append("Generated by `tools/audit-image-quality.py`. Re-run it after "
             "adding or replacing photographs.\n")
    L.append("| | |\n|---|---|")
    L.append("| Recipes | %d |" % len(recipes))
    L.append("| Photographs that pass every check | %d |" % ok)
    L.append("| Photographs worth replacing | %d |" % len(weak))
    L.append("| Recipes with no photograph | %d |" % len(missing))
    L.append("| Recipes borrowing a cuisine photograph | %d |" % len(borrowed))
    L.append("")
    L.append("Measured **after** the colour-correction pass, so anything still "
             "listed as dark or flat is one the correction could not save. "
             "Composition, clutter and whether the dish is the right dish are "
             "not measurable here and still need eyes.\n")

    L.append("## No photograph (%d)\n" % len(missing))
    L.append("These fall back to a letter tile, which is honest but plain. "
             "Worth a targeted Openverse or Commons search, or a photograph of "
             "your own.\n")
    L.append("| Recipe | Region | |")
    L.append("|---|---|---|")
    for m in missing:
        L.append("| %s | %s | %s |" % (m["name"], m["region"], m.get("note", "")))
    L.append("")

    L.append("## Borrowing a cuisine photograph (%d)\n" % len(borrowed))
    L.append("These have no photograph of their own and are showing their "
             "cuisine's hero or gallery image instead. Nothing is wrong with "
             "the picture, but the same frame appears twice to anyone browsing "
             "that cuisine, and this list is most of the site's best-known "
             "dishes — Butter Chicken, Rogan Josh, Masala Dosa, Vada Pav, "
             "Hyderabadi Biryani. They are the highest-traffic pages on the "
             "site and the strongest case for a commissioned shot.\n")
    L.append("| Recipe | Region | Currently showing |")
    L.append("|---|---|---|")
    for b in borrowed:
        L.append("| [%s](../recipes/%s.html) | %s | `%s` |"
                 % (b["name"], b["id"], b["region"], b["src"].split("/")[-1]))
    L.append("")

    L.append("## Weak photographs (%d)\n" % len(weak))
    L.append("Worst first, by how many checks each fails.\n")
    L.append("| Recipe | Region | Why | Size | Sharp | Credit |")
    L.append("|---|---|---|---|---|---|")
    for w in weak:
        L.append("| [%s](../recipes/%s.html) | %s | %s | %dx%d | %.0f | [%s](%s) |"
                 % (w["name"], w["id"], w["region"], "; ".join(w["faults"]),
                    w["w"], w["h"], w["sharpness"], w["credit"] or "?",
                    w["source"] or ""))
    L.append("")

    L.append("### Faults by kind\n")
    L.append("| Fault | Count |\n|---|---|")
    for k, v in tally.most_common():
        L.append("| %s | %d |" % (k, v))
    L.append("")

    if unverified:
        L.append("## Subject not confirmed (%d)\n" % len(unverified))
        L.append("`tools/audit-image-subjects.py` could not find a food "
                 "category on the source file. Usually it just means the "
                 "uploader never categorised their photograph, so this is a "
                 "watch list rather than a fault list.\n")
        L.append("`" + "`, `".join(sorted(unverified)) + "`\n")

    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L))
    print("%d photographs pass, %d weak, %d with none, %d borrowing a cuisine shot"
          % (ok, len(weak), len(missing), len(borrowed)))
    for k, v in tally.most_common():
        print("    %-30s %3d" % (k, v))
    print("\nwrote %s" % os.path.relpath(OUT_MD, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
