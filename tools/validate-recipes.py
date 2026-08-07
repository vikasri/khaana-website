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
import importlib.util, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DIFFICULTY = {"easy", "moderate", "advanced"}
EQUIPMENT = {"stovetop", "kadhai", "tawa", "oven", "steamer", "blender",
             "pressure-cooker"}
# The groups that decide an allergen or a tag live in tools/diet_rules.py, so
# the tool that writes them and this tool that checks them cannot disagree.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diet_rules import (ALLERGEN_GROUPS, ALLERGENS, JUSTIFIES, TAGS,
                        TAG_BLOCKERS, NUT_ADJACENT)

# ---------------------------------------------------------------------------
# Perishables left standing
#
# The August 2026 audit found four recipes telling a reader to hold dairy, a
# batter of eggs and milk, or cooked rice at room temperature for hours. Each
# read as tradition rather than as a hazard, which is exactly why none of them
# looked wrong to anybody writing the next one. This is that finding turned
# into a check, so the fifth gets caught before it ships.
#
# Precision is the whole job here. A rule that fires on every soak, ferment and
# marinade is a rule nobody reads: about a hundred recipes in this collection
# legitimately rest something for hours, and they are not the same case.
#
#   * A dosa, idli, jalebi or handvo batter souring in a warm place is
#     acidifying on purpose and is self-preserving. Grain and pulse, no animal
#     protein, so PERISHABLE never matches it.
#   * A marinade or a hung yogurt that says "refrigerated" is already correct,
#     so SAFE_NEARBY clears it.
#   * "Bring the mutton to room temperature for 30 minutes" is tempering,
#     which is inside the two-hour rule. BOUNDED clears anything an hour or
#     under.
#
# What is left is a perishable held warm for an unstated or long time, which is
# a warning rather than an error: a real one wants judgement, not a build
# failure, and the fix is usually to name a fridge rather than to cut a line.
# ---------------------------------------------------------------------------
# What makes a rest a hazard is in the ingredient list, not in the sentence:
# the baath cake's six-hour rest never mentions the eggs and milk that make it
# one. So the perishable is looked up by id, and the sentence only has to say
# how long and how warm.
#
# Rice earns its place because cooked rice is the Bacillus cereus vehicle, and
# a poita bhat or a pakhala is exactly a pot of it standing overnight.
PERISHABLE_IDS = {
    "eggs", "milk", "yogurt", "buttermilk", "cream", "paneer", "khoya",
    "condensed-milk", "coconut-milk", "rice", "basmati-rice",
    "chicken", "duck", "mutton", "beef", "pork", "fish", "dried-fish",
    "prawns", "crab", "squid",
}
# Long enough to matter. Two hours is the published limit for a perishable out
# of the fridge, so the check starts at three: tempering is minutes, and a
# dough resting the two hours a dough rests is not the thing being looked for.
LONG = re.compile(r"\b(overnight|all day|few hours|"
                  r"([3-9]|\d{2,})\s*(to\s*\d+\s*)?hours?|"
                  r"\d+\s*-\s*\d+\s*hours?)\b", re.I)
# Warm enough to matter. "Refrigerate 4 hours" is long but cold, and cold is
# the whole answer, so a marinade never reaches the check.
WARM = re.compile(r"\b(room temperature|warm place|warm kitchen|warm spot|"
                  r"on the counter|out of the fridge)\b", re.I)
# Named as a deliberate ferment, which is a different mechanism: the batter
# acidifies and preserves itself. Not "sour", which is what the kadhi and the
# pithla both said while doing nothing of the kind.
# A dough left to rise is being leavened, which is the same argument: the yeast
# or the yogurt takes the dough somewhere a bowl of yogurt does not go. Kept to
# the words that mean it deliberately — none of the five this rule was written
# for claims to be rising.
FERMENT = re.compile(r"\b(ferment\w*|leaven\w*|rise|risen|rises|proving|"
                     r"starter|setting time)\b", re.I)
# Cooking something and letting it come down to room temperature is not holding
# it there: the two-hour clock starts at the bottom of that curve, and every
# recipe here that says it goes on to chill. None of the five this rule was
# written for is cooling anything.
COOLING = re.compile(r"\bcool\w*\b", re.I)


def perishable_held(text, ing_ids=(), recipe_blob=""):
    """True when a recipe holds a perishable warm past the two-hour rule.

    A dish that names a ferment anywhere is doing this on purpose and its warm
    rests are cleared wholesale, because the sentence that says "ferment" is
    rarely the sentence that says how long.
    """
    if FERMENT.search(recipe_blob):
        return False
    if not (set(ing_ids) & PERISHABLE_IDS):
        return False
    if COOLING.search(text):
        return False
    return bool(LONG.search(text) and WARM.search(text))
