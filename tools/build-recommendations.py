#!/usr/bin/env python3
"""Generate recommendations.html, a curated seven.

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
  * One region each, and one protein source each. Seven Punjabi chicken
    dishes would be a truthful answer to the calorie question and a useless
    answer to the question anyone is actually asking. The first draft of this
    page had three fish dishes and no chicken at all, which is why both rules
    are checked below rather than left to whoever edits PICKS.

Run after build-nutrition.py. It must be followed by sync-chrome.py and
sync-contact.py, not just build-seo.py and version-assets.py: the nav and
footer here are copied from cook.html with the active state stripped, so
until those two run the page is missing its own highlighted nav item and its
feedback link. Running this tool last leaves both quietly wrong.
"""
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "recommendations.html")

# (recipe id, protein source, note). The source is named rather than guessed
# from the ingredients, which would put pork and paneer in the wrong bucket,
# and it is checked for duplicates below.
#
# Order: the four that carry real protein first, the drink last because it is
# the one nobody expects.
PICKS = [
    ("fish-tikka", "fish",
     "Half the calories here are protein, the highest ratio of anything on the "
     "site. Yogurt, spice and a very hot oven do all the work, and nothing is "
     "fried at any point."),
    # "needs almost no fat" was wrong: the recipe griddles it in 3 tbsp of
    # ghee and comes to 14.1 g of fat a serving. "The leanest red meat dish we
    # have" was wrong too -- it is third of the sixty-two mutton dishes by fat,
    # behind rissoles and dalcha.
    ("patthar-ka-gosht", "mutton",
     "Cooked on a slab of heated stone rather than in a pan of gravy, so the "
     "fat is the three tablespoons of ghee the griddle takes and nothing more. "
     "Third leanest of our sixty-two mutton dishes."),
    # The leftovers story is the usual account of the dish, not a documented
    # one, and the page said it as fact.
    ("jalfrezi", "chicken",
     "The leanest chicken here. It is usually told as an Anglo-Indian way of "
     "using up yesterday's roast, though that origin is repeated more often "
     "than it is evidenced. Chilli, onion and vinegar."),
    ("parsi-akuri", "egg",
     "Eggs scrambled soft and slow with onion, chilli and coriander. Eighteen "
     "grams of protein and about ten minutes, which is most of the argument "
     "for eggs in one dish."),
    ("arhar-ki-dal-awadhi", "lentils",
     "Eaten daily across most of north India and written about almost never. "
     "Twelve grams of protein and no technique to speak of."),
    ("ulavacharu", "horse gram",
     "A thin dark broth cooked down from horse gram, which carries more "
     "protein than most pulses grown anywhere. Andhra has been drinking it for "
     "centuries without the help of a marketing department."),
    # "two centuries ahead of the supplement aisle" put a date on something
    # nothing here can date. The protein figure is ours and can stay.
    ("namkeen-sattu-sharbat", "roasted gram",
     "Eleven grams of protein in a glass of roasted gram flour, salt and "
     "lemon, drunk in Bihar long before anyone sold protein by the tub."),
]

INTRO = ("Seven worth cooking, one from each regional kitchen and no two "
         "leaning on the same thing for their protein.")


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

    missing = [i for i, _, _ in PICKS if i not in by_id]
    if missing:
        print("  ! no such recipe: %s" % ", ".join(missing))
        return 1

    # A pick whose confidence has since dropped is a broken promise, not a
    # cosmetic problem, so it stops the build rather than printing quietly.
    weak = [i for i, _, _ in PICKS
            if (by_id[i].get("nutrition") or {}).get("confidence") != "good"]
    if weak:
        print("  ! these picks are no longer a Good-confidence estimate: %s"
              % ", ".join(weak))
        return 1

    # The page is titled "Seven Healthy Indian Recipes". That claim has to
    # survive a change to what the site means by healthy, and once it did not:
    # a sattu drink sat here as a healthy pick while the tag rule refused it,
    # because the rule did not recognise gram flour as a pulse. Warned rather
    # than fatal -- the picks are curated and swapping one is an editorial
    # decision, not something a build script should force at 3am.
    untagged = [i for i, _, _ in PICKS if "healthier" not in by_id[i].get("tags", [])]
    if untagged:
        print("  ! picked as healthy but no longer carry the healthier tag: %s"
              % ", ".join(untagged))

    # Diversity is the whole point of a list of seven, and it is the thing
    # that quietly rots as picks get swapped. The first draft ran three fish
    # dishes and no chicken. Checked, not remembered.
    for label, idx in [("region", None), ("protein source", 1)]:
        vals = ([by_id[i]["region"] for i, _, _ in PICKS] if idx is None
                else [p[1] for p in PICKS])
        dupes = {v for v in vals if vals.count(v) > 1}
        if dupes:
            print("  ! more than one pick shares a %s: %s"
                  % (label, ", ".join(sorted(dupes))))
            return 1

    items = []
    for n, (rid, source, note) in enumerate(PICKS, 1):
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
    # Was "Seven Healthy Indian Recipes". The picks are chosen on two numbers
    # -- calories and protein -- and "healthy" claims a great deal more than
    # two numbers can carry: nothing here weighs sodium, fibre balance or how
    # realistic the portion is. The title now says what the selection actually
    # did, and the sentence under it gives the rule so a reader can check it.
    title = "Seven High-Protein Indian Recipes Worth Cooking"
    desc = ("Seven Indian recipes from seven regional kitchens, each between "
            "190 and 340 kcal a serving with protein well above the site median, "
            "chosen from the dishes whose figures we can stand behind.")

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
      <h1>Seven high-protein recipes worth cooking</h1>
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
    print("wrote recommendations.html with %d picks" % len(PICKS))
    for rid, source, _ in PICKS:
        r = by_id[rid]
        ps = r["nutrition"]["perServing"]
        print("   %-24s %-16s %-12s %3d kcal  %4.1f g"
              % (rid, r["region"][:16], source, ps["kcal"], ps["protein"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
