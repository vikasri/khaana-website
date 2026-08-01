#!/usr/bin/env python3
"""Generate CREDITS.md from assets/images/credits.json.

    python3 tools/build-credits.py

CREDITS.md used to be hand-maintained alongside credits.json, and the two
drifted: seventeen images ended up in neither, published under CC BY-SA with no
credit line. credits.json is now the single source of truth and this file is
generated, so an image cannot be added without its attribution coming with it.

Exits non-zero if any image on disk has no entry, which makes it usable as a
check before deploying.
"""
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "assets", "images")
CREDITS_JSON = os.path.join(IMG_DIR, "credits.json")
OUT = os.path.join(ROOT, "CREDITS.md")

HEADER = """# Image Credits

Every photograph on khaana.com comes from Wikimedia Commons under a licence
that permits reuse: CC0, public domain, CC BY, or CC BY-SA. Non-commercial (NC)
and no-derivatives (ND) licences are rejected, because ND would forbid the resizing a
responsive layout does.

CC BY and CC BY-SA require attribution, so this file is part of meeting the
licence terms rather than a courtesy. It is generated from
`assets/images/credits.json` by `tools/build-credits.py`; edit that file, not
this one.

"""


def rows_for(rows, title, keep):
    sel = sorted([r for r in rows if keep(r)], key=lambda r: r["file"])
    if not sel:
        return ""
    out = ["## %s\n" % title,
           "| File | Subject | License | Artist | Source |",
           "|---|---|---|---|---|"]
    for r in sel:
        artist = (r.get("artist") or "Unknown").strip() or "Unknown"
        src = r.get("source_url") or ""
        link = "[link](%s)" % src if src else ", "
        out.append("| `%s` | %s | %s | %s | %s |" % (
            r["file"], (r.get("wiki_title") or "").strip() or ", ",
            r.get("license") or "Unknown", artist[:60], link))
    return "\n".join(out) + "\n\n"


def write_html_page(rows, n_files):
    """credits.html — the reader-facing version.

    CREDITS.md was linked from the footer of every page and served as
    text/markdown, so a browser showed raw pipe tables or offered a download.
    The licences require attribution to be reasonable to find, and a file the
    browser refuses to render is not that. Nav and footer are lifted from
    cook.html so this page cannot drift from the rest of the site.
    """
    src = open(os.path.join(ROOT, "cook.html"), encoding="utf-8").read()
    nav = re.search(r'<header class="site-header">.*?</header>', src, re.S).group(0)
    nav = nav.replace(' class="active"', '')
    foot = re.search(r'<footer class="site-footer">.*?</footer>', src, re.S).group(0)

    def esc(s):
        return html.escape(str(s if s is not None else ""), quote=True)

    def table(title, keep, blurb):
        sel = sorted([r for r in rows if keep(r)], key=lambda r: r["file"])
        if not sel:
            return ""
        out = ['<h2>%s</h2>' % esc(title), '<p class="credits-blurb">%s</p>' % blurb,
               '<div class="credits-scroll"><table class="credits-table">',
               '<thead><tr><th>Image</th><th>Subject</th><th>Licence</th>'
               '<th>Photographer</th><th>Source</th></tr></thead><tbody>']
        for r in sel:
            src_url = r.get("source_url") or ""
            link = ('<a href="%s" rel="noopener nofollow">Commons</a>' % esc(src_url)
                    if src_url else ", ")
            out.append("<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                       % (esc(r["file"]), esc((r.get("wiki_title") or "").strip() or ", "),
                          esc(r.get("license") or "Unknown"),
                          esc((r.get("artist") or "Unknown").strip() or "Unknown"), link))
        out.append("</tbody></table></div>")
        return "\n".join(out)

    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Image Credits | Khaana</title>
<meta name="description" content="Every photograph on Khaana comes from Wikimedia Commons under a licence that permits reuse. This page lists each image, its licence and its photographer." />
<link rel="stylesheet" href="style.css" />
</head>
<body>

%s

<section class="tight">
  <div class="container credits-page">
    <div class="section-head">
      <div class="eyebrow">Credits</div>
      <h1>Image Credits</h1>
    </div>
    <p class="credits-intro">Every photograph on Khaana comes from
      <a href="https://commons.wikimedia.org/" rel="noopener">Wikimedia Commons</a> under a licence
      that permits reuse: CC0, public domain, CC BY or CC BY-SA. Non-commercial (NC) and
      no-derivatives (ND) licences are not used, because ND would forbid the resizing a responsive
      layout does.</p>
    <p class="credits-intro">CC BY and CC BY-SA require attribution, so this page is part of
      meeting the licence terms rather than a courtesy. It lists all %d images on the site.
      If you believe something here is credited wrongly,
      <a href="mailto:strategychoice1@gmail.com">tell us</a> and it will be corrected.</p>

%s

%s
  </div>
</section>

%s

<script src="script.js"></script>
</body>
</html>
""" % (nav, n_files,
       table("Cuisine pages", lambda r: "/" not in r["file"],
             "Hero and gallery photographs on the regional cuisine pages."),
       table("Recipes", lambda r: r["file"].startswith("recipes/"),
             "One photograph per recipe. Where an exact match was unavailable, "
             "the nearest equivalent dish is used and noted as such."),
       foot)
    open(os.path.join(ROOT, "credits.html"), "w", encoding="utf-8").write(page)
    print("credits.html written")


def main():
    rows = json.load(open(CREDITS_JSON, encoding="utf-8"))
    by_file = {r["file"]: r for r in rows}

    on_disk = set()
    for base, _, files in os.walk(IMG_DIR):
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                rel = os.path.relpath(os.path.join(base, f), IMG_DIR)
                on_disk.add(rel.replace(os.sep, "/"))

    missing = sorted(f for f in on_disk if f not in by_file)
    orphan = sorted(f for f in by_file if f not in on_disk)

    body = HEADER
    body += rows_for(rows, "Cuisine pages (hero and gallery)",
                     lambda r: "/" not in r["file"])
    body += rows_for(rows, "Recipe photographs",
                     lambda r: r["file"].startswith("recipes/"))

    unknown = [r for r in rows if (r.get("license") or "Unknown") == "Unknown"]
    if unknown:
        body += ("## Licence not recorded\n\n"
                 "These predate the current pipeline. They came from Commons, but the "
                 "specific licence was not captured at download time, so they are listed "
                 "here rather than claimed to be something they may not be.\n\n")
        body += "\n".join("- `%s`, %s" % (r["file"], r.get("wiki_title") or "")
                          for r in sorted(unknown, key=lambda r: r["file"])) + "\n\n"

    open(OUT, "w", encoding="utf-8").write(body)
    write_html_page(rows, len(on_disk))

    print("CREDITS.md written: %d entries across %d image files"
          % (len(rows), len(on_disk)))
    if unknown:
        print("  licence recorded as Unknown: %d" % len(unknown))
    if orphan:
        print("  entries with no file on disk: %d" % len(orphan))
    if missing:
        print("\n  IMAGES WITH NO ATTRIBUTION: %d" % len(missing))
        for f in missing[:20]:
            print("    %s" % f)
        return 1
    print("  every image on disk is attributed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
