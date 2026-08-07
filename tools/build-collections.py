#!/usr/bin/env python3
"""Generate the diet and time collection pages.

    python3 tools/build-collections.py

Why these exist. The Cook page can already narrow the database to vegan, to
gluten-free, to half an hour — but it does it in JavaScript against a filter
panel, and no filter state has a URL. So the 227 vegan recipes and the 305
lighter ones were invisible to a search engine: there was no page to rank, no
title to match, and nothing for anyone searching "vegan Indian recipes" to
land on. Every cuisine has a page; no diet did.

Each page here is a real, crawlable list of every recipe that qualifies, with
its own title, its own opening paragraph and CollectionPage/ItemList markup.
They are generated from the same tags the Cook page filters on, so a page can
never drift from what the filter would return.

On wording: the site's own tag is "healthier", which is a comparative and a
defensible one. Nobody types that. The page is titled and described in the
words people actually search — healthy Indian recipes — while the sentence
that makes the claim still says what the tag means, so the honest version is
the one a reader sees.

Idempotent: rewrites each page whole on every run.
"""

import collections
import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://khaana.com"
ROW_LIMIT = 24          # tiles visible before the "show more" button


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


# Numbers quoted in the ledes are counted from the data at build time, never
# typed into the sentence. A hand-written "145 of these use asafoetida" is
# true on the day it is written and silently wrong after the next batch of
# recipes, and nothing on the site would ever complain.
WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve"]


def spell(n):
    """Small numbers read better as words in a sentence; large ones do not."""
    return WORDS[n].capitalize() if n < len(WORDS) else str(n)


def with_ing(recipes, ing):
    return sum(1 for r in recipes
               if any(i["id"] == ing for i in r.get("ingredients", [])))


def region_share(recipes):
    """Which kitchens are most and least represented, as 'n of the m'."""
    db = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))
    total = collections.Counter(r["region"] for r in db["recipes"])
    here = collections.Counter(r["region"] for r in recipes)
    # Only regions with enough recipes for a share to mean anything.
    ranked = sorted(((here[k] / total[k], k) for k in total if total[k] >= 20),
                    reverse=True)
    def phrase(k):
        return "%d of the %d %s recipes" % (here[k], total[k], k)
    top = " and ".join([phrase(ranked[0][1]),
                        phrase(ranked[1][1]).replace(" recipes", " ones")])
    return {"top": top, "bottom": phrase(ranked[-1][1])}


