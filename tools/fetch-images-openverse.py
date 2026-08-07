#!/usr/bin/env python3
"""Find photographs for recipes that still have none, via Openverse.

    python3 tools/fetch-images-openverse.py            # stage candidates
    python3 tools/fetch-images-openverse.py --install id1 id2 ...

Why a second fetcher. tools/fetch-recipe-images.py searches Wikimedia Commons,
which is where this site's photographs mostly come from and is the right first
stop for anything with a Commons category. It came back empty for 15 of the 16
recipes that still had no picture, and for the sixteenth it returned a mixed
spread of green curry and parathas for a chicken soup. Openverse indexes Flickr
and several museum collections as well as Commons, and for that same dish its
first hit is an actual bowl of murgh shorba — while its *second* hit is the
paratha spread Commons ranked first. Different index, different ranking, and
between them they cover more ground than either alone.

Two steps on purpose. Nothing is installed by the default run: candidates land
in tools/_openverse_staging/ with a manifest, and a human looks at them before
--install writes anything into data/recipes.json. A confident wrong match is
the failure mode here, and it is not one an automated check catches — a
photograph of the wrong dish is a perfectly good photograph.

Licences: CC0, PDM, BY and BY-SA accepted. NC is rejected because the site may
carry advertising one day, ND because it forbids the resizing below.
"""

import argparse
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGING = os.path.join(ROOT, "tools", "_openverse_staging")
RECIPES = os.path.join(ROOT, "data", "recipes.json")
CREDITS = os.path.join(ROOT, "assets", "images", "credits.json")
OUT_DIR = os.path.join(ROOT, "assets", "images", "recipes")
API = "https://api.openverse.org/v1/images/"
UA = "KhaanaSiteBot/1.0 (https://khaana.com)"

OK_LICENCE = {"cc0", "pdm", "by", "by-sa"}
MAX_W = 1000
TARGET_KB = 190
PAUSE = 0.6
PER_RECIPE = 3        # how many candidates to stage, so there is a choice

# Words that carry no dish meaning, so a title matching only on these has
# matched nothing. Same idea as the Commons guard, same reason.
STOP = {"and", "with", "the", "of", "in", "a", "ka", "ki", "ke", "style",
        "curry", "masala", "indian", "recipe", "dish", "fry", "gravy", "made",
        "at", "home", "img", "food", "traditional"}


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return fh.read()


def tokens(s):
    return {w for w in re.split(r"[^a-z]+", s.lower()) if w and w not in STOP and len(w) > 2}


def search(name, region):
    """Dish name first; the region only as a fallback, because 'Bihari' alone
    reliably returns a thali that is not the dish asked for."""
    queries = [name, "%s %s" % (name, region)]
    seen, out = set(), []
    for q in queries:
        url = API + "?" + urllib.parse.urlencode({
            "q": q, "license_type": "all-cc,commercial",
            "page_size": 12, "mature": "false",
        })
        try:
            data = json.loads(get(url))
        except Exception as exc:
            print("    ! search failed (%s): %s" % (q, str(exc)[:60]))
            continue
        for r in data.get("results", []):
            lic = (r.get("license") or "").lower()
            if lic not in OK_LICENCE:
                continue
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            # The title must share a real word with the dish, which is what
            # keeps "Bai" from matching every photograph containing the
            # letters b-a-i.
            if not (tokens(r.get("title") or "") & tokens(name)):
                continue
            out.append(r)
        time.sleep(PAUSE)
    return out[:PER_RECIPE]


def stage_one(r, cand, n):
    raw = get(cand["url"], timeout=60)
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    for q in (86, 80, 74, 68):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= TARGET_KB * 1024:
            break
    path = os.path.join(STAGING, "%s__%d.jpg" % (r["id"], n))
    with open(path, "wb") as fh:
        fh.write(buf.getvalue())
    return {
        "recipe": r["id"], "name": r["name"], "region": r["region"],
        "file": os.path.relpath(path, ROOT), "n": n,
        "title": cand.get("title"), "licence": (cand.get("license") or "").upper(),
        "version": cand.get("license_version"),
        "creator": cand.get("creator") or "Unknown",
        "source": cand.get("foreign_landing_url") or cand.get("url"),
        "size": "%dx%d" % (im.width, im.height),
    }


