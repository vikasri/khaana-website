#!/usr/bin/env python3
"""Tag the dishes that are soups.

    python3 tools/tag-soups.py [--dry-run]

Reviewed by hand rather than derived, because the question is not answerable
from the data. Seventeen recipes describe themselves as a soup or a broth in
their own subtitle, and four of those are not soups: sambar, macher jhol,
tambda rassa and haak are broths you eat with rice, not soups you drink. Two
that say neither word — thukpa and chamthong — plainly are.

So the list is the list. The script's job is to keep it honest: every name
here must still exist in the database, and it says so loudly if one does not,
because a renamed recipe would otherwise drop out of the filter silently.

What the tag buys, and why a tag rather than a rename:

  * the Cook page's search already reads `tags`, so typing "soup" finds rasam
  * so does the site-wide search index
  * the Soups checkbox on the Cook page filters on it like any diet tag

Renaming the dishes to "Rasam (soup)" would have done the same job by writing
a category into sixteen dish names, which are also the pairing game's board,
the recipe pages' headings and the sitemap's titles.
"""
import collections, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "recipes.json")
TAG = "soup"

# Eaten from a bowl or a tumbler, as its own course or drink.
SOUPS = [
    "Mulligatawny Soup",        # Anglo-Indian
    "Pepper Water",             # Anglo-Indian
    "Marag",                    # Hyderabadi
    "Ulavacharu",               # Andhra
    "Rasam",                    # Tamil Nadu
    "Nandu Rasam",              # Tamil Nadu
    "Katachi Amti",             # Maharashtrian
    "Thukpa",                   # Northeast Indian
    "Gundruk ko Jhol",          # Northeast Indian
    "Chamthong",                # Northeast Indian
    "Hot and Sour Soup",        # Indo-Chinese
    "Manchow Soup",             # Indo-Chinese
    "Sweet Corn Soup",          # Indo-Chinese
    "Wonton Soup",              # Indo-Chinese
    "Tomato Dhaniya Shorba",    # Awadhi/Lucknowi
    "Murgh Shorba",             # Awadhi/Lucknowi
]

# Say "broth" or "soup" about themselves and are not soups. Kept here so the
# next person to read the subtitles does not re-open the question.
NOT_SOUPS = {
    "Sambar":       "a tamarind and dal broth, but it goes over rice and idli",
    "Macher Jhol":  "a thin fish curry eaten with rice",
    "Tambda Rassa": "drunk alongside a Kolhapuri thali, but it is the gravy",
    "Haak":         "greens in their own liquor, served with rice",
    "Gujarati Kadhi": "a yoghurt and gram-flour gravy, poured over rice",
}


def main():
    dry = "--dry-run" in sys.argv
    db = json.load(open(SRC, encoding="utf-8"),
                   object_pairs_hook=collections.OrderedDict)
    by_name = {r["name"]: r for r in db["recipes"]}

    missing = [n for n in SOUPS if n not in by_name]
    if missing:
        raise SystemExit("no longer in the database: %s" % ", ".join(missing))

    added, removed = [], []
    for r in db["recipes"]:
        tags = set(r.get("tags", []))
        want = r["name"] in by_name and r["name"] in SOUPS
        if want and TAG not in tags:
            tags.add(TAG)
            added.append(r["name"])
        elif not want and TAG in tags:
            tags.discard(TAG)
            removed.append(r["name"])
        r["tags"] = sorted(tags)

    if not dry:
        json.dump(db, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open(SRC, "a", encoding="utf-8").write("\n")

    print("soup: %d tagged (%d added, %d removed)%s"
          % (len(SOUPS), len(added), len(removed), "  [dry run]" if dry else ""))
    for n in added:
        print("   + %s" % n)
    for n in removed:
        print("   - %s" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