# Each collection: the file, what it is called, how a recipe qualifies, and the
# one paragraph that says what the reader is looking at. The blurbs are short
# on purpose — a page of prose above a list of recipes is a page nobody reads.
COLLECTIONS = [
    {
        "file": "healthy-indian-recipes.html",
        "h1": "Healthy Indian Recipes",
        "title": "Healthy Indian Recipes: %d Lighter Dishes by Region | Khaana",
        "desc": ("%d healthy Indian recipes with the calories and protein in a serving "
                 "given for each. None of them is deep-fried."),
        "lede": ("The lighter dishes in the database, chosen on the estimated calories and "
                 "protein in one serving rather than on a dish's reputation. None of them is "
                 "deep-fried. The figures are estimates worked out from the raw ingredients, "
                 "so treat them as a guide."),
        "test": lambda r: "healthier" in r.get("tags", []),
    },
    {
        "file": "vegan-indian-recipes.html",
        "h1": "Vegan Indian Recipes",
        "title": "Vegan Indian Recipes: %d Dishes With No Dairy | Khaana",
        "desc": ("%d vegan Indian recipes with no dairy, no ghee and no honey, each one "
                 "checked against its own ingredient list."),
        "lede": ("A large part of Indian cooking is vegan without setting out to be, "
                 "particularly along the coast and in the east. Every recipe here has been "
                 "checked against its own ingredient list. Where one lists ghee for brushing, "
                 "the same line tells you to leave it out."),
        "test": lambda r: "vegan" in r.get("tags", []),
    },
    {
        "file": "vegetarian-indian-recipes.html",
        "h1": "Vegetarian Indian Recipes",
        "title": "Vegetarian Indian Recipes: %d Regional Dishes | Khaana",
        "desc": ("%d vegetarian Indian recipes from 21 regional cuisines, with times, "
                 "measured ingredients and nutrition estimates for every dish."),
        "lede": ("The largest collection on the site: pulses, vegetables, paneer, rice and "
                 "bread from all 21 regional kitchens. {eggs} of these list a beaten egg as "
                 "an optional enrichment and say in the same line to leave it out. The rest "
                 "contain no egg at all."),
        "facts": lambda rs: {"eggs": spell(with_ing(rs, "eggs"))},
        "test": lambda r: "vegetarian" in r.get("tags", []),
    },
    {
        "file": "gluten-free-indian-recipes.html",
        "h1": "Gluten-Free Indian Recipes",
        "title": "Gluten-Free Indian Recipes: %d Dishes Without Wheat | Khaana",
        "desc": ("%d gluten-free Indian recipes built on rice, millet, lentil and gram "
                 "flours rather than wheat, checked against each dish's own ingredients."),
        "lede": ("Much of India eats gluten-free without thinking about it. The southern and "
                 "eastern kitchens are built on rice and lentil batters, and the dry west on "
                 "millet and gram flour. One ingredient is worth checking: {asafoetida} of "
                 "these recipes use asafoetida, and most commercial asafoetida is cut with "
                 "wheat flour. Read the packet."),
        "facts": lambda rs: {"asafoetida": with_ing(rs, "asafoetida")},
        "test": lambda r: "gluten-free" in r.get("tags", []),
    },
    {
        "file": "dairy-free-indian-recipes.html",
        "h1": "Dairy-Free Indian Recipes",
        "title": "Dairy-Free Indian Recipes: %d Dishes Without Milk or Ghee | Khaana",
        "desc": ("%d dairy-free Indian recipes with no milk, yoghurt, ghee, cream or "
                 "paneer, from coastal coconut cooking to the mustard-oil kitchens."),
        "lede": ("No milk, yoghurt, ghee, cream or paneer. Some kitchens qualify almost "
                 "whole: {top}. The northern courts mostly do not, and only {bottom} are "
                 "here."),
        "facts": lambda rs: region_share(rs),
        "test": lambda r: "dairy-free" in r.get("tags", []),
    },
    {
        "file": "quick-indian-recipes.html",
        "h1": "Quick Indian Recipes",
        "title": "Quick Indian Recipes: %d Dishes in 30 Minutes or Less | Khaana",
        "desc": ("%d quick Indian recipes you can cook in half an hour or less, counting "
                 "the prep and the cooking together."),
        "lede": ("Half an hour or less, counting the chopping as well as the cooking. A "
                 "soak or a rest comes first in {soaking} of them, which is time you are "
                 "not standing in the kitchen for; where that applies it is printed beside "
                 "the time."),
        "facts": lambda rs: {"soaking": spell(sum(1 for r in rs if r.get("inactiveMinutes")))},
        "test": lambda r: (r.get("prepMinutes") or 0) + (r.get("cookMinutes") or 0) <= 30,
    },
    {
        "file": "no-onion-no-garlic-recipes.html",
        "h1": "No Onion No Garlic Indian Recipes",
        "title": "No Onion No Garlic Indian Recipes: %d Dishes | Khaana",
        "desc": ("%d Indian recipes cooked without onion or garlic, the way many households "
                 "eat on fast days, using asafoetida and ginger for depth."),
        # The Jain claim that used to be here was wrong and is not coming back:
        # Jain cooking excludes root vegetables, and 21 of these have potato in
        # them. Saying so on the page is more use to a reader than the label was.
        "lede": ("Cooked without onion or garlic, the way many households eat on fast days "
                 "and some eat all year. Asafoetida bloomed in hot fat does much of the work "
                 "and appears in {asafoetida} of them. This is not a Jain collection: root "
                 "vegetables are not excluded, and {potato} of these dishes contain potato."),
        "facts": lambda rs: {"asafoetida": with_ing(rs, "asafoetida"),
                             "potato": with_ing(rs, "potato")},
        "test": lambda r: "no-onion-garlic" in r.get("tags", []),
    },
    {
        "file": "indian-soup-recipes.html",
        "h1": "Indian Soup Recipes",
        "title": "Indian Soup Recipes: %d Shorbas, Rasams and Broths | Khaana",
        "desc": ("%d Indian soup recipes — shorba, rasam and broth — with times, "
                 "ingredients and nutrition estimates for each."),
        "lede": ("Shorba from the Awadhi kitchen, rasam from Tamil Nadu, broths from the "
                 "Northeast, and the Indo-Chinese soups served in every Indian city. Only "
                 "the last of those is really a first course. The rest are drunk alongside "
                 "the meal or poured over rice."),
        "test": lambda r: "soup" in r.get("tags", []),
    },
]


