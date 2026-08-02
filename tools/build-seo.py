#!/usr/bin/env python3
"""Add canonical + Open Graph tags to every page, and write sitemap.xml / robots.txt.

    python3 tools/build-seo.py

Run after tools/sync-chrome.py and tools/build-recipe-pages.py.

Recipe pages get their tags from tools/build-recipe-pages.py, which knows each
dish. This handles the hand-written pages, where the title and description are
already good and just need to be mirrored into og: tags so links preview, plus a
canonical so the query-string and stub URLs do not compete with the real one.
"""
import glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://khaana.com"

# Redirect stubs must stay out of the sitemap and keep pointing at their target.
STUBS = {"south-indian.html": "tamil-nadu.html", "himachali.html": "pahari.html"}
# recipe.html is a forwarder now; the static pages are the real thing.
# feedback.html is a form: nothing on it is worth a search result, and listing
# it in the sitemap while the page says noindex is a contradiction Search
# Console reports as an error. Membership here settles both, since the sitemap
# below skips this set.
NOINDEX = set(STUBS) | {"recipe.html", "feedback.html"}

HERO = {
    "index.html": "assets/images/home-hero.jpg",
    "cook.html": "assets/images/home-hero.jpg",
}


def page_image(path, src):
    if path in HERO:
        return HERO[path]
    m = re.search(r'<div class="hero small">\s*<img src="([^"]+)"', src)
    if m:
        return m.group(1)
    m = re.search(r'<img src="(assets/images/[^"]+)"', src)
    return m.group(1) if m else "assets/images/home-hero.jpg"


def main():
    pages = sorted(glob.glob(os.path.join(ROOT, "*.html")))
    touched = 0
    for full in pages:
        path = os.path.basename(full)
        src = open(full, encoding="utf-8").read()
        if "<head>" not in src:
            continue

        title = re.search(r"<title>(.*?)</title>", src, re.S)
        desc = re.search(r'<meta name="description" content="([^"]*)"', src)
        title = html.unescape(title.group(1).strip()) if title else "Khaana"
        desc = html.unescape(desc.group(1).strip()) if desc else ""
        img = "%s/%s" % (SITE, page_image(path, src))
        canon = "%s/%s" % (SITE, STUBS.get(path, path))
        if path == "index.html":
            canon = SITE + "/"

        block = ['<link rel="canonical" href="%s" />' % canon]
        if path in NOINDEX:
            block.append('<meta name="robots" content="noindex, follow" />')
        block += [
            '<meta property="og:type" content="website" />',
            '<meta property="og:site_name" content="Khaana" />',
            '<meta property="og:title" content="%s" />' % html.escape(title, quote=True),
            '<meta property="og:description" content="%s" />' % html.escape(desc, quote=True),
            '<meta property="og:url" content="%s" />' % canon,
            '<meta property="og:image" content="%s" />' % img,
            '<meta name="twitter:card" content="summary_large_image" />',
            '<meta name="twitter:title" content="%s" />' % html.escape(title, quote=True),
            '<meta name="twitter:description" content="%s" />' % html.escape(desc, quote=True),
            '<meta name="twitter:image" content="%s" />' % img,
        ]
        # replace any previous run's block rather than stacking duplicates
        src = re.sub(r'\n<link rel="canonical".*?(?=\n<link rel="stylesheet")', "", src, flags=re.S)
        src = re.sub(r'\n<meta (?:property="og:|name="twitter:|name="robots")[^>]*/?>', "", src)
        src = src.replace('<link rel="stylesheet"', "\n".join(block) + '\n<link rel="stylesheet"', 1)
        open(full, "w", encoding="utf-8").write(src)
        touched += 1

    # ---- sitemap ----
    db = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))
    urls = [(SITE + "/", "1.0")]
    for full in pages:
        p = os.path.basename(full)
        if p in NOINDEX or p == "index.html":
            continue
        urls.append(("%s/%s" % (SITE, p), "0.8"))
    for r in db["recipes"]:
        urls.append(("%s/recipes/%s.html" % (SITE, r["id"]), "0.6"))

    body = "\n".join(
        '  <url><loc>%s</loc><priority>%s</priority></url>' % (u, pr) for u, pr in urls)
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % body)

    open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)

    print("canonical + og/twitter added to %d pages" % touched)
    print("sitemap.xml: %d urls (%d pages + %d recipes)"
          % (len(urls), len(urls) - len(db["recipes"]), len(db["recipes"])))
    print("robots.txt written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
