#!/usr/bin/env python3
"""Dry-run every tools/_batch_*.py without touching data/recipes.json.

    python3 tools/check-batches.py

Batches are authored separately and installed all at once, so a single bad
ingredient id would otherwise surface only after the database had already been
rewritten. This expands each batch through R() and checks it in place, which
makes a failure cheap to fix — nothing has been written yet.

Passing here is not the whole story: run tools/validate-recipes.py after
installing, which additionally checks diet tags against ingredients.
"""
import glob, importlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from diet_rules import ALLERGEN_GROUPS, TAG_BLOCKERS

DIFFICULTY = {"easy", "moderate", "advanced"}
EQUIPMENT = {"stovetop", "kadhai", "tawa", "oven", "steamer", "blender",
             "pressure-cooker"}
# Taken from diet_rules.py rather than written out again here. Both lists were
# copies once, and they drifted: derive-allergens.py added egg, sesame, mustard,
# peanut and crustacean to the vocabulary and this gate never heard about it, so
# it rejected a new recipe for declaring an allergen that 222 live recipes
# already declare. A gate that is wrong about the rules is worse than no gate.
TAGS = set(TAG_BLOCKERS) | {"healthier"}
ALLERGENS = {name for name, _ingredients in ALLERGEN_GROUPS}


def main():
    pantry = json.load(open(os.path.join(ROOT, "data", "pantry.json"), encoding="utf-8"))
    valid = {i["id"] for c in pantry["categories"] for i in c["items"]}
    valid |= set(pantry["staples"])
    gloss = set(pantry["glossary"])

    existing = {r["id"] for r in json.load(
        open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))["recipes"]}

    total, failed, seen = 0, 0, {}
    for path in sorted(glob.glob(os.path.join(HERE, "_batch*.py"))):
        mod = os.path.basename(path)[:-3]
        try:
            batch = importlib.import_module(mod).BATCH
        except Exception as e:
            print("  ! %-24s import failed: %s: %s" % (mod, type(e).__name__, e))
            failed += 1
            continue

        problems = []
        for r in batch:
            rid = r["id"]
            if rid in existing:
                problems.append("%s: id already in the database" % rid)
            if rid in seen:
                problems.append("%s: duplicate id, also in %s" % (rid, seen[rid]))
            seen[rid] = mod
            for i in r["ingredients"]:
                if i["id"] not in valid:
                    problems.append("%s: unknown ingredient %s" % (rid, i["id"]))
            for g in r.get("glossary", []):
                if g not in gloss:
                    problems.append("%s: unknown glossary key %s" % (rid, g))
            for s in r["steps"]:
                if s.get("glossary") and s["glossary"] not in gloss:
                    problems.append("%s: unknown glossary key in step %s" % (rid, s["glossary"]))
            if r["difficulty"] not in DIFFICULTY:
                problems.append("%s: bad difficulty %s" % (rid, r["difficulty"]))
            for e in set(r["equipment"]) - EQUIPMENT:
                problems.append("%s: bad equipment %s" % (rid, e))
            for t in set(r["tags"]) - TAGS:
                problems.append("%s: bad tag %s" % (rid, t))
            for a in set(r["allergens"]) - ALLERGENS:
                problems.append("%s: bad allergen %s" % (rid, a))

        total += len(batch)
        mark = "ok " if not problems else "FAIL"
        print("  %s %-24s %2d recipes" % (mark, mod, len(batch)))
        for p in problems:
            print("       ! " + p)
        failed += bool(problems)

    print("\n%d recipes across %d batches" % (total, len(glob.glob(
        os.path.join(HERE, "_batch_*.py")))))
    if failed:
        print("%d batch(es) need fixing — nothing was installed" % failed)
        return 1
    print("all batches clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