def load(script):
    """Import a tools/ script whose filename has a hyphen in it."""
    path = os.path.join(ROOT, "tools", script)
    spec = importlib.util.spec_from_file_location(script[:-3].replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Both of these are pure functions of the recipe, so the check is simply to run
# the deriver and compare. They matter because both go on the page as promises
# and both go stale silently: edit the step that says how long a batter
# ferments, or swap chicken for paneer, and the old figure sits there looking
# authoritative until someone cooks from it.
INACTIVE = load("derive-inactive.py")
DONENESS = load("derive-doneness.py")


# The judgement in the rule above is invisible once it stops firing, and a
# silent check is indistinguishable from a broken one. These are the five
# recipes it was written for, as they read before they were fixed, and the
# seven long warm rests in the collection that are not the same case.
#
#     python3 tools/validate-recipes.py --selftest
SELFTEST = [
    (True,  "pithla",            "Leave fresh buttermilk on the counter overnight, or stir a squeeze of lemon into it.",
     {"buttermilk"}, ""),
    (True,  "rajasthani kadhi",  "Leave the buttermilk out for a few hours, or overnight in a warm kitchen, to sour it properly.",
     {"buttermilk"}, ""),
    (True,  "kadhi-pakora",      "Leave the yogurt out of the fridge overnight so it sours properly.",
     {"yogurt"}, ""),
    (True,  "goan baath cake",   "Cover and rest at room temperature 6 hours or overnight in the refrigerator.",
     {"eggs", "milk", "coconut-milk"}, ""),
    (True,  "poita bhat",        "The rice has to sit under water overnight, 8 to 12 hours at room temperature.",
     {"rice"}, ""),
    (False, "cold marinade",     "Marinate at least 6 hours, ideally overnight. Refrigerate 6 hours or overnight.",
     {"mutton", "yogurt"}, ""),
    (False, "tempering",         "Bring the mutton to room temperature for 30 minutes before cooking.",
     {"mutton"}, ""),
    (False, "yogurt hung cold",  "Hang the yogurt in muslin overnight in the fridge with a weight on top.",
     {"yogurt"}, ""),
    (False, "jaggery dough",     "The dough must rest overnight at room temperature, covered.",
     {"rice-flour", "jaggery"}, ""),
    (False, "bhatura dough",     "Knead 10 minutes, cover, rest 2 hours in a warm place.",
     {"yogurt", "maida"}, ""),
    (False, "dosa batter",       "Cover and leave to ferment 8 to 12 hours in a warm place.",
     {"rice", "urad-dal"}, "The batter ferments 8 to 12 hours in a warm place."),
    (False, "jalebi",            "cover, and leave 12 hours in a warm place.",
     {"yogurt", "maida"}, "The batter must ferment. Twelve hours in a warm place."),
]


def selftest():
    bad = 0
    for want, name, text, ids, blob in SELFTEST:
        got = perishable_held(text, ids, blob)
        if got != want:
            bad += 1
            print("  FAIL %-18s expected %s" % (name, "a warning" if want else "silence"))
    print("perishable check: %d of %d cases as expected"
          % (len(SELFTEST) - bad, len(SELFTEST)))
    return 1 if bad else 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
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

        blob = " ".join(r.get("prepNotes", [])
                        + [st["text"] + " " + (st.get("tip") or "") for st in r["steps"]]
                        + [(i.get("note") or "") for i in r["ingredients"]])
        for where, text in ([("note", n) for n in r.get("prepNotes", [])]
                            + [("step", st["text"]) for st in r["steps"]]
                            + [("ing", (i.get("note") or "")) for i in r["ingredients"]]):
            if perishable_held(text, ing_ids, blob):
                warnings.append("%-28s %s holds a perishable at room temperature: %s"
                                % (rid, where, " ".join(text.split())[:70]))
        if r["prepMinutes"] < 0 or r["cookMinutes"] < 0:
            err(rid, "negative time")

        mins, label = INACTIVE.derive(r)
        if (r.get("inactiveMinutes", 0), r.get("inactiveLabel")) != (mins, label or None):
            err(rid, "inactive time is %s but the steps say %s; run derive-inactive.py"
                % (r.get("inactiveMinutes", 0), mins))

        want_done = DONENESS.categories(r)
        if r.get("doneness", []) != want_done:
            err(rid, "doneness is %s but the ingredients say %s; run derive-doneness.py"
                % (r.get("doneness", []), want_done))

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
