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
    ("pahari.html",          "Pahari"),
    ("kashmiri.html",        "Kashmiri"),
    ("punjabi.html",         "Punjabi"),
    ("rajasthani.html",      "Rajasthani"),
    ("gujarati.html",        "Gujarati"),
    ("maharashtrian.html",   "Maharashtrian"),
    ("goan.html",            "Goan"),
    ("karnataka.html",       "Karnataka"),
    ("kerala.html",          "Kerala"),
    ("tamil-nadu.html",      "Tamil Nadu"),
    ("andhra.html",          "Andhra"),
    ("hyderabadi.html",      "Hyderabadi"),
    ("odia.html",            "Odia"),
    ("bihari.html",          "Bihari"),
    ("bengali.html",         "Bengali"),
    ("northeast-indian.html", "Northeast Indian"),
    # No map zone: community cuisines without territory, so they come last.
    ("sindhi.html",          "Sindhi"),
    ("parsi.html",           "Parsi"),
    ("anglo-indian.html",    "Anglo-Indian"),
    ("indo-chinese.html",    "Indo-Chinese"),
]
FOOTER_HEADS = ["Cuisines", "More", "Also", "And"]

# Pages that are not part of the site chrome.
SKIP = {"south-indian.html", "himachali.html"}   # redirect stubs


def nav_html(current):
    """Home, Recipes, a Cuisines menu, About.

    The 21 cuisines used to sit in the bar itself, which meant 24 items
    wrapping to three lines on a desktop and colliding with the brand. They are
    still written into the page, inside a menu that is closed by default, so
    every cuisine remains a crawlable link from every page.
    """
    cuisine_hrefs = {h for h, _ in CUISINES}
    on_cuisine = current in cuisine_hrefs

    rows = ['        <li><a href="index.html"%s>Home</a></li>'
            % (' class="active"' if current == "index.html" else ""),
            '        <li><a href="cook.html"%s>Recipes</a></li>'
            % (' class="active"' if current == "cook.html" else "")]

    menu = ['        <li class="nav-cuisines">',
            '          <button type="button" class="nav-cuisines-toggle%s" '
            'aria-expanded="false" aria-controls="nav-cuisine-menu">Cuisines</button>'
            % (" active" if on_cuisine else ""),
            '          <ul class="nav-dropdown" id="nav-cuisine-menu">']
    for href, label in CUISINES:
        cls = ' class="active"' if href == current else ""
        menu.append('            <li><a href="%s"%s>%s</a></li>' % (href, cls, label))
    menu += ['          </ul>', '        </li>']
    rows += menu

    rows.append('        <li><a href="about.html"%s>About</a></li>'
                % (' class="active"' if current == "about.html" else ""))
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
    # Bounded by </nav>, not by the first </ul>. The Cuisines dropdown put a
    # nested <ul> inside this one, so a non-greedy match to "</ul>" stopped at
    # the dropdown's closing tag and left the real tail behind, duplicating the
    # About link on all 25 pages. Matching to </nav> takes the whole list
    # however deeply it nests, and repairs a page that was already doubled.
    nav_re = re.compile(r'      <ul class="nav-links">.*?(?=\n\s*</nav>)', re.S)
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
