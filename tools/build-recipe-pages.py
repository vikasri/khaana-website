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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "recipes")
SITE = "https://khaana.com"
FALLBACK_IMG = "assets/images/home-hero.jpg"


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


def schema(r, url, img):
    """schema.org/Recipe. Only fields we can fill honestly."""
    d = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": r["name"],
        "description": r.get("subtitle", ""),
        "url": url,
        "recipeCuisine": r["region"],
        "recipeCategory": "Main" if "dessert" not in (r.get("subtitle") or "").lower() else "Dessert",
        "prepTime": iso_duration(r.get("prepMinutes")),
        "cookTime": iso_duration(r.get("cookMinutes")),
        "totalTime": iso_duration((r.get("prepMinutes") or 0) + (r.get("cookMinutes") or 0)),
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
    return json.dumps(d, ensure_ascii=False, indent=2)


CONFIDENCE_NOTE = {
    "good": "Worked out from the listed quantities; most of the ingredient list could be weighed.",
    "medium": "Worked out from the listed quantities. Some of the ingredient list is given "
              "to taste rather than by weight, so treat these as a guide.",
    "low": "A rough guide only. A large part of this ingredient list is given to taste rather "
           "than by weight, or much of what is weighed is not eaten.",
}


def nutrition_panel(r):
    """Calories and macros, most important first, per serving and per 100 g."""
    n = r.get("nutrition")
    if not n:
        return ""
    ps, pc = n["perServing"], n["per100g"]
    # A floor, not an estimate: unweighable ingredients count as zero.
    plus = "+" if n.get("direction") == "understated" else ""

    def row(label, key, unit="g", cls=""):
        return ('<tr class="%s"><th>%s</th><td>%s</td><td>%s</td></tr>'
                % (cls,
                   esc(label),
                   ("%d%s kcal" % (ps[key], plus)) if key == "kcal"
                   else ("%.1f%s %s" % (ps[key], plus, unit)),
                   ("%d%s kcal" % (pc[key], plus)) if key == "kcal"
                   else ("%.1f%s %s" % (pc[key], plus, unit))))

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
                '<td>%.1f%s g</td></tr>' % (unsat_s, plus, unsat_c, plus))

    notes = []
    if plus:
        notes.append("The <strong>+</strong> means ingredients given to taste rather than by "
                     "weight are counted as zero, so the true figure is a little higher than "
                     "shown.")
    notes.append(CONFIDENCE_NOTE.get(n.get("confidence", "medium")))
    if n.get("caveat"):
        notes.append(n["caveat"])
    if n.get("approximated"):
        notes.append("Some ingredients have no exact match in the nutrient database and use "
                     "the nearest equivalent: " +
                     ", ".join(a.replace("-", " ") for a in n["approximated"][:6]) +
                     ("." if len(n["approximated"]) <= 6 else ", and others."))
    notes.append("Estimated from raw ingredients using "
                 "<a href=\"https://fdc.nal.usda.gov/\" rel=\"noopener\">USDA FoodData "
                 "Central</a>. Cooking changes are not modelled, and added salt is excluded, "
                 "so sodium is not given.")

    return ("""<section class="nutrition" aria-labelledby="nutrition-h">
        <h2 id="nutrition-h">Nutrition <span class="nut-conf" data-c="%s">%s estimate</span></h2>
        <table class="nut-table">
          <thead><tr><th></th><th>Per serving<span>%d g</span></th><th>Per 100 g</th></tr></thead>
          <tbody>%s</tbody>
        </table>
        <p class="nut-note">%s</p>
      </section>""" % (n.get("confidence", "medium"), n.get("confidence", "medium").title(),
                       n["servingGrams"], "".join(rows), " ".join(notes)))


def render(r, nav, foot):
    rid = r["id"]
    url = "%s/recipes/%s.html" % (SITE, rid)
    img_rel = r["image"]["src"] if r.get("image") else FALLBACK_IMG
    img_abs = "%s/%s" % (SITE, img_rel)
    total = (r.get("prepMinutes") or 0) + (r.get("cookMinutes") or 0)

    desc = "%s. %s A %s recipe: %d minutes, serves %s, with measured ingredients, " \
           "substitutions and storage notes." % (
               r["name"], (r.get("subtitle") or "").capitalize().rstrip(".") + ".",
               r["region"], total, r.get("servings", 4))
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
    tags = "".join('<span class="diet-tag">%s</span>' % esc(t.replace("-", " ")) for t in r.get("tags", []))
    allerg = (", ".join(r["allergens"]) if r.get("allergens") else None)

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
<meta property="og:title" content="{esc(r['name'])} — {esc(r['region'])} recipe" />
<meta property="og:description" content="{esc(desc)}" />
<meta property="og:url" content="{url}" />
<meta property="og:image" content="{img_abs}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{esc(r['name'])} — {esc(r['region'])} recipe" />
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
          <h1>{esc(r['name'])}</h1>
          <p class="lede">{esc(r.get('subtitle',''))}</p>
          <div class="diet-tags">{tags}</div>
        </div>
        {photo}
      </div>

      <div class="recipe-stats">
        <div class="stat"><span class="stat-label">Prep</span><span class="stat-value">{r.get('prepMinutes',0)} min</span></div>
        <div class="stat"><span class="stat-label">Cook</span><span class="stat-value">{r.get('cookMinutes',0)} min</span></div>
        <div class="stat"><span class="stat-label">Total</span><span class="stat-value">{total} min</span></div>
        <div class="stat"><span class="stat-label">Serves</span><span class="stat-value">{esc(r.get('servings',4))}</span></div>
        <div class="stat"><span class="stat-label">Difficulty</span><span class="stat-value">{esc(r.get('difficulty',''))}</span></div>
      </div>

      {'<p class="allergen"><strong>Contains:</strong> %s</p>' % esc(allerg) if allerg
       else '<p class="allergen none"><strong>Allergens:</strong> none of the common ones</p>'}

      <div class="recipe-cols">
        <div class="recipe-ing">
          <h2>Ingredients</h2>
          <p class="serves-note">Quantities for {esc(r.get('servings',4))}.</p>
          <ul class="ing-list">
{ing}
          </ul>
          <h3>Equipment</h3>
          <p class="equip-line">{esc(', '.join(e.replace('-', ' ') for e in r.get('equipment', [])))}</p>
        </div>
        <div class="recipe-method">
          {'<h2>Before you start</h2><ul class="prep-notes">%s</ul>' % notes if notes else ''}
          <h2>Method</h2>
          <ol class="steps">
{steps}
          </ol>
          <h2>Storage</h2>
          <p>{esc(r.get('storage',''))}</p>
        </div>
      </div>

      {nutrition_html}

      <p class="provenance">Recipe v{esc(r.get('provenance',{}).get('recipeVersion','1.0.0'))},
        last updated {esc(r.get('provenance',{}).get('updated',''))}.
        Curated for Khaana and kept under version control.</p>
    </article>
  </div>
</section>

{foot}

<script src="../script.js"></script>
</body>
</html>
"""


def main():
    db = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))
    nav, foot = chrome(None)
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".html"):
            os.remove(os.path.join(OUT, f))
    for r in db["recipes"]:
        open(os.path.join(OUT, r["id"] + ".html"), "w", encoding="utf-8").write(render(r, nav, foot))
    total_kb = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1024
    print("wrote %d recipe pages (%.0f KB total, %.1f KB each)"
          % (len(db["recipes"]), total_kb, total_kb / len(db["recipes"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
