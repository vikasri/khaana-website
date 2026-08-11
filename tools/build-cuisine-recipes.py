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
from urllib.parse import quote_plus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEGIN = "<!-- BEGIN generated cuisine recipe list -->"
END = "<!-- END generated cuisine recipe list -->"
ROW_LIMIT = 12

# What to actually ask Maps for.
#
# The first version searched the region name plus "restaurant", which is fine
# for Punjabi or Bengali and useless for the rest. There is no such listing as
# a "Pahari restaurant" or an "Odia restaurant", so Maps found no match and did
# what it does with any unmatched query: returned whatever was nearby. Readers
# got Thai places and pizza.
#
# So each region gets a phrase built out of the words restaurants put on their
# own signage, not the words a food writer would use. Awadhi food is sold as
# Mughlai, Karnataka food as Udupi, Tamil Nadu food as Chettinad or South
# Indian. Every phrase ends in "Indian restaurant" (Indo-Chinese reads "Indian
# Chinese"), which is the part that keeps the results on-cuisine: where the
# specific term matches nothing, Maps still has a real category to fall back
# to, so the worst case is a nearby Indian restaurant rather than a taqueria.
SEARCH = {
    "Andhra":           "Andhra Indian restaurant",
    "Anglo-Indian":     "Anglo Indian restaurant",
    "Awadhi/Lucknowi":  "Awadhi Mughlai Indian restaurant",
    "Bengali":          "Bengali Indian restaurant",
    "Bihari":           "Bihari North Indian restaurant",
    "Goan":             "Goan Indian restaurant",
    "Gujarati":         "Gujarati Indian restaurant",
    "Hyderabadi":       "Hyderabadi biryani Indian restaurant",
    "Indo-Chinese":     "Indian Chinese Hakka restaurant",
    "Karnataka":        "Udupi Mangalorean Indian restaurant",
    "Kashmiri":         "Kashmiri Indian restaurant",
    "Kerala":           "Kerala South Indian restaurant",
    "Maharashtrian":    "Maharashtrian Indian restaurant",
    "Northeast Indian": "Northeast Indian Naga restaurant",
    "Odia":             "Odia Indian restaurant",
    "Pahari":           "Pahari North Indian restaurant",
    "Parsi":            "Parsi Irani Indian restaurant",
    "Punjabi":          "Punjabi North Indian restaurant",
    "Rajasthani":       "Rajasthani Marwari Indian restaurant",
    "Sindhi":           "Sindhi Indian restaurant",
    "Tamil Nadu":       "Chettinad South Indian restaurant",
}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def thumb_src(r):
    """The 148px square cut by tools/build-tile-thumbs.py, or the photograph.

    A tile shows the picture 74 pixels wide. The full-size file is made for a
    recipe page and averages 150 KB, which is about twenty-five times what a
    square this size can show. Falls back to the original where no thumbnail
    has been cut yet, so a photograph added between builds still appears.
    """
    src = r["image"]["src"]
    cut = os.path.join("assets", "images", "tiles", r["id"] + ".jpg")
    return cut.replace(os.sep, "/") if os.path.exists(os.path.join(ROOT, cut)) else src


def tile(r, hidden):
    thumb = ('<img src="%s" alt="%s" loading="lazy" />' % (esc(thumb_src(r)), esc(r["image"]["alt"]))
             if r.get("image") else
             '<span class="tile-noimg" aria-hidden="true">%s</span>' % esc(r["name"][:1]))
    mins = (r.get("prepMinutes") or 0) + (r.get("cookMinutes") or 0)
    # Active minutes, and a word for the wait where there is one. A tile is too
    # small for the figure, and "+ soaking" is the part that changes whether
    # you can cook this tonight.
    wait = (" + %s" % esc(r["inactiveLabel"]) if r.get("inactiveMinutes") else "")
    return ('<a class="recipe-tile%s" href="recipes/%s.html"%s>'
            '<span class="tile-thumb">%s</span>'
            '<span class="tile-body"><span class="tile-name">%s</span>'
            '<span class="tile-meta">%d min%s &middot; %s</span></span></a>'
            % (" is-extra" if hidden else "", esc(r["id"]), " hidden" if hidden else "",
               thumb, esc(r["name"]), mins, wait, esc(r.get("difficulty", ""))))


def block(region, query, recipes):
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
      <h2>More %s recipes</h2>
    </div>
    <div class="recipe-tiles">
      %s
    </div>%s

    <!-- Eating out instead. A plain link to Google Maps: no API key, no
         backend, and nothing leaves the page until the reader clicks. The
         postcode box is optional because Maps already uses the device
         location without it; it exists for people who will not grant
         location permission, or who are looking somewhere other than where
         they are standing.

         Google only. An Apple Maps link sat beside this and has been
         removed: maps.google.com opens in Safari on an iPhone with no app
         installed, so the second link bought nothing and asked every reader
         to make a choice on behalf of their phone. -->
    <div class="eat-out">
      <p class="eat-out-lead">Not cooking tonight?</p>
      <div class="eat-out-row">
        <label class="sr-only" for="eat-out-where">Postcode or town, optional</label>
        <input type="text" id="eat-out-where" class="eat-out-where"
               placeholder="Postcode or town (optional)" autocomplete="postal-code" />
        <a class="eat-out-btn" data-query="%s"
           href="https://www.google.com/maps/search/?api=1&amp;query=%s"
           target="_blank" rel="noopener noreferrer">Find %s restaurants</a>
      </div>
    </div>
  </div>
</section>
%s""" % (BEGIN, esc(region), tiles, more,
         esc(query), quote_plus(query), esc(region), END)


def main():
    db = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))["recipes"]
    by_page = {}
    for r in db:
        page = r.get("regionPage")
        if page:
            by_page.setdefault(page, []).append(r)

    # A region with no phrase, or one that forgot the Indian anchor, would ship
    # the bug this table exists to fix. Refuse to write anything rather than
    # let one page quietly send readers to the nearest sandwich shop.
    regions = sorted({r["region"] for r in db if r.get("regionPage")})
    bad = [x for x in regions if "indian" not in SEARCH.get(x, "").lower()]
    if bad:
        print("  ! no anchored Maps query for: %s" % ", ".join(bad))
        print("    add one to SEARCH in this file")
        return 1

    written = 0
    for page, recipes in sorted(by_page.items()):
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            print("  ! %s not found" % page)
            continue
        recipes.sort(key=lambda r: r["name"])
        src = open(path, encoding="utf-8").read()
        region = recipes[0]["region"]
        new_block = block(region, SEARCH[region], recipes)

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