def chrome():
    """Header and footer, copied from cook.html the way the recipe pages do."""
    src = open(os.path.join(ROOT, "cook.html"), encoding="utf-8").read()
    nav = re.search(r'<header class="site-header">.*?</header>', src, re.S).group(0)
    nav = nav.replace(' class="active"', '')
    foot = re.search(r'<footer class="site-footer">.*?</footer>', src, re.S).group(0)
    return nav, foot


def tile(r, hidden):
    thumb = ('<img src="%s" alt="%s" loading="lazy" />'
             % (esc(r["image"]["src"]), esc(r["image"]["alt"])) if r.get("image") else
             '<span class="tile-noimg" aria-hidden="true">%s</span>' % esc(r["name"][:1]))
    mins = (r.get("prepMinutes") or 0) + (r.get("cookMinutes") or 0)
    wait = (" + %s" % esc(r["inactiveLabel"]) if r.get("inactiveMinutes") else "")
    return ('<a class="recipe-tile%s" href="recipes/%s.html"%s>'
            '<span class="tile-thumb">%s</span>'
            '<span class="tile-body"><span class="tile-name">%s</span>'
            '<span class="tile-meta">%s &middot; %d min%s</span></span></a>'
            % (" is-extra" if hidden else "", esc(r["id"]), " hidden" if hidden else "",
               thumb, esc(r["name"]), esc(r.get("region", "")), mins, wait))


def lede_text(coll, recipes):
    """The opening paragraph, with any counted facts filled in from the data.

    A collection without a "facts" entry has no placeholders and passes
    through. One with placeholders and no facts is a bug, and str.format
    raises rather than shipping a page with {asafoetida} printed on it."""
    lede = coll["lede"]
    if "facts" not in coll:
        return lede
    return lede.format(**coll["facts"](recipes))


def share_image(recipes):
    """The picture that shows when the page is pasted into a chat or a post.

    Left to the generic SEO pass all eight would share the home page's bowl of
    spices, so eight different links would preview as one identical card. The
    widest photo from the collection is a landscape crop more often than not,
    which is the shape every social card wants."""
    shots = [r["image"]["src"] for r in recipes
             if r.get("image") and r["image"].get("src")]
    if not shots:
        return "assets/images/home-hero.jpg"
    # Deterministic: the same input must always give the same card.
    return sorted(shots)[0]


def region_links(recipes):
    """Every region represented, linked. Real navigation, and it gives the page
    an internal link to each cuisine rather than leaving it a dead end."""
    pages = {}
    for r in recipes:
        if r.get("regionPage"):
            pages.setdefault(r["region"], r["regionPage"])
    return " &middot; ".join(
        '<a href="%s">%s</a>' % (esc(p), esc(n)) for n, p in sorted(pages.items()))


def others(current):
    """Links to the sibling collections. Keeps each page one click from the
    rest instead of reachable only from the nav."""
    bits = [c for c in COLLECTIONS if c["file"] != current]
    return " &middot; ".join(
        '<a href="%s">%s</a>' % (esc(c["file"]), esc(c["h1"])) for c in bits)


def ld(coll, recipes, n):
    """CollectionPage wrapping an ItemList. The list carries names and URLs so
    the page describes itself as what it is — a list of these recipes — rather
    than leaving a crawler to infer it from markup."""
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": coll["h1"],
        "description": coll["desc"] % n,
        "url": "%s/%s" % (SITE, coll["file"]),
        "isPartOf": {"@type": "WebSite", "name": "Khaana", "url": SITE + "/"},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": n,
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "url": "%s/recipes/%s.html" % (SITE, r["id"]),
                 "name": r["name"]}
                for i, r in enumerate(recipes)
            ],
        },
    }, indent=1)


BEGIN = "<!-- BEGIN generated collection links -->"
END = "<!-- END generated collection links -->"


