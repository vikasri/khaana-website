#!/usr/bin/env python3
"""Generate one real HTML page per recipe, at recipes/<id>.html.

    python3 tools/build-recipe-pages.py

Why static pages rather than the existing recipe.html?id= view:

  * Link previews. WhatsApp, Facebook, Slack and X read Open Graph tags without
    executing JavaScript. Tags injected client-side are invisible to them, so
    the query-string page can never preview no matter what it injects.
  * Search. Every recipe needs its own URL, title, description and JSON-LD
    Recipe block to be eligible for a rich result. One shared template with a
    generic <title> is a single page to a crawler.

The old URL keeps working: recipe.html?id=x redirects to recipes/x.html, so
nothing already shared breaks.

Run after tools/split-recipes.py.
"""
import html, json, os, re, sys

# Shared copy. Python puts this script's own directory on sys.path, so a
# plain import finds tools/site_text.py.
import site_text as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "recipes")
SITE = "https://khaana.com"
FALLBACK_IMG = "assets/images/home-hero.jpg"

# Which collection pages a recipe belongs on, by tag. Printed at the foot of
# the page as real links: 656 recipe pages that link only upward to their own
# region leave the collection pages depending entirely on the nav, and a page
# nothing links to from the body of the site is a page search engines treat as
# an afterthought. Written the way a reader would say it, since that is also
# what someone types.
COLLECTION_FOR_TAG = [
    ("healthier",       "healthy-indian-recipes.html",     "Healthy Indian recipes"),
    ("vegan",           "vegan-indian-recipes.html",       "Vegan Indian recipes"),
    ("vegetarian",      "vegetarian-indian-recipes.html",  "Vegetarian Indian recipes"),
    ("gluten-free",     "gluten-free-indian-recipes.html", "Gluten-free Indian recipes"),
    ("dairy-free",      "dairy-free-indian-recipes.html",  "Dairy-free Indian recipes"),
    ("no-onion-garlic", "no-onion-no-garlic-recipes.html", "No onion no garlic recipes"),
    ("soup",            "indian-soup-recipes.html",        "Indian soup recipes"),
]
QUICK_PAGE = ("quick-indian-recipes.html", "Quick Indian recipes (30 min)")


def collections_for(r):
    """The collection links for one recipe, longest-tail first."""
    tags = set(r.get("tags", []))
    out = [(href, label) for tag, href, label in COLLECTION_FOR_TAG if tag in tags]
    if (r.get("prepMinutes") or 0) + (r.get("cookMinutes") or 0) <= 30:
        out.insert(0, QUICK_PAGE)
    return out


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def chrome(page_html, current="cook.html"):
    """Reuse the nav and footer exactly as sync-chrome.py writes them."""
    src = open(os.path.join(ROOT, "cook.html"), encoding="utf-8").read()
    nav = re.search(r'<header class="site-header">.*?</header>', src, re.S).group(0)
    nav = nav.replace(' class="active"', '')
    foot = re.search(r'<footer class="site-footer">.*?</footer>', src, re.S).group(0)
    # one level down, so every relative link needs ../
    nav = re.sub(r'(href|src)="(?!https?:|#|mailto:)', r'\1="../', nav)
    foot = re.sub(r'(href|src)="(?!https?:|#|mailto:)', r'\1="../', foot)
    return nav, foot


def iso_duration(mins):
    return "PT%dM" % int(mins or 0)


def human_duration(mins):
    """"8 hr", "3 days 1 hr", "45 min" — the way the stat row says it.

    Anything past a day is said in days. Anarsa's elapsed time is 4,390
    minutes and "73 hr 10 min" is a number nobody can plan around.
    """
    mins = int(mins)
    if mins >= 1440:
        d, rest = divmod(mins, 1440)
        h = round(rest / 60)
        if h == 24:                       # rounded up into the next day
            d, h = d + 1, 0
        out = "%d day%s" % (d, "" if d == 1 else "s")
        return out if not h else "%s %d hr" % (out, h)
    if mins >= 60:
        h, m = divmod(mins, 60)
        return "%d hr" % h if not m else "%d hr %d min" % (h, m)
    return "%d min" % mins


