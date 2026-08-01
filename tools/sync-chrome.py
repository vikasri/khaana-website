#!/usr/bin/env python3
"""Rewrite the shared nav and footer on every page from one definition here.

    python3 tools/sync-chrome.py

The site has no templating, so each page carries its own copy of the header nav
and the footer cuisine columns. Editing one page by hand leaves the rest
inconsistent — which has happened before. This makes the duplication mechanical:
change CUISINES once and every page is rewritten to match, with the current
page's own link marked active.
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ordered roughly north -> west -> south -> east, which is how the nav reads.
CUISINES = [
    ("awadhi-lucknowi.html", "Awadhi/Lucknowi"),
    ("kashmiri.html",        "Kashmiri"),
    ("himachali.html",       "Himachali/Pahari"),
    ("punjabi.html",         "Punjabi"),
    ("rajasthani.html",      "Rajasthani"),
    ("gujarati.html",        "Gujarati"),
    ("sindhi.html",          "Sindhi"),
    ("parsi.html",           "Parsi"),
    ("maharashtrian.html",   "Maharashtrian"),
    ("goan.html",            "Goan"),
    ("karnataka.html",       "Karnataka"),
    ("kerala.html",          "Kerala"),
    ("tamil-nadu.html",      "Tamil Nadu"),
    ("andhra.html",          "Andhra"),
    ("hyderabadi.html",      "Hyderabadi"),
    ("bihari.html",          "Bihari"),
    ("odia.html",            "Odia"),
    ("bengali.html",         "Bengali"),
    ("northeast-indian.html", "Northeast Indian"),
    ("anglo-indian.html",    "Anglo-Indian"),
]
FOOTER_HEADS = ["Cuisines", "More", "Also", "And"]

# Pages that are not part of the site chrome.
SKIP = {"south-indian.html"}   # redirect stub


def nav_html(current):
    rows = ['        <li><a href="index.html"%s>Home</a></li>'
            % (' class="active"' if current == "index.html" else ""),
            '        <li><a href="cook.html"%s>Cook</a></li>'
            % (' class="active"' if current == "cook.html" else "")]
    for href, label in CUISINES:
        cls = ' class="active"' if href == current else ""
        rows.append('        <li><a href="%s"%s>%s</a></li>' % (href, cls, label))
    return '      <ul class="nav-links">\n' + "\n".join(rows) + "\n      </ul>"


def footer_html():
    per = (len(CUISINES) + len(FOOTER_HEADS) - 1) // len(FOOTER_HEADS)
    out = []
    for i, head in enumerate(FOOTER_HEADS):
        chunk = CUISINES[i * per:(i + 1) * per]
        if not chunk:
            continue
        links = "\n".join('        <li><a href="%s">%s</a></li>' % (h, l) for h, l in chunk)
        out.append('    <div>\n      <h4>%s</h4>\n      <ul class="foot-links">\n%s\n'
                   '      </ul>\n    </div>' % (head, links))
    return "\n".join(out) + "\n"


def main():
    nav_re = re.compile(r'      <ul class="nav-links">.*?</ul>', re.S)
    foot_re = re.compile(r'    <div>\s*<h4>Cuisines</h4>.*?(?=    <div class="credit-line">)', re.S)
    changed = []
    for path in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        name = os.path.basename(path)
        if name in SKIP:
            continue
        src = open(path, encoding="utf-8").read()
        new = src
        if nav_re.search(new):
            new = nav_re.sub(lambda m: nav_html(name), new, count=1)
        else:
            print("  ! %-24s no nav block found" % name)
        if foot_re.search(new):
            new = foot_re.sub(lambda m: footer_html(), new, count=1)
        else:
            print("  ! %-24s no footer columns found" % name)
        if new != src:
            open(path, "w", encoding="utf-8").write(new)
            changed.append(name)
    print("rewrote chrome on %d of %d pages" % (len(changed), len(glob.glob(
        os.path.join(ROOT, "*.html"))) - len(SKIP)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