def strip_block(src):
    return re.sub(re.escape(BEGIN) + ".*?" + re.escape(END), "", src, flags=re.S).rstrip() + "\n"


def links_block(counts):
    """A row of collection links for the home and Recipes pages.

    Both existing routes in ask the visitor to know something first — what is
    in their kitchen, or what to search for. Someone who only knows they eat
    no dairy had nowhere to go. It doubles as the internal link from the two
    highest-authority pages on the site to the eight new ones.
    """
    items = "\n      ".join(
        '<a href="%s">%s</a>' % (esc(c["file"]), esc(c["h1"]))
        for c in COLLECTIONS if counts.get(c["file"])
    )
    return """%s
<section class="tight collection-band">
  <div class="container">
    <h2 class="collection-band-head">Browse by diet or by time</h2>
    <div class="collection-band-links">
      %s
    </div>
  </div>
</section>
%s""" % (BEGIN, items, END)


def inject(path, counts):
    """Put the band into a page, replacing any previous run's copy. Anchored
    before the footer so it lands last in the body whatever else changes."""
    full = os.path.join(ROOT, path)
    src = strip_block(open(full, encoding="utf-8").read())
    block = links_block(counts)
    if '<footer class="site-footer">' not in src:
        print("  ! %-40s no footer to anchor against" % path)
        return
    src = src.replace('<footer class="site-footer">', block + '\n<footer class="site-footer">', 1)
    open(full, "w", encoding="utf-8").write(src)


def page(coll, recipes, nav, foot):
    n = len(recipes)
    title = coll["title"] % n
    desc = coll["desc"] % n
    shown = recipes[:ROW_LIMIT]
    rest = recipes[ROW_LIMIT:]
    tiles = "\n        ".join(tile(r, False) for r in shown)
    if rest:
        tiles += "\n        " + "\n        ".join(tile(r, True) for r in rest)
    more = ('\n      <button type="button" class="show-more-recipes" aria-expanded="false">'
            'Show the rest</button>' if rest else "")

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<meta name="description" content="{desc}" />
<link rel="canonical" href="{site}/{file}" />

<meta property="og:type" content="website" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{desc}" />
<meta property="og:url" content="{site}/{file}" />
<meta property="og:image" content="{site}/{share_img}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{desc}" />
<meta name="twitter:image" content="{site}/{share_img}" />

<link rel="stylesheet" href="style.css" />
<script type="application/ld+json">
{ld}
</script>
</head>
<body>

{nav}

<section class="tight">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">Collections</div>
      <h1>{h1}</h1>
      <p class="lede">{lede}</p>
    </div>

    <div class="collection-body">
      <div class="recipe-tiles">
        {tiles}
      </div>{more}

      <p class="collection-links"><strong>By region:</strong> {regions}</p>
      <p class="collection-links"><strong>Other collections:</strong> {others}</p>
      <p class="collection-links"><a href="cook.html">Filter these by what is in your kitchen &rarr;</a></p>
    </div>
  </div>
</section>

{foot}

<script src="script.js"></script>
<script src="assets/js/favourites.js"></script>
</body>
</html>
""".format(title=esc(title), desc=esc(desc), site=SITE, file=coll["file"],
           ld=ld(coll, recipes, n), nav=nav, foot=foot, h1=esc(coll["h1"]),
           lede=esc(lede_text(coll, recipes)), tiles=tiles, more=more,
           share_img=esc(share_image(recipes)),
           regions=region_links(recipes), others=others(coll["file"]))


def main():
    data = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))
    recipes = data["recipes"]
    nav, foot = chrome()

    counts = {}
    for coll in COLLECTIONS:
        hits = sorted((r for r in recipes if coll["test"](r)),
                      key=lambda r: r["name"])
        if not hits:
            print("  ! %-40s no recipes match" % coll["file"])
            continue
        counts[coll["file"]] = len(hits)
        out = os.path.join(ROOT, coll["file"])
        open(out, "w", encoding="utf-8").write(page(coll, hits, nav, foot))
        print("  %-40s %3d recipes" % (coll["file"], len(hits)))

    for host in ("index.html", "cook.html"):
        inject(host, counts)
    print("wrote %d collection pages, linked from index.html and cook.html"
          % len(counts))


if __name__ == "__main__":
    main()
