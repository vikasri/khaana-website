#!/usr/bin/env python3
"""Link each "Signature dishes" bullet on a region page to its recipe.

    python3 tools/link-dishes.py

Matching is deliberately conservative: a bullet is only linked to a recipe in
the SAME region whose name it contains or is contained by. Linking the wrong
recipe is worse than linking none, so anything the rule cannot settle is either
listed in OVERRIDES with a reason or left unlinked.

Re-running is safe — a bullet that already carries a link is skipped, so this
can be run again after editing a region page.
"""
import json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAGE_REGION = {
 "awadhi-lucknowi.html": "Awadhi/Lucknowi", "kashmiri.html": "Kashmiri",
 "punjabi.html": "Punjabi", "rajasthani.html": "Rajasthani",
 "gujarati.html": "Gujarati", "maharashtrian.html": "Maharashtrian",
 "goan.html": "Goan", "kerala.html": "Kerala", "south-indian.html": "South Indian",
 "hyderabadi.html": "Hyderabadi", "odia.html": "Odia", "bengali.html": "Bengali",
 "northeast-indian.html": "Northeast Indian", "bihari.html": "Bihari",
}

# Bullets the name rule cannot resolve on its own. Each entry is a decision,
# not a guess, so the reason is recorded next to it.
OVERRIDES = {
 # Spelling differs between the page and the recipe title.
 ("bengali.html", "Machher jhol"):    "macher-jhol",
 ("odia.html", "Chungudi malai"):     "chungdi-malai",
 # Several recipes share the bullet's name; these pick the one the bullet means.
 ("kashmiri.html", "Yakhni"):         "mutton-yakhni",     # nadru yakhni is the lotus-stem variant
 ("odia.html", "Pakhala"):            "dahi-pakhala",      # the yogurt version is the everyday one
 ("rajasthani.html", "Kachori"):      "pyaaz-kachori",     # the Jodhpur onion kachori is the icon
 ("south-indian.html", "Dosa"):       "masala-dosa",       # rava dosa is the variant, not the default
 ("northeast-indian.html", "Momos and thukpa"): "momos",   # one bullet, two dishes; links the first
}

# Bullets with no recipe behind them, recorded so the gaps are visible rather
# than silently unlinked: Kahwa, Sadya, Thalassery biryani, Duck roast,
# Kolhapuri mutton (only the chicken version exists — a different dish),
# Bamboo shoot pickle, Rasagola (Pahala), Amritsari kulcha, Lassi, Filter
# coffee, Champaran ahuna mutton, and Bihari khaja (the only khaja recipe is
# the Odia one, and linking across regions would misattribute it).


def norm(s):
    s = unicodedata.normalize("NFKD", s).replace("&amp;", "&")
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def phrases(dish):
    """Every phrase worth trying for one bullet: the whole label, anything in
    parentheses, and each half of a compound such as 'Fafda-jalebi'."""
    parts = [dish] + re.findall(r"\(([^)]*)\)", dish)
    parts += re.split(r"\s*(?:&amp;|&|\band\b|/|-)\s*", re.sub(r"\([^)]*\)", " ", dish))
    out, seen = [], set()
    for p in parts:
        n = norm(p)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def main():
    db = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))
    ids = {r["id"] for r in db["recipes"]}
    by_region = {}
    for r in db["recipes"]:
        by_region.setdefault(r["region"], []).append((norm(r["name"]), r["id"]))

    for key, rid in OVERRIDES.items():
        if rid not in ids:
            print("  ! override points at a missing recipe: %s -> %s" % (key, rid))
            return 1

    linked = skipped = unlinked = 0
    for page, region in sorted(PAGE_REGION.items()):
        path = os.path.join(ROOT, page)
        src = open(path, encoding="utf-8").read()
        pool = by_region.get(region, [])

        def repl(m):
            nonlocal linked, skipped, unlinked
            whole, dish, body = m.group(0), m.group(1), m.group(2)
            if "dish-recipe" in body:
                skipped += 1
                return whole
            rid = OVERRIDES.get((page, dish))
            if not rid:
                hits = []
                for cand in phrases(dish):
                    ct = set(cand.split())
                    for rn, rid_ in pool:
                        rt = set(rn.split())
                        if cand == rn or ct <= rt or rt <= ct:
                            hits.append((len(rt ^ ct), rid_))
                    if hits:
                        break
                hits.sort()
                # Ambiguity is a reason to stop, not to pick the first one.
                if hits and len([h for h in hits if h[0] == hits[0][0]]) == 1:
                    rid = hits[0][1]
            if not rid:
                unlinked += 1
                return whole
            linked += 1
            # body already excludes </li>; rstrip(chars) here would eat real
            # letters off the end of the sentence.
            return ('<li><strong>%s</strong>%s <a class="dish-recipe" href="recipe.html?id=%s">'
                    'Recipe &rarr;</a></li>' % (dish, body.rstrip(), rid))

        new = re.sub(r"<li><strong>(.*?)</strong>(.*?)</li>", repl, src, flags=re.S)
        if new != src:
            open(path, "w", encoding="utf-8").write(new)

    print("linked   : %d" % linked)
    print("already  : %d" % skipped)
    print("no recipe: %d  (left as plain text)" % unlinked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
