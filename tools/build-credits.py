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
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "assets", "images")
CREDITS_JSON = os.path.join(IMG_DIR, "credits.json")
OUT = os.path.join(ROOT, "CREDITS.md")

HEADER = """# Image Credits

Every photograph on khaana.com comes from Wikimedia Commons under a licence
that permits reuse: CC0, public domain, CC BY, or CC BY-SA. Non-commercial (NC)
and no-derivatives (ND) licences are rejected — ND would forbid the resizing a
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
        link = "[link](%s)" % src if src else "—"
        out.append("| `%s` | %s | %s | %s | %s |" % (
            r["file"], (r.get("wiki_title") or "").strip() or "—",
            r.get("license") or "Unknown", artist[:60], link))
    return "\n".join(out) + "\n\n"


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
        body += "\n".join("- `%s` — %s" % (r["file"], r.get("wiki_title") or "")
                          for r in sorted(unknown, key=lambda r: r["file"])) + "\n\n"

    open(OUT, "w", encoding="utf-8").write(body)

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
