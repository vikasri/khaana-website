#!/usr/bin/env python3
"""Add a full recipe list to the bottom of every cuisine page.

    python3 tools/build-cuisine-recipes.py

Each cuisine page listed three or four signature dishes while the database held
dozens for that region: 65 Punjabi recipes, 48 Tamil Nadu, 35 Bengali. Those
pages are the main way in from search, and they were dead ends.

The tiles are written into the HTML rather than fetched by script, so every
recipe is a real crawlable link from its region page. Only the first ROW_LIMIT
are visible; the rest carry the hidden attribute and a button reveals them, so
the page does not open with sixty-five thumbnails.

No counts are shown. The site deliberately does not advertise how many recipes
it has, and a per-region count adds up to the same thing.

Idempotent: the block is delimited by markers and replaced whole on each run.
"""
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEGIN = "<!-- BEGIN generated cuisine recipe list -->"
END = "<!-- END generated cuisine recipe list -->"
ROW_LIMIT = 12


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def tile(r, hidden):
    thumb = ('<img src="%s" alt="%s" loading="lazy" />' % (esc(r["image"]["src"]), esc(r["image"]["alt"]))
             if r.get("image") else
             '<span class="tile-noimg" aria-hidden="true">%s</span>' % esc(r["name"][:1]))
    mins = (r.get("prepMinutes") or 0) + (r.get("cookMinutes") or 0)
    return ('<a class="recipe-tile%s" href="recipes/%s.html"%s>'
            '<span class="tile-thumb">%s</span>'
            '<span class="tile-body"><span class="tile-name">%s</span>'
            '<span class="tile-meta">%d min &middot; %s</span></span></a>'
            % (" is-extra" if hidden else "", esc(r["id"]), " hidden" if hidden else "",
               thumb, esc(r["name"]), mins, esc(r.get("difficulty", ""))))


def block(region, recipes):
    shown = recipes[:ROW_LIMIT]
    rest = recipes[ROW_LIMIT:]
    tiles = "\n      ".join(tile(r, False) for r in shown)
    if rest:
        tiles += "\n      " + "\n      ".join(tile(r, True) for r in rest)
    more = ('\n    <button type="button" class="show-more-recipes" aria-expanded="false">'
            'Show more %s recipes</button>' % esc(region)) if rest else ""
    return """%s
<section class="tight cuisine-recipes">
  <div class="container">
    <div class="section-head">
      <div class="eyebrow">Every recipe</div>
      <h2>More %s recipes</h2>
    </div>
    <div class="recipe-tiles">
      %s
    </div>%s
  </div>
</section>
%s""" % (BEGIN, esc(region), tiles, more, END)


def main():
    db = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))["recipes"]
    by_page = {}
    for r in db:
        page = r.get("regionPage")
        if page:
            by_page.setdefault(page, []).append(r)

    written = 0
    for page, recipes in sorted(by_page.items()):
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            print("  ! %s not found" % page)
            continue
        recipes.sort(key=lambda r: r["name"])
        src = open(path, encoding="utf-8").read()
        new_block = block(recipes[0]["region"], recipes)

        if BEGIN in src:
            src = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), new_block, src, flags=re.S)
        else:
            # Before the closing call to action, which should stay last.
            anchor = '<section class="tight cook-cta-band">'
            if anchor not in src:
                print("  ! %s has no cook-cta-band to anchor to" % page)
                continue
            src = src.replace(anchor, new_block + "\n\n" + anchor, 1)

        open(path, "w", encoding="utf-8").write(src)
        written += 1
        print("  %-24s %3d recipes (%d visible)" % (page, len(recipes), min(ROW_LIMIT, len(recipes))))

    print("\nrecipe lists written to %d cuisine pages" % written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
