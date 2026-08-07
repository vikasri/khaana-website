#!/usr/bin/env python3
"""Put the Cloudflare Web Analytics beacon on every page, once.

    python3 tools/sync-analytics.py

The site has no shared template — 682 pages each carry their own HTML — so
"add it to the footer once" is not available here. This walks every page
instead and keeps the snippet in one delimited block, replaced whole on each
run. Adding a page, regenerating the recipes, or rotating the token means
running this again, which tools/rebuild.py does.

To remove the beacon entirely: set TOKEN to "" and run. The block comes out of
every page and nothing is left behind.

Why it does not slow anything down: the tag is type="module", which browsers
defer by default, so it is fetched after the document is parsed and cannot
block rendering. If Cloudflare is unreachable the request fails and the page
carries on — nothing on any page depends on it.

Placed immediately before </body>, after the site's own scripts, so a beacon
that misbehaves cannot come between the reader and a page that works.
"""

import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BEGIN = "<!-- Cloudflare Web Analytics -->"
END = "<!-- End Cloudflare Web Analytics -->"

# Public by design: it identifies the site to Cloudflare and ships in the HTML
# of every page. It is not a secret and does not need hiding.
TOKEN = "62f25201991348cab07ffeb4eb59dd99"

SNIPPET = (
    '%s<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" '
    'data-cf-beacon=\'{"token": "%s"}\'></script>%s' % (BEGIN, TOKEN, END)
)


def strip(src):
    """Remove a previous run's block, however it was formatted."""
    while BEGIN in src and END in src:
        a = src.index(BEGIN)
        b = src.index(END, a) + len(END)
        # Take the newline the block sits on with it, so repeated runs do not
        # accumulate blank lines above </body>.
        while a > 0 and src[a - 1] in " \t":
            a -= 1
        if a > 0 and src[a - 1] == "\n":
            a -= 1
        src = src[:a] + src[b:]
    return src


def main():
    pages = sorted(glob.glob(os.path.join(ROOT, "*.html")))
    pages += sorted(glob.glob(os.path.join(ROOT, "recipes", "*.html")))

    changed = skipped = 0
    for path in pages:
        src = open(path, encoding="utf-8").read()
        out = strip(src)

        if TOKEN:
            if "</body>" not in out:
                # Redirect stubs are a head and one line; there is nothing to
                # measure and nowhere to put it.
                skipped += 1
                if out != src:
                    open(path, "w", encoding="utf-8").write(out)
                    changed += 1
                continue
            out = out.replace("</body>", SNIPPET + "\n</body>", 1)

        if out != src:
            open(path, "w", encoding="utf-8").write(out)
            changed += 1

    where = "on" if TOKEN else "removed from"
    print("analytics beacon %s %d of %d pages" % (where, changed, len(pages)))
    if skipped:
        print("   %d page(s) have no </body> and were left alone" % skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
