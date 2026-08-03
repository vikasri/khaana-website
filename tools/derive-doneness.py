#!/usr/bin/env python3
"""Recompute which safe-temperature targets each recipe needs to print.

    python3 tools/derive-doneness.py [--dry-run]

An audit of the live site found 198 recipes with meat, poultry, fish,
crustaceans or eggs and not one internal temperature anywhere in the
collection. Doneness was given as time, tenderness, colour, oil separation or
appearance. Those are good cooking cues and they stay exactly as written, but
none of them is a control: burner power, pan geometry, portion size, starting
temperature and the thickness of a thigh all vary, and a cue that reads right
on one stove reads right on another at a different temperature.

So each recipe carries a `doneness` list of category keys, derived from its
ingredients the way allergens are. The sentences themselves live in
tools/site_text.py, because they appear on two hundred pages and copy that
appears on more than one page belongs in one place or it drifts.

Categories follow FDA and USDA FSIS, which split by animal and by whether the
meat is ground:

    poultry     74C / 165F   chicken and duck, every cut, minced or not
    ground      71C / 160F   minced mutton, beef, pork
    whole-red   63C / 145F   whole cuts of mutton, beef, pork, plus a 3 min rest
    fish        63C / 145F   finfish, or opaque and flaking
    shellfish   --           prawns, crab, squid: opaque and pearly, no target
    egg         71C / 160F   egg dishes; whole eggs by firm yolk and white

Minced meat is a separate category because grinding moves surface bacteria
through the whole mass, so the centre has to reach a temperature a whole cut
never needs to. The recipes say so in their quantity strings ("500g, minced",
"600g boneless leg, minced twice"), which is what MINCED reads.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "recipes.json")

POULTRY = {"chicken", "duck"}
RED = {"mutton", "beef", "pork"}
FISH = {"fish", "dried-fish"}
SHELLFISH = {"prawns", "crab", "squid"}
EGG = {"eggs"}

MINCED = re.compile(r"\bminc\w*|\bkeema\b|\bground\b", re.I)

# Print order, so a mixed dish reads the same way on every page.
ORDER = ["poultry", "ground", "whole-red", "fish", "shellfish", "egg"]


def categories(r):
    out = set()
    for i in r["ingredients"]:
        iid = i["id"]
        text = (i.get("qty") or "") + " " + (i.get("note") or "")
        if iid in POULTRY:
            # Ground poultry has the same target as a whole bird, so it needs
            # no separate line.
            out.add("poultry")
        elif iid in RED:
            out.add("ground" if MINCED.search(text) else "whole-red")
        elif iid in FISH:
            out.add("fish")
        elif iid in SHELLFISH:
            out.add("shellfish")
        elif iid in EGG:
            out.add("egg")
    return [c for c in ORDER if c in out]


def main():
    dry = "--dry-run" in sys.argv
    db = json.load(open(SRC, encoding="utf-8"))
    counts, changed = {}, 0

    for r in db["recipes"]:
        want = categories(r)
        if want != r.get("doneness", []):
            changed += 1
        if want:
            r["doneness"] = want
            for c in want:
                counts[c] = counts.get(c, 0) + 1
        else:
            r.pop("doneness", None)

    have = sum(1 for r in db["recipes"] if r.get("doneness"))
    print("doneness targets on %d of %d recipes (%d changed)"
          % (have, len(db["recipes"]), changed))
    for c in ORDER:
        if counts.get(c):
            print("    %-11s %3d" % (c, counts[c]))
    if dry:
        print("dry run, nothing written")
        return 0
    json.dump(db, open(SRC, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("wrote %s" % os.path.relpath(SRC, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
