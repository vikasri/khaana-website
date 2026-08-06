# khaana.com

A static site about India's regional cooking. 652 recipes across 21 regional
cuisines, plus a guide page for each cuisine.

There is no framework and no build step in the usual sense. The pages in this
repository are the pages that get served. Python scripts in `tools/` write
them, and GitHub Pages serves the result.

## I want to change some words

**A sentence that appears on more than one page** — the allergen note, the
liability disclaimer, the footer tagline, the nutrition caveats — lives in
[`tools/site_text.py`](tools/site_text.py). Edit it there and run:

```
python3 tools/rebuild.py
```

That is the whole loop. Nothing else needs touching, and the change reaches
every page that carries the sentence.

**A sentence on one page only** — a recipe's method, a cuisine's history, the
home page hero — lives in that page, or in the recipe's own entry in
`data/recipes.json`. Editing the HTML directly is fine for the hand-written
pages: `index.html`, `about.html`, `cook.html` and the 21 cuisine pages.

**Do not hand-edit anything in `recipes/`.** All 651 of those are generated
and your change will be overwritten on the next rebuild. Edit
`data/recipes.json` instead.

## Layout

```
index.html, about.html, cook.html      hand-written pages
<cuisine>.html  x21                    hand-written, with a generated recipe list
recommendations.html, credits.html     fully generated
feedback.html                          hand-written; posts to a Google Form
recipes/  x651                         fully generated - do not edit

data/recipes.json                      the source of truth for every recipe
data/nutrition.json                    computed from USDA data
data/search-index.json                 generated

assets/js/                             cook page, search, saved recipes, feedback
style.css, script.js                   one stylesheet, one shared script

tools/                                 the scripts that build all of the above
tools/one-off/                         finished import scripts, kept for the record
```

## The build

`tools/rebuild.py` runs everything in the right order and says what each step
did. The order matters more than it looks: the recipe pages copy their nav and
footer out of `cook.html`, so the sync tools have to run both before and after
the generators. Getting it wrong produces a half-correct site and no error.
The reasoning is written out at the top of that file.

Two things `rebuild.py` deliberately does **not** do, because both need either
the network or a multi-gigabyte local archive:

- `tools/fetch-*.py` — pull recipe photographs from Wikimedia Commons
- `tools/build-nutrition.py` — recompute nutrition from USDA FoodData Central

## Derived fields

Four things on a recipe are not authored, they are computed from the rest of
it, because a hand-typed copy of something the recipe already says goes stale
the moment the recipe changes and nothing complains:

```
python3 tools/derive-allergens.py     # allergens, diet tags, tagsConditional
python3 tools/derive-inactive.py      # inactiveMinutes, inactiveLabel
python3 tools/derive-doneness.py      # doneness
python3 tools/build-nutrition.py      # nutrition (from the cached USDA table)
```

Run the relevant one after editing a recipe's ingredients or steps.
`validate-recipes.py` fails if you forget, so nothing ships stale — but it
fails after the fact, not instead of running them.

`inactiveMinutes` is the soak, ferment, marinade, rest or chill the recipe
requires. It is the reason the page says **Active** rather than Total: prep
plus cook on a dish that soaks overnight is the time you spend standing at the
stove, not the time the dish takes. `derive-inactive.py --report` lists every
recipe where the wait is longer than the whole of the active time.

## Checks worth running

```
python3 tools/validate-recipes.py     # ingredients, tags, allergens, derived fields
python3 tools/rebuild.py              # then: git diff, before committing
```

`git diff` after a rebuild should only show what you meant to change. If it
shows more, something upstream moved.

## Deploying

Commit and push. GitHub Pages rebuilds within a minute or two. See
[DEPLOY.md](DEPLOY.md) for how the domain is served, why renaming a page means
adding a redirect stub, and why `tools/version-assets.py` has to run last.
