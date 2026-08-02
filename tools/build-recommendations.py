#!/usr/bin/env python3
"""Generate healthy.html, a curated seven.

    python3 tools/build-recommendations.py

The picks and the notes below are editorial and belong to a person. Everything
else on the page is read from data/recipes.json at build time, so if the
nutrition is ever recomputed the page moves with it rather than quietly going
stale. That matters here more than elsewhere: a page whose entire claim is
"these are the light ones" is worthless the moment its numbers stop matching
the recipes they point at.

Two rules held while choosing:

  * Good confidence only. A third of the site's nutrition figures are marked
    Medium or Low because much of the ingredient list is given to taste. Those
    may well be lighter than what is here, but "healthy" is a claim, and a
    claim wants the numbers that can carry it.
  * One region each, and both diet types. Seven Punjabi chicken dishes would
    be a truthful answer to the calorie question and a useless answer to the
    question anyone is actually asking.

Run after build-nutrition.py, and before build-seo.py and version-assets.py.
"""
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "healthy.html")

# (recipe id, the note). Order is the order on the page: the two leanest meat
# dishes first because they are the surprise, the drink last for the same
# reason.
PICKS = [
    ("fish-tikka",
     "Half the calories here are protein, the highest ratio of anything on the "
     "site. Yogurt, spice and a very hot oven do all the work, and nothing is "
     "fried at any point."),
    ("patthar-ka-gosht",
     "Cooked on a slab of heated stone, which sounds like a restaurant gimmick "
     "and is in fact the reason it needs almost no fat. The leanest red meat "
     "dish we have."),
    ("nga-thongba",
     "A fish curry with nothing rich anywhere in it: no cream, no coconut, no "
     "cashew paste. Manipur has been cooking this way for a long time without "
     "ever needing a word for it."),
    ("parsi-patra-ni-machhi",
     "Packed in green chutney and steamed inside a banana leaf, so nothing "
     "fries and nothing dries out. The lightest thing on this list by a "
     "distance."),
    ("pithla",
     "Gram flour, water, and about ten minutes. This is what gets made when "
     "there is nothing in the house, which is precisely the moment most people "
     "reach for a menu instead."),
    ("arhar-ki-dal-awadhi",
     "Eaten daily across most of north India and written about almost never. "
     "Twelve grams of protein and no technique to speak of."),
    ("namkeen-sattu-sharbat",
     "Eleven grams of protein in a glass of roasted gram flour, salt and "
     "lemon. Bihar arrived at the protein shake roughly two centuries ahead of "
     "the supplement aisle."),
]

INTRO = ("Seven that are worth cooking, not seven that are merely low in "
         "something. Each is picked from the recipes whose nutrition we can "
         "stand behind, and no two come from the same regional kitchen.")


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def chrome():
    """The nav and footer exactly as the shared tools write them."""
    src = open(os.path.join(ROOT, "cook.html"), encoding="utf-8").read()
    nav = re.search(r'<header class="site-header">.*?</header>', src, re.S).group(0)
    nav = nav.replace(' class="active"', '')
    foot = re.search(r'<footer class="site-footer">.*?</footer>', src, re.S).group(0)
    return nav, foot


def main():
    db = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))
    by_id = {r["id"]: r for r in db["recipes"]}

    missing = [i for i, _ in PICKS if i not in by_id]
    if missing:
        print("  ! no such recipe: %s" % ", ".join(missing))
        return 1

    # A pick whose confidence has since dropped is a broken promise, not a
    # cosmetic problem, so it stops the build rather than printing quietly.
    weak = [i for i, _ in PICKS
            if (by_id[i].get("nutrition") or {}).get("confidence") != "good"]
    if weak:
        print("  ! these picks are no longer a Good-confidence estimate: %s"
              % ", ".join(weak))
        return 1

    items = []
    for n, (rid, note) in enumerate(PICKS, 1):
        r = by_id[rid]
        ps = r["nutrition"]["perServing"]
        share = (ps["protein"] * 4) / ps["kcal"] if ps["kcal"] else 0
        img = (r.get("image") or {}).get("src") or "assets/images/home-hero.jpg"
        items.append("""      <li class="pick">
        <a class="pick-thumb" href="recipes/%s.html" tabindex="-1" aria-hidden="true">
          <img src="%s" alt="" loading="lazy" /></a>
        <div class="pick-body">
          <h2 class="pick-name"><span class="pick-num">%d</span>
            <a href="recipes/%s.html">%s</a></h2>
          <p class="pick-region">%s</p>
          <p class="pick-nums">%d kcal &middot; %.0f g protein &middot;
            %.0f%% of the calories, a serving</p>
          <p class="pick-note">%s</p>
        </div>
      </li>""" % (esc(rid), esc(img), n, esc(rid), esc(r["name"]),
                  esc(r["region"]), ps["kcal"], ps["protein"], share * 100,
                  esc(note)))

    nav, foot = chrome()
    title = "Healthy Indian Recipes: Seven Worth Cooking"
    desc = ("Seven lighter Indian recipes from seven regional kitchens, chosen "
            "from the dishes whose calorie and protein figures we can stand behind.")

    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%s | Khaana</title>
<meta name="description" content="%s" />
<link rel="stylesheet" href="style.css" />
</head>
<body>

%s
<section class="tight">
  <div class="container picks-page">
    <div class="section-head">
      <div class="eyebrow">Recommendations</div>
      <h1>Seven healthy recipes worth cooking</h1>
    </div>

    <p class="lede">%s</p>

    <ol class="pick-list">
%s
    </ol>

    <p class="picks-method">How these were chosen: every dish here has a
      <strong>Good</strong> nutrition estimate, meaning most of its ingredient
      list could actually be weighed. Recipes leaning on quantities given to
      taste are excluded, however light they may turn out to be, because a
      figure that cannot be checked is not a figure worth ranking on. The
      numbers are still estimates, and every recipe page says so.</p>
  </div>
</section>

%s

<script src="script.js"></script>
</body>
</html>
""" % (esc(title), esc(desc), nav, esc(INTRO), "\n".join(items), foot)

    open(OUT, "w", encoding="utf-8").write(page)
    print("wrote healthy.html with %d picks" % len(PICKS))
    for rid, _ in PICKS:
        r = by_id[rid]
        ps = r["nutrition"]["perServing"]
        print("   %-24s %-16s %3d kcal  %4.1f g" % (rid, r["region"][:16],
                                                    ps["kcal"], ps["protein"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
