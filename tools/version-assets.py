#!/usr/bin/env python3
"""Stamp style.css and the scripts with a content hash in every page.

    python3 tools/version-assets.py

GitHub Pages serves assets with cache-control: max-age=600, so for ten minutes
after a deploy a browser can hold the previous stylesheet while already having
the new HTML. That combination is not a graceful degradation: when the cuisines
menu shipped, old CSS with new markup rendered the 21 cuisines as a plain list
inside the header and pushed it to three times its height.

Appending ?v=<hash of the file> makes the URL change whenever the file changes,
so new markup can only ever be paired with the CSS it was built against. The
hash is of the content, so an unchanged file keeps its URL and stays cached.

Run last, after every other build step, since it must see final file contents.
Idempotent: an existing ?v= is replaced rather than stacked.
"""
import glob, hashlib, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = ["style.css", "script.js", "assets/js/cook.js", "assets/js/site-search.js",
          "assets/js/search-match.js", "assets/js/kitchen-strip.js",
          "assets/js/favourites.js"]


def digest(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return None
    return hashlib.sha1(open(path, "rb").read()).hexdigest()[:8]


def main():
    stamps = {rel: digest(rel) for rel in ASSETS}
    stamps = {k: v for k, v in stamps.items() if v}

    pages = glob.glob(os.path.join(ROOT, "*.html")) + glob.glob(os.path.join(ROOT, "recipes", "*.html"))
    touched = 0
    for path in pages:
        src = open(path, encoding="utf-8").read()
        out = src
        for rel, h in stamps.items():
            base = os.path.basename(rel) if rel.startswith("assets/") else rel
            # match href/src ending in this asset, with or without ../ and ?v=
            pat = re.compile(r'((?:href|src)=")((?:\.\./)?%s)(\?v=[0-9a-f]+)?(")'
                             % re.escape(rel if not rel.startswith("assets/") else rel))
            out = pat.sub(lambda m: m.group(1) + m.group(2) + "?v=" + h + m.group(4), out)
        if out != src:
            open(path, "w", encoding="utf-8").write(out)
            touched += 1

    print("stamped %d assets into %d pages" % (len(stamps), touched))
    for rel, h in sorted(stamps.items()):
        print("   %-30s v=%s" % (rel, h))
    return 0


if __name__ == "__main__":
    sys.exit(main())
