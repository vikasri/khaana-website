#!/usr/bin/env python3
"""Second pass for recipes the first fetch could not match.

    python3 tools/fetch-images-secondpass.py

The first pass searches Commons for the dish by name. That works for dishes
Commons has heard of and fails for the rest — Ulavacharu, Kumror Chorchori,
Warqi Paratha and 200 others returned nothing.

This pass gives up on finding the exact dish and looks for the right kind of
food instead, using the subtitle the recipe already carries. "fish simmered in
a dark tamarind gravy" becomes a search for a fish curry; "wafer-thin layered
paratha" becomes a search for paratha. The result is a photograph of the right
sort of thing rather than of that exact dish, which is the trade this pass
exists to make: a plausible plate of the right food beats a lettered tile.

Everything else is inherited from tools/fetch-recipe-images.py, including the
licence filter and the food-category gate that keeps basketball photographs out
of the recipe database.
"""
import importlib.util, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "fetcher", os.path.join(ROOT, "tools", "fetch-recipe-images.py"))
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

# What kind of thing is it? Ordered, because a subtitle often names several and
# the first match is the most specific.
DISH_TYPE = [
    ("biryani", "biryani"), ("pulao", "pulao rice"), ("pilaf", "pulao rice"),
    ("khichdi", "khichdi"), ("paratha", "paratha"), ("roti", "roti flatbread"),
    ("naan", "naan"), ("puri", "puri bread"), ("dosa", "dosa"), ("idli", "idli"),
    ("uttapam", "uttapam"), ("vada", "vada"), ("pitha", "rice cake"),
    ("kebab", "kebab"), ("tikka", "tikka"), ("chutney", "chutney"),
    ("pickle", "indian pickle"), ("raita", "raita"), ("halwa", "halwa"),
    ("kheer", "kheer pudding"), ("payasam", "payasam"), ("laddu", "laddu"),
    ("barfi", "barfi"), ("jalebi", "jalebi"), ("pudding", "indian pudding"),
    ("soup", "indian soup"), ("broth", "indian soup"), ("rasam", "rasam"),
    ("sambar", "sambar"), ("dal", "dal"), ("lentil", "dal"), ("curry", "curry"),
    ("gravy", "curry"), ("sabzi", "sabzi"), ("stir-fry", "indian stir fry"),
    ("fritter", "pakora"), ("pakora", "pakora"), ("samosa", "samosa"),
    ("rice", "indian rice dish"), ("salad", "indian salad"),
    ("relish", "chutney"), ("stew", "indian stew"),
]

# The protein or vegetable at the centre of it.
CORE = [
    ("prawn", "prawn"), ("shrimp", "prawn"), ("fish", "fish"), ("hilsa", "fish"),
    ("crab", "crab"), ("chicken", "chicken"), ("mutton", "mutton"),
    ("lamb", "mutton"), ("goat", "mutton"), ("pork", "pork"), ("beef", "beef"),
    ("duck", "duck"), ("egg", "egg"), ("paneer", "paneer"), ("cheese", "paneer"),
    ("jackfruit", "jackfruit"), ("pumpkin", "pumpkin"), ("gourd", "gourd"),
    ("aubergine", "aubergine"), ("brinjal", "aubergine"), ("potato", "potato"),
    ("cauliflower", "cauliflower"), ("spinach", "spinach"), ("okra", "okra"),
    ("mushroom", "mushroom"), ("chickpea", "chickpea"), ("bean", "beans"),
    ("mango", "mango"), ("coconut", "coconut"), ("millet", "millet"),
    ("vermicelli", "vermicelli"), ("yogurt", "yogurt"), ("tomato", "tomato"),
]


def pick(text, table):
    """Whole-word match only.

    Substring matching read "Dosakaya Pappu" as a dosa and "Papdi" as a
    pappadum. The dish type has to be its own word to count."""
    low = text.lower()
    for needle, term in table:
        if re.search(r"\b%s(?:s|es)?\b" % re.escape(needle), low):
            return term
    return None


def second_pass_terms(r):
    blob = "%s %s" % (r.get("subtitle", ""), r["name"])
    kind = pick(blob, DISH_TYPE)
    core = pick(blob, CORE)
    region = (r.get("region") or "").split("/")[0]
    out = []
    if core and kind:
        out.append("%s %s" % (core, kind))
        out.append("%s %s indian" % (core, kind))
    if kind:
        out.append("%s %s" % (region, kind))
        if not kind.startswith("indian"):
            out.append("indian %s" % kind)
    if core:
        out.append("indian %s dish" % core)
    # last resort: the distinctive first word of the dish name
    first = re.split(r"[^A-Za-z]+", r["name"])[0]
    if len(first) > 3:
        out.append("%s indian food" % first)
    seen, uniq = set(), []
    for t in out:
        if t not in seen:
            seen.add(t); uniq.append(t)
    return uniq


def main():
    failures = json.load(open(F.FAILED, encoding="utf-8"))
    doc = json.load(open(F.RECIPES, encoding="utf-8"))
    todo = [r for r in doc["recipes"] if r["id"] in failures and not r.get("image")]
    print("second pass over %d recipes\n" % len(todo))

    # The subtitle-derived term names a food category rather than this dish, so
    # the first-pass filename guard would reject every hit. It used to be
    # switched off entirely here, and that is how a recipe for devilled kidneys
    # was given a colonial photograph captioned "Enslaved natives with a load of
    # rubber weighing 75 kilos". Loose about which dish, never loose about
    # whether the subject is food at all.
    NOT_FOOD = (
        "enslaved", "slave", "native", "portrait", "war", "colonial", "monument",
        "temple", "church", "mosque", "map", "coin", "stamp", "painting", "print",
        "engraving", "museum", "statue", "soldier", "battle", "funeral", "grave",
        "protest", "poster", "logo", "flag", "building", "railway", "bridge",
        "cemetery", "memorial", "manuscript", "coat of arms", "bm ",
    )

    def food_guard(term, title):
        low = title.lower()
        if any(w in low for w in NOT_FOOD):
            return False
        return True

    F.name_ok = food_guard
    F.terms_for = second_pass_terms

    # Generic terms mean many recipes chase the same few photographs — every
    # mutton curry would end up with one identical picture. Refuse a Commons
    # file already used anywhere on the site, so each recipe gets its own.
    creds = json.load(open(F.CREDITS, encoding="utf-8"))
    taken = {c.get("source_url") for c in creds if c.get("source_url")}
    inner = F.candidate

    def unique_candidate(page, term):
        c = inner(page, term)
        if not c or c["source_url"] in taken:
            return None
        taken.add(c["source_url"])
        return c

    F.candidate = unique_candidate

    # F.main() re-reads the database itself and takes every recipe without an
    # image, which is exactly this set — no subsetting needed here.
    sys.argv = ["fetch-recipe-images.py"]
    return F.main()


if __name__ == "__main__":
    sys.exit(main())