def schema(r, url, img):
    """schema.org/Recipe. Only fields we can fill honestly."""
    d = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": r["name"],
        "description": r.get("subtitle", ""),
        "url": url,
        # Search engines want a named author on a recipe, and leaving it out is
        # part of why these pages look thin to them. It is the site rather than
        # a person, so Organization is the honest type. Kept to the markup: no
        # byline is printed on the page, since a line saying who wrote it adds
        # nothing a reader of khaana.com does not already know.
        "author": {"@type": "Organization", "name": "Khaana", "url": "https://khaana.com/"},
        "recipeCuisine": r["region"],
        "recipeCategory": "Main" if "dessert" not in (r.get("subtitle") or "").lower() else "Dessert",
        # totalTime used to be prep plus cook, which on a recipe that soaks
        # its beans overnight told a search engine the dish takes 80 minutes.
        # The soak, ferment, marinade or rest goes into prepTime, which is
        # where schema.org puts getting the ingredients ready, so the three
        # figures still add up and totalTime is now elapsed time. It matches
        # the Active and Plus figures printed on the page.
        "prepTime": iso_duration((r.get("prepMinutes") or 0)
                                 + (r.get("inactiveMinutes") or 0)),
        "cookTime": iso_duration(r.get("cookMinutes")),
        "totalTime": iso_duration((r.get("prepMinutes") or 0)
                                  + (r.get("cookMinutes") or 0)
                                  + (r.get("inactiveMinutes") or 0)),
        "recipeYield": "%s servings" % r.get("servings", 4),
        "recipeIngredient": [
            (i.get("qty", "").strip() + " " + i["id"].replace("-", " ")).strip()
            for i in r["ingredients"]
        ],
        "recipeInstructions": [
            {"@type": "HowToStep", "position": n + 1, "text": s["text"]}
            for n, s in enumerate(r["steps"])
        ],
        "keywords": ", ".join([r["region"]] + list(r.get("tags", []))),
    }
    n = r.get("nutrition")
    if n:
        ps = n["perServing"]
        # Google reads these. Values are per serving, which is what the property
        # means; servingSize states the weight so the figures are interpretable.
        d["nutrition"] = {
            "@type": "NutritionInformation",
            "servingSize": "%d g" % n["servingGrams"],
            "calories": "%d kcal" % ps["kcal"],
            "proteinContent": "%.1f g" % ps["protein"],
            "carbohydrateContent": "%.1f g" % ps["carbs"],
            "fiberContent": "%.1f g" % ps["fibre"],
            "sugarContent": "%.1f g" % ps["sugars"],
            "fatContent": "%.1f g" % ps["fat"],
            "saturatedFatContent": "%.1f g" % ps["satFat"],
            "unsaturatedFatContent": "%.1f g" % (ps["monoFat"] + ps["polyFat"]),
        }
    if img:
        d["image"] = [img]
    if r.get("tags"):
        # Google understands these two as dietary restrictions.
        diets = []
        if "vegan" in r["tags"]:
            diets.append("https://schema.org/VeganDiet")
        elif "vegetarian" in r["tags"]:
            diets.append("https://schema.org/VegetarianDiet")
        if "gluten-free" in r["tags"]:
            diets.append("https://schema.org/GlutenFreeDiet")
        if diets:
            d["suitableForDiet"] = diets

    # A second graph node: where this page sits. Breadcrumbs are what turn the
    # green URL line in a result into "khaana.com > Bihari > Machhak Jhor",
    # which is both more clickable and more legible than the path.
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Khaana", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Recipes",
             "item": SITE + "/cook.html"},
        ],
    }
    if r.get("regionPage"):
        crumbs["itemListElement"].append(
            {"@type": "ListItem", "position": 3, "name": r["region"],
             "item": "%s/%s" % (SITE, r["regionPage"])})
    crumbs["itemListElement"].append(
        {"@type": "ListItem", "position": len(crumbs["itemListElement"]) + 1,
         "name": r["name"], "item": "%s/recipes/%s.html" % (SITE, r["id"])})

    return json.dumps([d, crumbs], ensure_ascii=False, indent=2)




