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

# What earns the pescatarian tag, as opposed to merely not disqualifying a dish.
SEAFOOD_IDS = {"fish", "dried-fish", "prawns", "crab", "squid"}


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
        # A blocked tag comes off, and an unblocked one goes on. Both
        # directions, because for a while only egg-free went on and the rest
        # were applied by hand: 137 recipes with no onion or garlic anywhere in
        # them were missing the tag, so more than half of what belonged in that
        # filter was invisible to it. A tag that is a pure function of the
        # ingredient list should not depend on anyone remembering.
        #
        # pescatarian is the exception and does not derive from its blocker.
        # That blocker is land meat only, so deriving it would put the tag on
        # every vegetarian dish on the site and the filter would hand back the
        # vegetarian list with fish mixed in. What it marks instead is the part
        # a vegetarian filter cannot already give you: the dish has fish or
        # seafood in it and nothing else off an animal.
        for tag, blockers in TAG_BLOCKERS.items():
            if tag == "pescatarian":
                continue
            blocked = bool(essential & blockers) or bool(optional & blockers)
            if blocked and tag in tags:
                tags.discard(tag)
                removed_t.setdefault(tag, []).append(r["id"])
            elif not blocked and tag not in tags:
                tags.add(tag)
                added_t.setdefault(tag, []).append(r["id"])

        # Fish or seafood, and no land meat.
        seafood = bool(everything & SEAFOOD_IDS)
        land_meat = bool(everything & TAG_BLOCKERS["pescatarian"])
        if seafood and not land_meat and "pescatarian" not in tags:
            tags.add("pescatarian")
            added_t.setdefault("pescatarian", []).append(r["id"])
        elif (not seafood or land_meat) and "pescatarian" in tags:
            tags.discard("pescatarian")
            removed_t.setdefault("pescatarian", []).append(r["id"])

        # vegan implies vegetarian; never leave one without the other.
        if "vegan" in tags:
            tags.add("vegetarian")
        r["tags"] = sorted(tags)

        # Which of those tags are true only of a variation. Khaman Dhokla is
        # tagged vegan and gluten-free while listing optional yogurt and
        # optional rava; the ingredient notes say to omit them, which is why
        # the tag survives the rule above and why the allergen line still
        # declares milk and gluten. Nothing is hidden, but a card that says
        # "vegan" flat is describing the version you get by leaving something
        # out, and it should say so. An audit called this out on Dhokla and
        # Chapati; deriving it finds the other nine as well.
        conditional = set()
        for i in r["ingredients"]:
            if i.get("essential", True):
                continue
            note = (i.get("note") or "").lower()
            if not any(w in note for w in OMIT_WORDS):
                continue
            for tag, blockers in TAG_BLOCKERS.items():
                if i["id"] in blockers and tag in tags:
                    conditional.add(tag)
        # vegan is the stronger claim, so if it is conditional then so is the
        # vegetarian that comes with it — but only when something non-
        # vegetarian is what makes it so.
        if conditional:
            r["tagsConditional"] = sorted(conditional)
        else:
            r.pop("tagsConditional", None)

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
    json.dump(db, open(SRC, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("\nwrote %s" % os.path.relpath(SRC, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
