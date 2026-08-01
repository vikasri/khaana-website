#!/usr/bin/env python3
"""Check data/recipes.json for the errors that actually reach the reader.

    python3 tools/validate-recipes.py

Two classes of problem matter here and they fail differently:

  * A bad ingredient id fails loudly — the Cook page can't join it to the
    pantry, so the dish silently never matches anything.
  * A bad diet tag fails quietly and dangerously — someone filtering for vegan
    gets a dish made with ghee. Nothing in the UI catches that, so it is
    checked here against the recipe's own ingredient list.

Exits non-zero if anything is wrong, so it can gate a build.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DIFFICULTY = {"easy", "moderate", "advanced"}
EQUIPMENT = {"stovetop", "kadhai", "tawa", "oven", "steamer", "blender",
             "pressure-cooker"}

# The groups that decide an allergen or a tag live in tools/diet_rules.py, so
# the tool that writes them and this tool that checks them cannot disagree.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diet_rules import (ALLERGEN_GROUPS, ALLERGENS, JUSTIFIES, TAGS,
                        TAG_BLOCKERS, NUT_ADJACENT)


def main():
    pantry = json.load(open(os.path.join(ROOT, "data", "pantry.json"), encoding="utf-8"))
    valid_ing = {i["id"] for c in pantry["categories"] for i in c["items"]}
    valid_ing |= set(pantry["staples"])
    gloss_keys = set(pantry["glossary"])

    db = json.load(open(os.path.join(ROOT, "data", "recipes.json"), encoding="utf-8"))
    recipes = db["recipes"]
    errors, warnings = [], []
    seen_ids = {}

    def err(rid, msg):
        errors.append("%-28s %s" % (rid, msg))

    for r in recipes:
        rid = r.get("id", "<no id>")
        if rid in seen_ids:
            err(rid, "duplicate recipe id")
        seen_ids[rid] = True

        ing_ids = {i["id"] for i in r["ingredients"]}
        for i in sorted(ing_ids - valid_ing):
            err(rid, "unknown ingredient id: %s" % i)

        if r["difficulty"] not in DIFFICULTY:
            err(rid, "bad difficulty: %s" % r["difficulty"])
        for e in set(r["equipment"]) - EQUIPMENT:
            err(rid, "bad equipment: %s" % e)
        for t in set(r["tags"]) - TAGS:
            err(rid, "bad tag: %s" % t)
        for a in set(r["allergens"]) - ALLERGENS:
            err(rid, "bad allergen: %s" % a)
        for g in set(r.get("glossary", [])) - gloss_keys:
            err(rid, "unknown glossary key: %s" % g)
        for s in r["steps"]:
            if s.get("glossary") and s["glossary"] not in gloss_keys:
                err(rid, "unknown glossary key in step: %s" % s["glossary"])

        tags = set(r["tags"])
        allerg = set(r["allergens"])

        # A tag describes the recipe as written, which means its essential
        # ingredients. An optional cashew garnish or a flour seal that gets
        # discarded should not strip the tag off the dish — but the reader
        # still has to be told, so those become warnings, not errors.
        essential = {i["id"] for i in r["ingredients"] if i.get("essential", True)}
        optional = ing_ids - essential
        # An optional ingredient that contradicts a tag is fine only if the
        # recipe tells the reader to leave it out.
        explained = {i["id"] for i in r["ingredients"]
                     if any(w in (i.get("note") or "").lower()
                            for w in ("omit", "leave out", "discard"))}

        def check(group, tag):
            if tag not in tags:
                return
            hard = essential & group
            if hard:
                err(rid, "tagged %s but essential: %s" % (tag, ", ".join(sorted(hard))))
            soft = (optional & group) - explained
            if soft:
                warnings.append("%-28s tagged %s; optional %s has no note saying to omit it"
                                % (rid, tag, ", ".join(sorted(soft))))

        for tag, blockers in TAG_BLOCKERS.items():
            check(blockers, tag)
        if "vegan" in tags and "vegetarian" not in tags:
            err(rid, "tagged vegan but not vegetarian")
        # egg-free is derived for the whole catalogue, so its absence is an
        # error rather than an authoring choice.
        if "egg-free" not in tags and not (ing_ids & TAG_BLOCKERS["egg-free"]):
            err(rid, "has no egg but is not tagged egg-free; run derive-allergens.py")

        # Allergens are declared for every ingredient present, including
        # optional ones a note excuses for tagging. See tools/diet_rules.py.
        for name, group in ALLERGEN_GROUPS:
            if ing_ids & group and name not in allerg:
                err(rid, "contains %s (%s) but does not declare it"
                    % (name, ", ".join(sorted(ing_ids & group))))
            if name in allerg and not ing_ids & JUSTIFIES.get(name, group):
                warnings.append("%-28s declares %s with no matching ingredient"
                                % (rid, name))

        # Editorial floor. Not fatal, but a recipe under it is not usable.
        if len(r["steps"]) < 4:
            warnings.append("%-28s only %d steps" % (rid, len(r["steps"])))
        if len(r["ingredients"]) < 4:
            warnings.append("%-28s only %d ingredients" % (rid, len(r["ingredients"])))
        if not r.get("storage"):
            warnings.append("%-28s no storage line" % rid)
        if r["prepMinutes"] < 0 or r["cookMinutes"] < 0:
            err(rid, "negative time")

    print("checked %d recipes across %d regions"
          % (len(recipes), len({r["region"] for r in recipes})))
    if warnings:
        print("\n%d warning(s):" % len(warnings))
        for w in sorted(warnings):
            print("  ~ " + w)
    if errors:
        print("\n%d ERROR(S):" % len(errors))
        for e in sorted(errors):
            print("  ! " + e)
        return 1
    print("\nno errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