def nutrition_panel(r):
    """Calories and macros, most important first, per serving and per 100 g."""
    n = r.get("nutrition")
    if not n:
        return ""
    ps, pc = n["perServing"], n["per100g"]
    # A floor, not an estimate: unweighable ingredients count as zero.
    # No "+" on the numbers. It was honest about the two thirds of figures
    # that are floors rather than estimates, but no other recipe site marks
    # them and it read as a typo. The caveat is kept in words below the table.
    plus = ""

    def row(label, key, unit="g", cls=""):
        return ('<tr class="%s"><th>%s</th><td>%s</td><td>%s</td></tr>'
                % (cls,
                   esc(label),
                   ("%d%s kcal" % (ps[key], plus)) if key == "kcal"
                   else ("%.1f%s %s" % (ps[key], plus, unit)),
                   # Per 100 g carries no decimals: it is a comparison figure,
                   # and a tenth of a gram per 100 g is noise on an estimate.
                   ("%d%s kcal" % (pc[key], plus)) if key == "kcal"
                   else ("%.0f%s %s" % (pc[key], plus, unit))))

    # The same two-part test the Cook page filter uses.
    share = (ps["protein"] * 4) / ps["kcal"] if ps["kcal"] else 0
    band = ("high" if ps["protein"] >= 20 and share >= 0.12
            else "medium" if ps["protein"] >= 10 else "low")

    rows = [
        row("Calories", "kcal", cls="nut-major"),
        row("Protein", "protein", cls="nut-major"),
        row("Carbohydrate", "carbs", cls="nut-major"),
        row("of which sugars", "sugars", cls="nut-sub"),
        row("Fibre", "fibre", cls="nut-sub"),
        row("Fat", "fat", cls="nut-major"),
        row("of which saturated", "satFat", cls="nut-sub"),
    ]
    unsat_s = ps["monoFat"] + ps["polyFat"]
    unsat_c = pc["monoFat"] + pc["polyFat"]
    rows.append('<tr class="nut-sub"><th>of which unsaturated</th><td>%.1f%s g</td>'
                '<td>%.0f%s g</td></tr>' % (unsat_s, plus, unsat_c, plus))

    # Three sentences at most, and usually one.
    #
    # This paragraph had grown to 640 characters and said the same thing three
    # times: a generated line about to-taste ingredients, a confidence note
    # repeating it, and a stored caveat repeating it again while pointing at a
    # "+" on the numbers that no longer exists. A caveat nobody finishes
    # reading protects nobody.
    #
    # What survives is only what is specific to this dish and said nowhere
    # else. The badge in the heading already gives the confidence level, so no
    # sentence restates it, and the provenance line further down already says
    # the nutrition is worked out rather than measured. That leaves which way
    # the error runs, which substitutions were made, and where the data came
    # from.
    notes = []
    if n.get("caveat"):
        notes.append(n["caveat"])
    elif n.get("direction") == "understated":
        notes.append(T.NUTRITION_UNDERSTATED)
    if n.get("approximated"):
        notes.append(T.nutrition_approximated(n["approximated"]))
    notes.append(T.NUTRITION_SOURCE)

    return ("""<section class="nutrition" aria-labelledby="nutrition">
        <h2 id="nutrition">Nutrition <span class="nut-conf" data-c="%s">%s estimate</span></h2>
        <p class="nut-band" data-band="%s">%s protein: <strong>%.0f%s g</strong> a serving,
          %.0f%% of the calories</p>
        <table class="nut-table">
          <thead><tr><th></th><th>Per serving<span>%d g</span></th><th>Per 100 g</th></tr></thead>
          <tbody>%s</tbody>
        </table>
        <p class="nut-note">%s</p>
      </section>""" % (n.get("confidence", "medium"), n.get("confidence", "medium").title(),
                       band, band.title(), ps["protein"], plus, share * 100,
                       n["servingGrams"], "".join(rows), " ".join(notes)))