def do_stage():
    os.makedirs(STAGING, exist_ok=True)
    db = json.load(open(RECIPES, encoding="utf-8"))
    todo = [r for r in db["recipes"]
            if not r.get("image") or not (r["image"] or {}).get("src")]
    print("recipes with no photograph: %d\n" % len(todo))

    manifest = []
    for r in todo:
        print("  %-22s %s" % (r["id"][:22], r["region"]))
        try:
            cands = search(r["name"], r["region"])
        except Exception as exc:
            print("    ! %s" % str(exc)[:70])
            continue
        if not cands:
            print("    no candidate")
            continue
        for n, c in enumerate(cands, 1):
            try:
                entry = stage_one(r, c, n)
            except Exception as exc:
                print("    ! download %d: %s" % (n, str(exc)[:60]))
                continue
            manifest.append(entry)
            print("    %d. %-52s %s" % (n, (entry["title"] or "")[:52], entry["licence"]))

    with open(os.path.join(STAGING, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
    print("\nstaged %d candidates for %d recipes -> %s"
          % (len(manifest), len({m["recipe"] for m in manifest}),
             os.path.relpath(STAGING, ROOT)))
    print("look at them, then: python3 tools/fetch-images-openverse.py --install <recipe-id>__<n> ...")


LICENCE_LABEL = {"CC0": "CC0", "PDM": "Public domain",
                 "BY": "CC BY", "BY-SA": "CC BY-SA"}


def do_install(picks):
    """Install chosen candidates, writing the photo, the recipe entry and the
    credit row together — never one without the others."""
    manifest = json.load(open(os.path.join(STAGING, "manifest.json"), encoding="utf-8"))
    by_key = {"%s__%d" % (m["recipe"], m["n"]): m for m in manifest}
    db = json.load(open(RECIPES, encoding="utf-8"))
    recipes = {r["id"]: r for r in db["recipes"]}
    credits = json.load(open(CREDITS, encoding="utf-8"))
    rows = credits["images"] if isinstance(credits, dict) else credits

    done = 0
    for key in picks:
        m = by_key.get(key)
        if not m:
            print("  ! %-28s not in the manifest" % key)
            continue
        r = recipes[m["recipe"]]
        dest_rel = "assets/images/recipes/%s.jpg" % r["id"]
        with open(os.path.join(ROOT, m["file"]), "rb") as src:
            with open(os.path.join(ROOT, dest_rel), "wb") as dst:
                dst.write(src.read())

        lic = LICENCE_LABEL.get(m["licence"], m["licence"])
        if m["version"] and m["licence"] not in ("CC0", "PDM"):
            lic = "%s %s" % (lic, m["version"])
        r["image"] = {
            "src": dest_rel,
            "alt": r["name"],
            "credit": m["creator"],
            "license": lic,
            "source": m["source"],
        }
        # credits.json has one schema and build-credits.py reads exactly it.
        # A row invented to look reasonable — file/recipe/credit/source — was
        # accepted silently by the JSON and then reported by build-credits.py
        # as an image with no attribution at all, which is the one thing this
        # file exists to prevent. Paths here are relative to assets/images.
        rows.append({
            "file": "recipes/%s.jpg" % r["id"],
            "region": r["region"],
            "slot": "recipe",
            "wiki_title": m["title"],
            "source_url": m["source"],
            "license": lic,
            "artist": m["creator"],
            "note": "fetched by tools/fetch-images-openverse.py",
        })
        rows.sort(key=lambda x: (x.get("slot", ""), x.get("file", "")))
        print("  + %-24s %s / %s" % (r["id"][:24], m["creator"], lic))
        done += 1

    json.dump(db, open(RECIPES, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(credits, open(CREDITS, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\ninstalled %d. Now run: python3 tools/rebuild.py" % done)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", nargs="*", default=None,
                    help="candidate keys, e.g. murgh-shorba__1")
    args = ap.parse_args()
    if args.install:
        do_install(args.install)
    else:
        do_stage()


if __name__ == "__main__":
    main()
