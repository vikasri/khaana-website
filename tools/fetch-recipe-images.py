#!/usr/bin/env python3
"""Fetch a freely-licensed photo for every recipe that still has none.

    python3 tools/fetch-recipe-images.py            # all remaining
    python3 tools/fetch-recipe-images.py --limit 40 # a slice, for a trial run
    python3 tools/fetch-recipe-images.py --region Bengali

Writes assets/images/recipes/<id>.jpg, sets the recipe's image object in
data/recipes.json, and appends the attribution to assets/images/credits.json in
the same pass. Nothing gets published without its credit, because the two are
written together rather than in separate steps that can drift.

Resumable. Recipes that already have an image are skipped, and progress is
flushed to disk every SAVE_EVERY recipes, so an interrupted run loses at most
that many and re-running continues where it stopped.

Licences: CC0, public domain, CC BY, CC BY-SA are accepted. NC and ND are
rejected — NC because the site may one day carry ads, ND because it forbids the
resizing this script does.

On matching: Commons search is relevance-ranked, not content-verified. A
filename guard is still applied, because without one a search for "Akuri"
returns a portrait photograph of a person and a search for "dham" returns a
decorated temple. The guard is deliberately loose — a related or approximate
dish photo is acceptable — but a hit sharing no word with the dish name is not.
"""
import argparse, io, json, os, re, sys, time
import urllib.parse, urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "images", "recipes")
RECIPES = os.path.join(ROOT, "data", "recipes.json")
CREDITS = os.path.join(ROOT, "assets", "images", "credits.json")
FAILED = os.path.join(ROOT, "tools", "_image_failures.json")
API = "https://commons.wikimedia.org/w/api.php"
UA = "KhaanaSiteBot/1.0 (https://khaana.com; hello@khaana.com)"

OK_LICENCE = re.compile(r"^(cc0|public domain|cc by(-sa)?[\s-]|cc by(-sa)?$)", re.I)
BAD_LICENCE = re.compile(r"(\bnc\b|non[- ]commercial|\bnd\b|no[- ]deriv|fair use)", re.I)

MAX_W = 1000          # plenty for a card or a recipe page
TARGET_KB = 190
SAVE_EVERY = 10
PAUSE = 0.45          # be polite to Commons

STOP = {"and", "with", "the", "of", "in", "a", "ka", "ki", "ke", "style",
        "curry", "masala", "indian", "recipe", "dish", "fry", "gravy"}

# A filename guard alone is not enough. "Ball Curry" matched a photograph of a
# basketball game on the word "ball"; "Akuri" once matched a portrait of a
# person. Commons categorises its files, so requiring a food category rejects
# that whole class of hit rather than blacklisting words one at a time.
FOOD_CAT = re.compile(
    r"(food|cuisine|dish|dishes|cook|cookery|culinary|meal|snack|dessert|sweets?|"
    r"confection|curr(y|ies)|rice|bread|noodle|soup|stew|kebab|biryani|pickle|"
    r"chutney|beverage|drink|restaurant|recipes?|gastronom|edible|fruit|vegetable|"
    r"meat|seafood|fish dish|poultry|dairy|cheese|pastry|cake|breakfast)", re.I)
# Strong signals that the subject is not a plate of food.
NOT_FOOD_CAT = re.compile(
    r"(basketball|football|cricket|sport|athlet|player|portrait|people of|"
    r"musician|actor|politic|temple|mosque|church|building|architect|monument|"
    r"map(s)? of|logo|coat of arms|flag|aircraft|vehicle|railway station)", re.I)


def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def tokens(s):
    return {w for w in re.split(r"[^a-z0-9]+", s.lower()) if len(w) > 2 and w not in STOP}


def name_ok(term, title):
    """Loose subject guard: the filename must share a word with the dish name.

    Substring rather than equality, because Commons runs words together
    ("Palakpaneer_Rayagada.jpg"). Loose enough to accept a near neighbour of the
    dish, strict enough that "Akuri" cannot return a portrait of a person.
    """
    want = tokens(term)
    if not want:
        return True
    fname = re.split(r"[^a-z0-9]+", title.lower())
    return any(any(w in tok or tok in w for tok in fname if len(tok) > 2) for w in want)


def search(term, limit=8):
    q = urllib.parse.urlencode({
        "action": "query", "generator": "search",
        "gsrsearch": "filetype:bitmap " + term, "gsrnamespace": "6",
        "gsrlimit": str(limit), "prop": "imageinfo|categories",
        "iiprop": "url|extmetadata|size", "iiurlwidth": str(MAX_W),
        "cllimit": "60", "clshow": "!hidden", "format": "json",
    })
    data = json.loads(get(API + "?" + q))
    pages = (data.get("query") or {}).get("pages") or {}
    return sorted(pages.values(), key=lambda p: p.get("index", 999))