def doneness_block(r):
    """Safe internal temperatures for whatever animal protein is in the pot.

    Under the method, not inside it. The steps keep their own cues — oil
    separating, meat pulling off the bone, fish going opaque — and this is the
    number to check them against, not a replacement for them.
    """
    keys = r.get("doneness")
    if not keys:
        return ""
    lines = [T.DONENESS[k] for k in keys if k in T.DONENESS]
    if not lines:
        return ""
    lines.append(T.DONENESS_REHEAT)
    return ('<p class="doneness"><strong>Safe temperatures:</strong> %s '
            '<span class="doneness-src">%s</span></p>'
            % (esc(" ".join(lines)), T.DONENESS_SOURCE))


def render(r, nav, foot):
    """One recipe page.

    The jump links are not decoration. On a phone the method starts about
    2,000px down and there were no anchors at all, so a cook at step six
    scrolled back through twenty ingredients to check a quantity. Sticky under
    the header on small screens; hidden on desktop, where the ingredient
    column is already sticky beside the method.

    They stay a direct child of the article, after the head, because a sticky
    element cannot escape its parent's box: moved inside .recipe-head so they
    would sit above the photo, they scrolled away with the head and were gone
    by the time the method started — losing the one thing they are for. The
    phone ordering is done in CSS instead, which is why the mobile rules
    reorder the article rather than the markup doing it.

    The scope note on the allergen check moved down to the end of the
    ingredient list: it is about that list, and it was four lines of small
    print standing between the reader and it.
    """
    rid = r["id"]
    url = "%s/recipes/%s.html" % (SITE, rid)
    img_rel = r["image"]["src"] if r.get("image") else FALLBACK_IMG
    img_abs = "%s/%s" % (SITE, img_rel)
    # "Total" was prep plus cook and was called total on 651 pages, including
    # the 141 where a required soak or ferment is longer than the whole of it.
    # Active is what that number always was; elapsed is what it claimed to be.
    active = (r.get("prepMinutes") or 0) + (r.get("cookMinutes") or 0)
    inactive = r.get("inactiveMinutes") or 0
    total = active + inactive

    # "A Andhra recipe" was going out in 89 descriptions. The article follows
    # the sound, not the letter, so this is a first-letter test plus the
    # regions that break it. None currently do (no "European", no "Uttar"),
    # but the list is where a future one goes.
    CONSONANT_SOUND = ()
    region = r["region"]
    article = "An" if (region[0].upper() in "AEIOU"
                       and not region.startswith(CONSONANT_SOUND)) else "A"
    # The minutes in a search result are a promise, so they are active minutes
    # with the wait named separately. "545 minutes" would be true of chana
    # masala and would tell nobody anything.
    wait = (" plus %s %s," % (human_duration(inactive), r.get("inactiveLabel", "resting"))
            if inactive else "")
    desc = "%s. %s %s %s recipe: %d minutes active,%s serves %s, with measured " \
           "ingredients, substitutions and storage notes." % (
               r["name"], (r.get("subtitle") or "").capitalize().rstrip(".") + ".",
               article, region, active, wait, r.get("servings", 4))
    desc = re.sub(r"\s+", " ", desc)[:300]

    ing = "\n".join(
        '        <li><span class="ing-qty">%s</span> <span class="ing-name">%s</span>%s%s</li>'
        % (esc(i.get("qty", "")), esc(i["id"].replace("-", " ").title()),
           '<span class="ing-note">%s</span>' % esc(i["note"]) if i.get("note") else "",
           '<span class="ing-opt">optional</span>' if i.get("essential") is False else "")
        for i in r["ingredients"])

    steps = "\n".join(
        '        <li>%s%s</li>' % (esc(s["text"]),
                                   '<span class="step-tip">%s</span>' % esc(s["tip"]) if s.get("tip") else "")
        for s in r["steps"])

    notes = "".join('<li>%s</li>' % esc(n) for n in r.get("prepNotes", []))
    # A tag that only holds if you leave an optional ingredient out says so.
    # Khaman Dhokla is vegan without the yogurt and gluten-free without the
    # rava, and a flat "vegan" chip describes a dish the page does not quite
    # print. The allergen line above still declares milk and gluten either way.
    cond = set(r.get("tagsConditional") or [])
    tags = "".join(
        '<span class="diet-tag%s">%s%s</span>'
        % (" diet-tag-opt" if t in cond else "", esc(t.replace("-", " ")),
           " option" if t in cond else "")
        for t in r.get("tags", []))
    # "crustacean" is the regulatory word; "crustacean shellfish" is what a
    # reader scanning the line actually recognises.
    ALLERGEN_LABEL = {"crustacean": "crustacean shellfish", "nuts": "tree nuts",
                      "peanut": "peanuts", "dairy": "milk"}
    allerg = (", ".join(ALLERGEN_LABEL.get(a, a) for a in r["allergens"])
              if r.get("allergens") else None)

    region_link = ('<a href="../%s">%s</a>' % (esc(r["regionPage"]), esc(r["region"]))
                   if r.get("regionPage") else esc(r["region"]))

    photo = ('<figure class="recipe-photo"><img src="../%s" alt="%s" />'
             '<figcaption>Photo: %s &middot; %s</figcaption></figure>'
             % (esc(r["image"]["src"]), esc(r["image"]["alt"]),
                esc(r["image"]["credit"]), esc(r["image"]["license"]))
             if r.get("image") else
             '<figure class="recipe-photo recipe-photo-none" aria-hidden="true"><span>%s</span></figure>'
             % esc(r["name"][:1]))

    nutrition_html = nutrition_panel(r)
    doneness_html = doneness_block(r)

    colls = collections_for(r)
    collection_line = ('<p class="collection-links"><strong>More like this:</strong> '
                       + " &middot; ".join('<a href="../%s">%s</a>' % (h, esc(l))
                                           for h, l in colls)
                       + (' &middot; <a href="../%s">%s recipes</a>'
                          % (esc(r["regionPage"]), esc(r["region"]))
                          if r.get("regionPage") else "")
                       + '</p>') if colls or r.get("regionPage") else ""

    # The sixth stat, only where there is a wait to name. Leaving it off the
    # other 240 recipes keeps its presence meaningful.
    plus_stat = ('<div class="stat stat-plus"><span class="stat-label">Plus</span>'
                 '<span class="stat-value">%s %s</span></div>'
                 % (human_duration(inactive), esc(r.get("inactiveLabel", "resting")))
                 if inactive else "")

    # And a line telling the reader when to start, for waits long enough that
    # finding out at step one is finding out too late.
    ahead = ""
    if inactive >= 240:
        when = ("the day before" if inactive < 1440
                else "%s ahead" % human_duration(inactive))
        # Against the active figure rather than the elapsed one: "3 days, and
        # the whole thing takes 3 days 1 hr" says the same number twice, and
        # the useful comparison is how little of it is work.
        ahead = ('<p class="start-ahead">Start %s. The %s alone is %s, against '
                 '%d min of actual work.</p>'
                 % (when, esc(r.get("inactiveLabel", "resting")),
                    human_duration(inactive), active))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{esc(r['name'])} recipe | Khaana</title>
