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
TAGS = {"vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free",
        "no-onion-garlic", "pescatarian",
        # Derived by tools/tag-healthy.py from explicit thresholds, not authored.
        "healthier"}
ALLERGENS = {"dairy", "gluten", "nuts", "fish"}

# Ingredient groups that decide a tag. Kept here rather than in pantry.json
# because they encode dietary rules, not pantry structure.
DAIRY = {"butter", "buttermilk", "condensed-milk", "cream", "ghee", "khoya",
         "milk", "paneer", "yogurt"}
MEAT = {"beef", "chicken", "duck", "mutton", "pork"}
SEAFOOD = {"crab", "dried-fish", "fish", "prawns", "squid"}
# rava (semolina) and dalia (broken wheat) are wheat despite not being called
# flour; leaving them out would let a gluten-free tag through on an upma.
GLUTEN = {"atta", "maida", "bread", "pav", "vermicelli", "dalia", "rava"}
NUTS = {"almonds", "cashew", "peanut", "pistachios", "walnuts", "melon-seeds"}
# US labelling counts coconut as a tree nut; Indian cooking never does, and
# treating it as one would put a nuts warning on most of Kerala and Goa. So
# coconut does not force a declaration or block `nut-free` — but a recipe that
# declares nuts because of it is not flagged as over-declaring.
NUT_ADJACENT = NUTS | {"coconut", "dried-coconut", "coconut-milk"}
ALLIUM = {"onion", "garlic", "shallot", "spring-onion"}
NON_VEGAN = DAIRY | MEAT | SEAFOOD | {"eggs", "honey"}


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

        def check(group, tag, label):
            if tag not in tags:
                return
            hard = essential & group
            if hard:
                err(rid, "tagged %s but essential: %s" % (tag, ", ".join(sorted(hard))))
            soft = (optional & group) - explained
            if soft:
                warnings.append("%-28s tagged %s; optional %s has no note saying to omit it"
                                % (rid, tag, ", ".join(sorted(soft))))

        check(NON_VEGAN, "vegan", "non-vegan")
        check(MEAT | SEAFOOD, "vegetarian", "meat")
        check(DAIRY, "dairy-free", "dairy")
        check(GLUTEN, "gluten-free", "gluten")
        check(NUTS, "nut-free", "nuts")
        check(ALLIUM, "no-onion-garlic", "allium")
        check(MEAT, "pescatarian", "meat")
        if "vegan" in tags and "vegetarian" not in tags:
            err(rid, "tagged vegan but not vegetarian")

        # Allergens follow the same essential/optional split.
        for group, name in ((DAIRY, "dairy"), (GLUTEN, "gluten"),
                            (NUTS, "nuts"), (SEAFOOD, "fish")):
            if essential & group and name not in allerg:
                err(rid, "essential %s (%s) but does not declare the allergen"
                    % (name, ", ".join(sorted(essential & group))))
            soft = (optional & group) - explained
            if soft and name not in allerg:
                warnings.append("%-28s optional %s (%s) not declared and not explained"
                                % (rid, name, ", ".join(sorted(soft))))
            justifies = NUT_ADJACENT if name == "nuts" else group
            if name in allerg and not ing_ids & justifies:
                warnings.append("%-28s declares %s allergen with no matching ingredient"
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
