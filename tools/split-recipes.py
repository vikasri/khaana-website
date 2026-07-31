#!/usr/bin/env python3
"""Split data/recipes.json into a light matching index plus per-recipe detail.

data/recipes.json stays the authoring source of truth. This generates:

    data/recipes-index.json   what the Cook page needs to rank and draw cards
    data/recipes/<id>.json    full detail, fetched only when a recipe is opened

Without this the Cook page downloads every step, prep note and storage line of
every recipe just to sort some cards — about 960KB at 235 recipes. The index
carries roughly a fifth of that.

Run after editing recipes.json:

    python3 tools/split-recipes.py
"""
import json, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "recipes.json")
INDEX = os.path.join(ROOT, "data", "recipes-index.json")
DETAIL_DIR = os.path.join(ROOT, "data", "recipes")

# Fields the Cook page needs to filter, score and render a card.
INDEX_FIELDS = ("id", "name", "subtitle", "region", "regionPage", "servings",
                "prepMinutes", "cookMinutes", "difficulty", "equipment",
                "tags", "allergens", "image")


def main():
    db = json.load(open(SRC, encoding="utf-8"))
    recipes = db["recipes"]

    if os.path.isdir(DETAIL_DIR):
        shutil.rmtree(DETAIL_DIR)
    os.makedirs(DETAIL_DIR)

    index = []
    for r in recipes:
        entry = {k: r[k] for k in INDEX_FIELDS if k in r}
        # Only the join key and weighting matter for scoring — quantities,
        # notes and substitution prose stay in the detail file.
        entry["ingredients"] = [
            {"id": i["id"], "essential": i.get("essential", True)}
            for i in r["ingredients"]
        ]
        index.append(entry)
        json.dump(r, open(os.path.join(DETAIL_DIR, r["id"] + ".json"), "w",
                          encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    json.dump({"version": db.get("version"), "updated": db.get("updated"),
               "recipes": index},
              open(INDEX, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    full = os.path.getsize(SRC) / 1024
    idx = os.path.getsize(INDEX) / 1024
    print("recipes:        %d" % len(recipes))
    print("full database:  %6.0f KB  (authoring source, no longer shipped whole)" % full)
    print("index shipped:  %6.0f KB  (%.0f%% of full)" % (idx, idx / full * 100))
    print("detail files:   %d written to data/recipes/" % len(recipes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