<meta name="description" content="{esc(desc)}" />
<link rel="canonical" href="{url}" />

<meta property="og:type" content="article" />
<meta property="og:site_name" content="Khaana" />
<meta property="og:title" content="{esc(r['name'])}, {esc(r['region'])} recipe" />
<meta property="og:description" content="{esc(desc)}" />
<meta property="og:url" content="{url}" />
<meta property="og:image" content="{img_abs}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{esc(r['name'])}, {esc(r['region'])} recipe" />
<meta name="twitter:description" content="{esc(desc)}" />
<meta name="twitter:image" content="{img_abs}" />

<link rel="stylesheet" href="../style.css" />
<script type="application/ld+json">
{schema(r, url, img_abs)}
</script>
</head>
<body>

{nav}

<section class="tight">
  <div class="container">
    <article id="recipe">
      <nav class="crumbs"><a href="../cook.html">&larr; Back to recipes</a></nav>
      <div class="recipe-head">
        <div class="recipe-headline">
          <div class="eyebrow">{region_link}</div>
          <h1>{esc(r['name'])}<button type="button" class="save-btn"
              data-save-id="{esc(rid)}" aria-pressed="false"
              aria-label="Save this recipe"></button></h1>
          <p class="lede">{esc(r.get('subtitle',''))}</p>
          <div class="diet-tags">{tags}</div>
        </div>
        {photo}
      </div>

      <nav class="recipe-jump" aria-label="Jump to a section">
        <a href="#ingredients">Ingredients</a>
        <a href="#method">Method</a>
        <a href="#nutrition">Nutrition</a>
      </nav>

      <div class="recipe-stats">
        <div class="stat"><span class="stat-label">Prep</span><span class="stat-value">{r.get('prepMinutes',0)} min</span></div>
        <div class="stat"><span class="stat-label">Cook</span><span class="stat-value">{r.get('cookMinutes',0)} min</span></div>
        <div class="stat"><span class="stat-label">Active</span><span class="stat-value">{active} min</span></div>
        {plus_stat}
        <div class="stat"><span class="stat-label">Serves</span><span class="stat-value">{esc(r.get('servings',4))}</span></div>
        <div class="stat"><span class="stat-label">Difficulty</span><span class="stat-value">{esc(r.get('difficulty',''))}</span></div>
      </div>
      {ahead}

      {'<p class="allergen"><strong>Contains:</strong> %s</p>' % esc(allerg) if allerg
       else f'<p class="allergen none"><strong>Allergens:</strong> {T.ALLERGEN_NONE}</p>'}

      <div class="recipe-cols">
        <div class="recipe-ing">
          <h2 id="ingredients">Ingredients</h2>
          <p class="serves-note">Quantities for {esc(r.get('servings',4))}.</p>
          <ul class="ing-list">
{ing}
          </ul>
          <h3>Cookware</h3>
          <p class="equip-line">{esc(', '.join(e.replace('-', ' ') for e in r.get('equipment', [])))}</p>
          <p class="allergen-scope">{T.ALLERGEN_SCOPE}</p>
        </div>
        <div class="recipe-method">
          {'<h2>Before you start</h2><ul class="prep-notes">%s</ul>' % notes if notes else ''}
          <h2 id="method">Method</h2>
          <ol class="steps">
{steps}
          </ol>
          {doneness_html}
          <h2>Storage</h2>
          <p>{esc(r.get('storage',''))}</p>
        </div>
      </div>

      {nutrition_html}

      {collection_line}

      <p class="provenance">{T.PROVENANCE}
          <a href="../about.html">More in About</a>.</p>
    </article>
  </div>
</section>

{foot}

<script src="../script.js"></script>
<script src="../assets/js/favourites.js"></script>
</body>
</html>
"""


# Pages here that no recipe owns. A renamed recipe leaves its old URL behind
# in somebody's bookmarks and in a search index, and this host has no working
# redirect rules — _redirects is a Cloudflare file and the site is served by
# GitHub Pages, so the only redirect available is a page that redirects
# itself. Same device as south-indian.html and himachali.html at the root.
# Listed here so the sweep below does not delete them every build.
KEEP = {"mithila-machh-posto.html"}   # -> machhak-jhor.html


def main():
    db = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))
    nav, foot = chrome(None)
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".html") and f not in KEEP:
            os.remove(os.path.join(OUT, f))
    for r in db["recipes"]:
        open(os.path.join(OUT, r["id"] + ".html"), "w", encoding="utf-8").write(render(r, nav, foot))
    total_kb = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1024
    print("wrote %d recipe pages (%.0f KB total, %.1f KB each)"
          % (len(db["recipes"]), total_kb, total_kb / len(db["recipes"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
