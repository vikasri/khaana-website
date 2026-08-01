#!/usr/bin/env python3
"""Recompute every recipe's allergens and diet tags from its ingredients.

    python3 tools/derive-allergens.py [--dry-run]

Allergens were hand-written per recipe, and hand-written allergens drift. An
audit of the live site found 141 recipes printing "Allergens: none of the
common ones" while containing a regulated one. Egg Curry, eight hard-boiled
eggs, printed it. The vocabulary itself had no egg, sesame or mustard, so no
amount of care while authoring could have caught that.

Allergens are a pure function of the ingredient list, so they are derived here
instead. tools/validate-recipes.py checks the same rules from the same module
and fails the build if this has not been run.

What changes for the reader:

  * egg, sesame, mustard and peanut become declarable, and crustacean splits
    from fish, following FDA and UK categories.
  * `vegetarian` now excludes egg. An egg-essential dish loses the tag.
  * `egg-free` joins the diet filters, so egg can be avoided the same way
    dairy, gluten and nuts already can.

Optional ingredients are treated differently for the two:

  * A diet tag survives an optional ingredient the recipe tells you to omit.
    Leave out the cashew garnish and the dish really is nut-free.
  * An allergen is declared for every ingredient in the list, omit note or
    not. Champaran ahuna mutton seals its pot with a wheat dough lid that is
    discarded, and nobody eats it, but the dough sits against the food for the
    whole cook. The reader deciding whether that is a risk needs to be told it
    is there. Over-declaring costs someone a dish; under-declaring does worse.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diet_rules import ALLERGEN_GROUPS, TAG_BLOCKERS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "recipes.json")
OMIT_WORDS = ("omit", "leave out", "discard")


def parts(r):
    """essential ids, and optional ids the recipe does not tell you to drop."""
    essential, optional = set(), set()
    for i in r["ingredients"]:
        note = (i.get("note") or "").lower()
        if i.get("essential", True):
            essential.add(i["id"])
        elif not any(w in note for w in OMIT_WORDS):
            optional.add(i["id"])
    return essential, optional


def main():
    dry = "--dry-run" in sys.argv
    db = json.load(open(SRC, encoding="utf-8"))
    added_a, removed_a, added_t, removed_t = {}, {}, {}, {}

    for r in db["recipes"]:
        essential, optional = parts(r)
        # Allergens see the whole list, including ingredients an omit note
        # excuses for tagging purposes.
        everything = {i["id"] for i in r["ingredients"]}

        want = [name for name, group in ALLERGEN_GROUPS if everything & group]
        have = list(r.get("allergens") or [])
        for a in set(want) - set(have):
            added_a.setdefault(a, []).append(r["id"])
        for a in set(have) - set(want):
            removed_a.setdefault(a, []).append(r["id"])
        r["allergens"] = want

        tags = set(r.get("tags") or [])
        # A blocked tag comes off. egg-free goes on wherever nothing blocks it,
        # so the new filter covers the whole catalogue rather than only the
        # recipes someone remembered to tag.
        for tag, blockers in TAG_BLOCKERS.items():
            blocked = bool(essential & blockers) or bool(optional & blockers)
            if blocked and tag in tags:
                tags.discard(tag)
                removed_t.setdefault(tag, []).append(r["id"])
            elif tag == "egg-free" and not blocked and tag not in tags:
                tags.add(tag)
                added_t.setdefault(tag, []).append(r["id"])
        # vegan implies vegetarian; never leave one without the other.
        if "vegan" in tags:
            tags.add("vegetarian")
        r["tags"] = sorted(tags)

    def report(title, d):
        if not d:
            return
        print("\n  %s" % title)
        for k in sorted(d):
            ex = ", ".join(d[k][:4]) + (" ..." if len(d[k]) > 4 else "")
            print("    %-12s %3d   %s" % (k, len(d[k]), ex))

    report("allergens added", added_a)
    report("allergens removed", removed_a)
    report("tags removed", removed_t)
    report("tags added", added_t)

    if dry:
        print("\ndry run, nothing written")
        return 0
    json.dump(db, open(SRC, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\nwrote %s" % os.path.relpath(SRC, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
