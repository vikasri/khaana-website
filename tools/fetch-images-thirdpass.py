#!/usr/bin/env python3
"""Last pass: three routes Commons keyword search cannot reach on its own.

    python3 tools/fetch-images-thirdpass.py

Passes one and two searched Commons for the dish name, then for the kind of
dish. What is left is 27 recipes where both failed, usually because the dish is
regional enough that Commons has no file naming it.

Three broader routes, tried in order:

  1. Wikipedia. If an article exists, its lead image is almost always a good
     photograph of the subject, and it lives on Commons with full licence
     metadata. Wikipedia's own search is far better at Indian dish names than
     a Commons filename match — it knows "Zunka" and "Gundruk".

  2. Hand-written alternate names. A short table, because at this size naming
     the dish properly is cheaper than any heuristic: Bhee is lotus root,
     Ravo is a semolina pudding, Kane is ladyfish.

  3. The region's Commons category. Failing everything else, take an unused
     food photograph from that cuisine's own category. Broad, but it is at
     least the right regional kitchen.

Licence filtering, the food-category gate and site-wide de-duplication are all
inherited from tools/fetch-recipe-images.py.
"""
import importlib.util, json, os, re, sys, time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "fetcher", os.path.join(ROOT, "tools", "fetch-recipe-images.py"))
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

WIKI = "https://en.wikipedia.org/w/api.php"

# Route 2. What the dish actually is, in words Commons has heard of.
ALIAS = {
    "ulavacharu": ["horse gram soup", "horse gram rasam", "kollu rasam"],
    "anarsa": ["Anarsa sweet", "Anarsa"],
    "badanekayi-ennegayi": ["Ennegayi", "stuffed brinjal curry", "gutti vankaya"],
    "kane-rava-fry": ["rava fried fish", "fish rava fry", "Mangalorean fish fry"],
    "kumm-curry": ["mushroom curry dish", "mushroom masala curry"],
    "modur-pulav": ["sweet saffron rice", "zarda rice", "meethe chawal"],
    "roth": ["Kashmiri sweet bread", "roat bread"],
    "tehar": ["turmeric rice", "yellow rice indian"],
    "kothimbir-vadi": ["Kothimbir vadi", "coriander vadi"],
    "zunka": ["Zunka", "Zunka bhakar", "pithla"],
    "gundruk-ko-jhol": ["Gundruk", "gundruk soup"],
    "omita-khar": ["Khar Assamese dish", "Assamese khar"],
    "ooti": ["Manipuri peas dish", "Manipuri cuisine dish"],
    "pika-pila": ["Apatani cuisine", "bamboo shoot pickle"],
    "sanpiau": ["Mizo rice porridge", "Mizo cuisine dish"],
    "chhatu-rai": ["mushroom curry dish", "mushroom mustard curry"],
    "saja-pakhala": ["Pakhala", "pakhala bhata"],
    "arsa": ["Arsa sweet", "rice flour jaggery sweet"],
    "kullu-trout": ["fried trout dish", "trout fry", "grilled trout plate"],
    "dar-ni-pori": ["Dar ni pori", "Parsi sweet pastry"],
    "lagan-nu-custard": ["Lagan nu custard", "Parsi custard", "baked custard"],
    "ravo": ["semolina pudding", "sooji halwa", "rava kesari"],
    "bharwa-karela": ["stuffed bitter gourd dish", "bharwa karela"],
    "bhee-patata": ["lotus root curry", "lotus stem curry", "kamal kakdi"],
    "bhuga-chawal": ["brown onion rice", "Sindhi rice dish"],
    "seyal-bhaji": ["Sindhi cauliflower curry", "coriander potato curry"],
    "kootu": ["Kootu", "kootu dish"],
}

# Route 3.
REGION_CAT = {
    "Andhra": "Category:Cuisine of Andhra Pradesh",
    "Bihari": "Category:Bihari cuisine",
    "Karnataka": "Category:Cuisine of Karnataka",
    "Kashmiri": "Category:Kashmiri cuisine",
    "Maharashtrian": "Category:Maharashtrian cuisine",
    "Northeast Indian": "Category:Cuisine of Northeast India",
    "Odia": "Category:Odia cuisine",
    "Pahari": "Category:Himachali cuisine",
    "Parsi": "Category:Parsi cuisine",
    "Punjabi": "Category:Punjabi cuisine",
    "Sindhi": "Category:Sindhi cuisine",
    "Tamil Nadu": "Category:Tamil cuisine",
}


