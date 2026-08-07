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
def assets():
    """Every stylesheet and script the site serves.

    This was a hand-written list, and a hand-written list of files is a list
    that goes out of date the first time somebody adds one. assets/js/trivia.js
    shipped unstamped for exactly that reason: returning visitors kept a cached
    copy of the old script against new markup, which is the precise failure the
    stamping exists to prevent.

    Discovering them means a new script is covered the moment it exists.
    """
    found = ["style.css", "script.js"]
    found += sorted(os.path.relpath(p, ROOT).replace(os.sep, "/")
                    for p in glob.glob(os.path.join(ROOT, "assets", "js", "*.js")))
    return found


def digest(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return None
    return hashlib.sha1(open(path, "rb").read()).hexdigest()[:8]


def main():
    stamps = {rel: digest(rel) for rel in assets()}
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

    # The JSON the scripts fetch needs the same treatment, and cannot get it
    # the same way: those URLs live inside the JavaScript, not in an href. So
    # the hash is stamped into the script instead, and because that changes the
    # script's own content the page's ?v= for it moves too — the bust cascades.
    #
    # Without this the Cook page fetched data/recipes-index.json unstamped, so
    # a returning visitor could run today's cook.js against a cached index for
    # as long as the CDN held it. It is the exact failure this tool exists to
    # prevent, on the one file the page is actually about.
    DATA = ["data/recipes-index.json", "data/pantry.json", "data/search-index.json"]
    dstamps = {rel: digest(rel) for rel in DATA}
    dstamps = {k: v for k, v in dstamps.items() if v}
    scripts = [os.path.join(ROOT, p) for p in assets() if p.endswith(".js")]
    stamped_js = 0
    for path in scripts:
        src = open(path, encoding="utf-8").read()
        out = src
        for rel, h in dstamps.items():
            out = re.sub(r"(['\"])" + re.escape(rel) + r"(?:\?v=[0-9a-f]+)?\1",
                         lambda m, h=h, rel=rel: m.group(1) + rel + "?v=" + h + m.group(1),
                         out)
        if out != src:
            open(path, "w", encoding="utf-8").write(out)
            stamped_js += 1
    if stamped_js:
        # The scripts just changed, so their own hashes are stale. Recompute
        # and rewrite the pages a second time.
        stamps = {rel: digest(rel) for rel in assets()}
        stamps = {k: v for k, v in stamps.items() if v}
        for path in pages:
            src = open(path, encoding="utf-8").read()
            out = src
            for rel, h in stamps.items():
                pat = re.compile(r'((?:href|src)=")((?:\.\./)?%s)(\?v=[0-9a-f]+)?(")'
                                 % re.escape(rel))
                out = pat.sub(lambda m, h=h: m.group(1) + m.group(2) + "?v=" + h + m.group(4), out)
            if out != src:
                open(path, "w", encoding="utf-8").write(out)

    print("stamped %d assets into %d pages" % (len(stamps), touched))
    for rel, h in sorted(dstamps.items()):
        print("   %-30s v=%s  (into %d scripts)" % (rel, h, stamped_js))
    for rel, h in sorted(stamps.items()):
        print("   %-30s v=%s" % (rel, h))
    return 0


if __name__ == "__main__":
    sys.exit(main())
