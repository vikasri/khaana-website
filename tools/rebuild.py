#!/usr/bin/env python3
"""Rebuild the site. Run this after editing site_text.py or any recipe data.

    python3 tools/rebuild.py

The order below is not arbitrary and getting it wrong fails quietly rather
than loudly, which is the reason this file exists instead of a note in a
README that nobody reads twice.

Two orderings matter in particular:

  * The page generators copy the nav and footer out of cook.html. So the two
    sync tools run BEFORE them, or the 651 recipe pages inherit whatever
    cook.html happened to say last time. They also run AFTER, because the
    generators strip the active state out of the nav they copied and write
    pages that still need their own feedback link. Running them only once, at
    either end, leaves half the site wrong and nothing complains.
  * version-assets.py stamps a content hash onto style.css and the scripts in
    every page, so it can only run once every page has reached its final
    state. Run it earlier and half the site points at a stale stylesheet.

This does not fetch images or recompute nutrition from the USDA archive.
Those need network access or a local download, they take minutes rather than
seconds, and neither changes when you edit a sentence.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STEPS = [
    # First, so cook.html is correct before anything copies out of it.
    ("sync-chrome.py",           "nav and footer columns on the root pages"),
    ("sync-shared-text.py",      "shared copy on the root pages"),

    ("build-recipe-pages.py",    "651 recipe pages"),
    ("build-cuisine-recipes.py", "recipe lists on the 21 cuisine pages"),
    ("build-recommendations.py", "the curated seven"),
    ("build-credits.py",         "the image credits page"),

    # Again, because the generators write pages of their own and strip the
    # active state out of the nav they copied.
    ("sync-chrome.py",           "again: active nav on the pages just written"),
    ("sync-shared-text.py",      "again: per-page feedback links, recipes included"),

    ("build-search-index.py",    "the site search index"),
    ("build-seo.py",             "canonical tags, sitemap.xml, robots.txt"),
    ("version-assets.py",        "cache-busting stamps (must be last)"),
]


def main():
    failed = []
    for script, what in STEPS:
        path = os.path.join(ROOT, "tools", script)
        if not os.path.exists(path):
            print("  ! missing: tools/%s" % script)
            failed.append(script)
            continue
        r = subprocess.run([sys.executable, path], cwd=ROOT,
                           capture_output=True, text=True)
        mark = "ok " if r.returncode == 0 else "FAIL"
        print("  %s  %-26s %s" % (mark, script, what))
        if r.returncode != 0:
            failed.append(script)
            for line in (r.stdout + r.stderr).strip().splitlines()[-6:]:
                print("        %s" % line)

    print()
    if failed:
        print("  %d step(s) failed: %s" % (len(failed), ", ".join(failed)))
        print("  The site is now part-built. Fix and re-run before committing.")
        return 1
    print("  Site rebuilt. Check `git diff` before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