def wiki_lead_file(term):
    """The Commons filename behind an article's lead image."""
    q = urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrsearch": term,
        "gsrlimit": "3", "gsrnamespace": "0", "prop": "pageimages",
        "piprop": "name", "format": "json"})
    try:
        data = json.loads(F.get(WIKI + "?" + q))
    except Exception:
        return None
    pages = sorted(((data.get("query") or {}).get("pages") or {}).values(),
                   key=lambda p: p.get("index", 99))
    for p in pages:
        if p.get("pageimage"):
            return p["pageimage"], p.get("title", "")
    return None


def commons_file(filename):
    """Full imageinfo for one Commons file, shaped like a search hit."""
    q = urllib.parse.urlencode({
        "action": "query", "titles": "File:" + filename,
        "prop": "imageinfo|categories", "iiprop": "url|extmetadata|size",
        "iiurlwidth": str(F.MAX_W), "cllimit": "60", "clshow": "!hidden",
        "format": "json"})
    try:
        data = json.loads(F.get(F.API + "?" + q))
        return list(((data.get("query") or {}).get("pages") or {}).values())[0]
    except Exception:
        return None


def category_members(cat, limit=40):
    q = urllib.parse.urlencode({
        "action": "query", "generator": "categorymembers", "gcmtitle": cat,
        "gcmtype": "file", "gcmlimit": str(limit), "prop": "imageinfo|categories",
        "iiprop": "url|extmetadata|size", "iiurlwidth": str(F.MAX_W),
        "cllimit": "60", "clshow": "!hidden", "format": "json"})
    try:
        data = json.loads(F.get(F.API + "?" + q))
        return list(((data.get("query") or {}).get("pages") or {}).values())
    except Exception:
        return []


def main():
    doc = json.load(open(F.RECIPES, encoding="utf-8"))
    creds = json.load(open(F.CREDITS, encoding="utf-8"))
    have_cred = {c["file"] for c in creds}
    taken = {c.get("source_url") for c in creds if c.get("source_url")}

    todo = [r for r in doc["recipes"] if not r.get("image")]
    print("recipes still without a photo: %d\n" % len(todo))
    got = 0

    def accept(page, term):
        """Licence + food-category gates, minus the filename check."""
        old = F.name_ok
        F.name_ok = lambda t, ti: True
        try:
            c = F.candidate(page, term)
        finally:
            F.name_ok = old
        if not c or c["source_url"] in taken:
            return None
        return c

    for r in todo:
        hit, how = None, ""

        # 1. Wikipedia lead image
        lead = wiki_lead_file(r["name"] + " " + r["region"].split("/")[0]) \
            or wiki_lead_file(r["name"])
        if lead:
            page = commons_file(lead[0])
            if page:
                hit = accept(page, r["name"])
                if hit:
                    how = "wikipedia:%s" % lead[1][:28]
        time.sleep(F.PAUSE)

        # 2. hand-written alternate names
        if not hit:
            for alt in ALIAS.get(r["id"], []):
                try:
                    for p in F.search(alt):
                        hit = accept(p, alt)
                        if hit:
                            how = "alias:%s" % alt
                            break
                except Exception:
                    pass
                if hit:
                    break
                time.sleep(F.PAUSE)

        # 3. the region's own Commons category
        if not hit:
            cat = REGION_CAT.get(r["region"])
            if cat:
                for p in category_members(cat):
                    hit = accept(p, r["name"])
                    if hit:
                        how = "category:%s" % cat.replace("Category:", "")[:28]
                        break
                time.sleep(F.PAUSE)

        if not hit:
            print("  -  %-26s no match on any route" % r["name"][:26])
            continue

        dest = os.path.join(F.OUT_DIR, r["id"] + ".jpg")
        try:
            (w, h), size = F.save_jpeg(F.get(hit["url"]), dest)
        except Exception as e:
            print("  !  %-26s %s" % (r["name"][:26], e))
            continue

        taken.add(hit["source_url"])
        r["image"] = {"src": "assets/images/recipes/%s.jpg" % r["id"], "alt": r["name"],
                      "credit": hit["artist"][:80], "license": hit["license"],
                      "sourceUrl": hit["source_url"]}
        key = "recipes/%s.jpg" % r["id"]
        if key not in have_cred:
            creds.append({"file": key, "region": r["region"], "slot": "recipe",
                          "wiki_title": hit["title"], "source_url": hit["source_url"],
                          "license": hit["license"], "artist": hit["artist"][:80],
                          "note": "third pass via " + how})
            have_cred.add(key)
        got += 1
        print("  +  %-26s %-14s %-30s %s"
              % (r["name"][:26], hit["license"], how[:30], hit["title"][:34]))

        json.dump(doc, open(F.RECIPES, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        json.dump(creds, open(F.CREDITS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        time.sleep(F.PAUSE)

    total = sum(1 for x in doc["recipes"] if x.get("image"))
    print("\nfetched %d of %d" % (got, len(todo)))
    print("recipes with a photo: %d of %d" % (total, len(doc["recipes"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
