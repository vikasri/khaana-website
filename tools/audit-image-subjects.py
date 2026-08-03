#!/usr/bin/env python3
"""Re-check every published photograph against the subject guard.

    python3 tools/audit-image-subjects.py [--out tools/_image_subjects.json]

tools/fetch-recipe-images.py refuses a candidate whose Commons categories say
it is not food, and the comment at the top of that file names the exact hit
that made the rule necessary: "Ball Curry matched a photograph of a basketball
game on the word 'ball'". The guard works. The problem is that it only ever ran
at the moment a picture was fetched, and the pictures fetched before it existed
were never re-examined — so the basketball photograph is still on the Ball
Curry page, and a black-and-white portrait of a man is still on Mandua ki Roti.

This runs the same gate over what is already published. It asks Commons for the
categories of every current image and reports three kinds of problem:

  wrong      categories positively say not-food: sport, portrait, building
  unverified no food category at all, so nothing confirms the subject
  gone       the file is no longer on Commons under that name

Read the result as triage, not verdict. "unverified" mostly means an uploader
never categorised their photo, which says nothing about what is in it. "wrong"
is the one worth acting on, and it is worth acting on immediately: a picture of
the wrong thing is the one image fault a reader cannot forgive, and the one
this site's own notes say never to be lenient about.
"""
import argparse, importlib.util, json, os, re, sys, time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The gate itself is not redefined here. It lives in the fetcher, and a second
# copy would drift from it and start disagreeing about what counts as food.
spec = importlib.util.spec_from_file_location(
    "fetcher", os.path.join(ROOT, "tools", "fetch-recipe-images.py"))
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

API = "https://commons.wikimedia.org/w/api.php"
BATCH = 40            # Commons accepts up to 50 titles per query
PAUSE = 0.4


def commons_title(url):
    """File title out of a Commons description URL, or None if not Commons."""
    if not url or "commons.wikimedia.org" not in url:
        return None
    m = re.search(r"/(?:wiki|File):(.+)$", url)
    if not m:
        return None
    return "File:" + urllib.parse.unquote(m.group(1).split("#")[0]).replace("_", " ")


def fetch_categories(titles):
    """title -> list of category names, for a batch of file titles."""
    q = urllib.parse.urlencode({
        "action": "query", "titles": "|".join(titles),
        "prop": "categories", "cllimit": "500", "clshow": "!hidden",
        "format": "json", "formatversion": "2",
    })
    data = json.loads(F.get(API + "?" + q))
    out = {}
    for p in (data.get("query") or {}).get("pages") or []:
        if p.get("missing"):
            out[p["title"]] = None
            continue
        out[p["title"]] = [c["title"] for c in (p.get("categories") or [])]
    # Commons normalises titles; map the request back onto the response.
    for norm in (data.get("query") or {}).get("normalized") or []:
        if norm["to"] in out:
            out[norm["from"]] = out[norm["to"]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "tools", "_image_subjects.json"))
    args = ap.parse_args()

    doc = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))
    have = [r for r in doc["recipes"] if r.get("image")]
    jobs = []
    for r in have:
        t = commons_title(r["image"].get("sourceUrl"))
        if t:
            jobs.append((r, t))

    print("%d recipes with a photograph; %d of them sourced from Commons"
          % (len(have), len(jobs)))

    cats = {}
    for i in range(0, len(jobs), BATCH):
        chunk = [t for _, t in jobs[i:i + BATCH]]
        try:
            cats.update(fetch_categories(chunk))
        except Exception as e:
            print("  ! batch %d failed: %s" % (i // BATCH, e))
        time.sleep(PAUSE)
        sys.stdout.write("\r  checked %d/%d" % (min(i + BATCH, len(jobs)), len(jobs)))
        sys.stdout.flush()
    print()

    report = {"wrong": [], "unverified": [], "gone": []}
    for r, title in jobs:
        c = cats.get(title)
        if c is None:
            report["gone"].append({"id": r["id"], "name": r["name"], "title": title})
            continue
        blob = " ; ".join(c)
        entry = {"id": r["id"], "name": r["name"], "title": title,
                 "categories": [x.replace("Category:", "") for x in c][:12]}
        if F.NOT_FOOD_CAT.search(blob):
            entry["hit"] = F.NOT_FOOD_CAT.search(blob).group(0)
            report["wrong"].append(entry)
        elif not F.FOOD_CAT.search(blob + " " + title):
            report["unverified"].append(entry)

    json.dump(report, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for k in ("wrong", "gone", "unverified"):
        print("%-11s %d" % (k, len(report[k])))
    print("\nwrong subjects:")
    for e in report["wrong"]:
        print("  %-28s %-34s matched %r" % (e["id"], e["title"][:34], e["hit"]))
    print("\nwritten to %s" % os.path.relpath(args.out, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