def candidate(page, term):
    ii = (page.get("imageinfo") or [{}])[0]
    m = ii.get("extmetadata", {})
    lic = ((m.get("LicenseShortName", {}) or {}).get("value", "") or "").strip()
    if not lic or BAD_LICENCE.search(lic) or not OK_LICENCE.search(lic):
        return None
    if not name_ok(term, page.get("title", "")):
        return None
    cats = " ; ".join(c.get("title", "") for c in (page.get("categories") or []))
    if NOT_FOOD_CAT.search(cats):
        return None
    # No categories at all is treated as unverified rather than fine.
    if not FOOD_CAT.search(cats + " " + page.get("title", "")):
        return None
    url = ii.get("thumburl") or ii.get("url")
    if not url:
        return None
    return {
        "title": page.get("title", "").replace("File:", ""),
        "url": url,
        "license": lic,
        "artist": strip_html((m.get("Artist", {}) or {}).get("value", "")) or "Unknown",
        "source_url": ii.get("descriptionurl", ""),
    }


def save_jpeg(data, dest):
    im = Image.open(io.BytesIO(data))
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    for q in (82, 74, 66, 58):
        im.save(dest, "JPEG", quality=q, optimize=True, progressive=True)
        if os.path.getsize(dest) <= TARGET_KB * 1024:
            break
    return im.size, os.path.getsize(dest)


def terms_for(r):
    """Search terms, most specific first."""
    name = r["name"]
    out = [name]
    if r.get("region") and r["region"].lower() not in name.lower():
        out.append("%s %s" % (name, r["region"].split("/")[0]))
    # drop a leading region word the dish name may already carry
    bare = re.sub(r"^(hyderabadi|bengali|punjabi|goan|kashmiri|andhra|kerala|sindhi|parsi|"
                  r"rajasthani|gujarati|awadhi|lucknowi|odia|bihari|karnataka|tamil)\s+",
                  "", name, flags=re.I)
    if bare != name:
        out.append(bare)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--region")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    doc = json.load(open(RECIPES, encoding="utf-8"))
    creds = json.load(open(CREDITS, encoding="utf-8"))
    have_cred = {c["file"] for c in creds}
    failures = json.load(open(FAILED, encoding="utf-8")) if os.path.exists(FAILED) else {}

    # No two recipes should carry the same photograph. This lived only in the
    # second-pass script, so a plain run could and did hand one file to two
    # dishes: both kathi rolls got the same picture, and chicken biryani took
    # the Chettinad biryani's.
    taken = {c.get("source_url") for c in creds if c.get("source_url")}

    todo = [r for r in doc["recipes"] if not r.get("image")]
    if args.region:
        todo = [r for r in todo if r["region"] == args.region]
    if args.limit:
        todo = todo[:args.limit]

    print("recipes needing a photo: %d\n" % len(todo))
    got = 0

    def flush():
        json.dump(doc, open(RECIPES, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        json.dump(creds, open(CREDITS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        json.dump(failures, open(FAILED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    for n, r in enumerate(todo, 1):
        hit = None
        for term in terms_for(r):
            try:
                for page in search(term):
                    hit = candidate(page, term)
                    if hit and hit["source_url"] in taken:
                        hit = None
                        continue
                    if hit:
                        break
            except Exception as e:
                failures[r["id"]] = "search error: %s" % e
            if hit:
                break
            time.sleep(PAUSE)
        if not hit:
            failures[r["id"]] = "no freely-licensed match"
            print("  -  %-34s %s" % (r["name"][:34], "no match"))
            continue

        dest = os.path.join(OUT_DIR, r["id"] + ".jpg")
        try:
            (w, h), size = save_jpeg(get(hit["url"]), dest)
        except Exception as e:
            failures[r["id"]] = "download/encode error: %s" % e
            print("  !  %-34s %s" % (r["name"][:34], e))
            continue

        taken.add(hit["source_url"])
        rel = "assets/images/recipes/%s.jpg" % r["id"]
        r["image"] = {"src": rel, "alt": r["name"], "credit": hit["artist"][:80],
                      "license": hit["license"], "sourceUrl": hit["source_url"]}
        key = "recipes/%s.jpg" % r["id"]
        if key not in have_cred:
            creds.append({"file": key, "region": r["region"], "slot": "recipe",
                          "wiki_title": hit["title"], "source_url": hit["source_url"],
                          "license": hit["license"], "artist": hit["artist"][:80],
                          "note": "fetched by tools/fetch-recipe-images.py"})
            have_cred.add(key)
        failures.pop(r["id"], None)
        got += 1
        print("  +  %-34s %-14s %4dx%-4d %3.0f KB  %s"
              % (r["name"][:34], hit["license"], w, h, size / 1024, hit["artist"][:22]))

        if got % SAVE_EVERY == 0:
            flush()
            print("     ... saved (%d/%d done, %d fetched)" % (n, len(todo), got))
        time.sleep(PAUSE)

    flush()
    total = sum(1 for x in doc["recipes"] if x.get("image"))
    print("\nfetched %d of %d attempted" % (got, len(todo)))
    print("recipes with a photo: %d of %d" % (total, len(doc["recipes"])))
    print("unmatched recorded in tools/_image_failures.json: %d" % len(failures))
    return 0


if __name__ == "__main__":
    sys.exit(main())
