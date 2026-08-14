#!/usr/bin/env python3
"""Generate indian-food-names-in-english.html from data/glossary.json.

    python3 tools/build-glossary.py

Why this page exists. Search Console shows the same query shape over and over
-- "mash dal in english", "gahat dal in english", "cholar dal in english",
"tilkut in english", "puran poli in english" -- and the site had nothing to
answer it with. A recipe page names its ingredients in the words the recipe
uses, which is the right call for a cook and no help at all to someone holding
a packet they cannot read.

One table per group, three columns, no prose. The third column is the point:
the same lentil is maash in a Lahore kitchen, mashkalai in a Kolkata one and
black gram on the packet, and only one of those three is what the reader typed.

Idempotent: rewrites the page whole on every run.
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://khaana.com"
FILE = "indian-food-names-in-english.html"

TITLE = "Indian Food Names in English: Dals, Spices, Vegetables"
DESC = ("What Indian ingredient and cooking names mean in English: urad dal, "
        "besan, bhindi, hing, tadka and a hundred more, with the other names "
        "each one goes by.")
LEDE = ("The same ingredient carries a different name in every kitchen it is "
        "cooked in. Here is what the Hindi, Urdu and regional names on a "
        "recipe mean in English, and what else each one is called.")


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def chrome():
    """Header and footer, copied from cook.html the way the other pages do."""
    src = open(os.path.join(ROOT, "cook.html"), encoding="utf-8").read()
    nav = re.search(r'<header class="site-header">.*?</header>', src, re.S).group(0)
    nav = nav.replace(' class="active"', '')
    foot = re.search(r'<footer class="site-footer">.*?</footer>', src, re.S).group(0)
    return nav, foot


def table(group):
    rows = []
    for e in group["entries"]:
        also = ", ".join(e.get("also") or []) or "&mdash;"
        rows.append('<tr><th scope="row">%s</th><td>%s</td><td class="muted">%s</td></tr>'
                    % (esc(e["term"]), esc(e["english"]),
                       also if also == "&mdash;" else esc(also)))
    return """    <h2 id="%s">%s</h2>
    <div class="table-wrap">
      <table class="gloss-table">
        <thead><tr><th>Name</th><th>In English</th><th>Also called</th></tr></thead>
        <tbody>%s</tbody>
      </table>
    </div>""" % (esc(group["id"]), esc(group["label"]), "".join(rows))


def ld(groups):
    terms = []
    for g in groups:
        for e in g["entries"]:
            t = {"@type": "DefinedTerm", "name": e["term"], "description": e["english"]}
            if e.get("also"):
                t["alternateName"] = e["also"]
            terms.append(t)
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "DefinedTermSet",
        "name": "Indian food names in English",
        "url": "%s/%s" % (SITE, FILE),
        "hasDefinedTerm": terms,
    }, ensure_ascii=False, indent=1)


def page(groups, nav, foot):
    jump = " &middot; ".join('<a href="#%s">%s</a>' % (esc(g["id"]), esc(g["label"]))
                             for g in groups)
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
<meta name="twitter:card" content="summary" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{desc}" />

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
      <div class="eyebrow">Glossary</div>
      <h1>Indian food names in English</h1>
      <p class="lede">{lede}</p>
    </div>

    <p class="gloss-jump">{jump}</p>

{tables}

    <p class="collection-links"><a href="cook.html">Find recipes by what is in your kitchen &rarr;</a></p>
  </div>
</section>

{foot}

<script src="script.js"></script>
</body>
</html>
""".format(title=esc(TITLE), desc=esc(DESC), site=SITE, file=FILE,
           ld=ld(groups), nav=nav, foot=foot, lede=esc(LEDE), jump=jump,
           tables="\n\n".join(table(g) for g in groups))


def main():
    data = json.load(open(os.path.join(ROOT, "data", "glossary.json"), encoding="utf-8"))
    groups = data["groups"]
    nav, foot = chrome()
    open(os.path.join(ROOT, FILE), "w", encoding="utf-8").write(page(groups, nav, foot))
    n = sum(len(g["entries"]) for g in groups)
    print("wrote %s: %d terms in %d groups" % (FILE, n, len(groups)))


if __name__ == "__main__":
    main()
