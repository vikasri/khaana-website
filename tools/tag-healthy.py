#!/usr/bin/env python3
"""Tag recipes that meet an explicit "healthier" definition.

    python3 tools/tag-healthy.py          # report only
    python3 tools/tag-healthy.py --write  # apply the tag

"Healthier" is not a fact about a dish the way "vegan" is, so it is defined here
by rules that can be checked against the recipe data rather than by judgement.
A dish earns the tag only if ALL of these hold:

  * it is not deep-fried
  * no refined flour (maida) as an essential ingredient
  * added fat, counting only essential ghee/butter/cream/oils, is at most
    1.5 tbsp per serving
  * added sugar, jaggery, honey or condensed milk is at most 1 tsp per serving
  * it is not a dessert
  * it has a real vegetable, pulse or protein backbone — at least two
    vegetables, or a pulse, or any meat, fish or egg
  * the meat portion is at most 250g raw bone-in per serving

Red meat is not excluded. What decides a meat dish is the portion and how it is
cooked — the frying, added-fat and portion rules above — not the animal.

These thresholds are deliberately conservative. The label is comparative on purpose: it means "lighter than the rest of
this database", not a nutritional or medical claim, and the
Cook page says so next to the filter.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FATS = {"ghee", "butter", "cream", "coconut-oil", "groundnut-oil", "sesame-oil",
        "mustard-oil", "neutral-oil", "khoya", "condensed-milk"}
SWEETS = {"sugar", "jaggery", "honey", "condensed-milk"}
PULSES = {"chana-dal", "chickpeas", "dried-peas", "horse-gram", "kala-chana", "lobia",
          "masoor-dal", "moong-dal", "rajma", "sprouted-moth", "toor-dal", "urad-dal",
          "whole-moong", "whole-urad",
          # Gram, ground. The pantry files these two under flours because that
          # is what they are sold as, and this set was copied from that shelf,
          # so a dish built entirely on chickpea flour counted as having no
          # backbone at all: pithla, zunka, khandvi, missi roti and a sattu
          # drink were all refused the tag for containing no pulse, while
          # being nothing but pulse.
          "besan", "sattu"}
LEAN = {"fish", "prawns", "crab", "squid", "chicken", "eggs", "paneer"}
# Red meat counts as a protein backbone like any other. What matters is the
# portion and how it is cooked, not the animal — a slow-braised mutton curry in
# a sensible serving is not worse than the paneer dishes already allowed. The
# per-serving cap below is what does the work.
RED = {"mutton", "beef", "pork", "duck"}

# Per serving, applied to the computed figures at the end of assess().
#
# Fat, saturated fat and sugar do the work. Calories are a backstop and
# nothing more, because for this food they are a bad measure of richness on
# their own: idli is 696 kcal a serving and 1.5g of fat, a steamed cake of
# rice and lentil that no one would call heavy, and a 550 kcal ceiling threw
# it out while a paneer dish at 48g of fat stayed. Plain dosa, varan bhaat and
# pesarattu were going the same way. What makes a dish here heavy is the ghee,
# the cream and the cashew paste, so that is what these lean on, and the
# calorie line sits high enough to catch only a genuinely enormous plate.
#
# Move these four to change what the label means; they are the whole dial. At
# 700/20/7/12 the tagged set runs to a median of 307 kcal, 13.9g fat and 2.1g
# saturated fat, against 401, 18.5 and 5.1 for the database.
MAX_KCAL = 700
MAX_FAT_G = 20
MAX_SATFAT_G = 7
MAX_SUGAR_G = 12
MEAT = (LEAN | RED) - {"paneer", "eggs"}   # parens matter: | binds looser than -
# Raw, bone-in weight. Set deliberately high: a normal Indian curry portion
# passes, and this only catches genuinely outsized ones.
MAX_MEAT_G_PER_SERVING = 250
VEG = {"amaranth-greens", "ash-gourd", "bamboo-shoot", "beetroot", "bitter-gourd",
       "bottle-gourd", "cabbage", "capsicum", "carrot", "cauliflower", "cluster-beans",
       "colocasia", "cucumber", "drumstick", "eggplant", "french-beans", "lotus-stem",
       "methi-leaves", "mushroom", "mustard-greens", "okra", "peas", "pointed-gourd",
       "pumpkin", "radish", "raw-banana", "raw-jackfruit", "raw-papaya", "ridge-gourd",
       "spinach", "spring-onion", "sweet-potato", "tomato", "yam", "corn", "onion",
       "potato"}

FRY = re.compile(r"deep[- ]?fr|for frying|for deep|slip .* into the hot oil|"
                 r"fry in batches|until golden and crisp|deep fat", re.I)
DESSERT = re.compile(r"\b(kheer|halwa|payasam|payesh|barfi|ladoo|laddu|jalebi|"
                     r"malpua|rasgulla|sandesh|basundi|shrikhand|phirni|kulfi|"
                     r"pudding|custard|mithai|mysore pak|chhena poda|dodol|"
                     r"bebinca|tilkut|patishapta|thekua|arsa|modak|puran poli|"
                     r"sheer khurma|double ka meetha|qubani|zarda|mishti doi|"
                     r"rabri|sandesh|seero|malido|kalakand|ghevar|balushahi|"
                     r"adhirasam|obbattu|holige|payasa|kesari|anarsa|imarti)\b", re.I)

TBSP = {"tsp": 1 / 3.0, "teaspoon": 1 / 3.0, "tbsp": 1.0, "tablespoon": 1.0,
        "cup": 16.0, "ml": 1 / 15.0, "g": 1 / 14.0}


def tbsp_of(qty):
    """Rough tablespoons from a free-text quantity. Unparseable reads as 0."""
    if not qty:
        return 0.0
    q = qty.lower().replace("½", "0.5").replace("¼", "0.25").replace("¾", "0.75")
    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+)", q)
    n = None
    if m:
        n = float(m.group(1)) / float(m.group(2))
    else:
        m = re.search(r"(\d+(?:\.\d+)?)", q)
        if m:
            n = float(m.group(1))
    if n is None:
        return 0.0
    for unit, mult in sorted(TBSP.items(), key=lambda x: -len(x[0])):
        if re.search(r"\b%s\b" % unit, q):
            return n * mult
    return 0.0


def grams_of(qty):
    """Grams from a free-text quantity. Unparseable or unitless reads as 0, so a
    missing weight never fails a recipe on portion grounds."""
    if not qty:
        return 0.0
    q = qty.lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*kg\b", q)
    if m:
        return float(m.group(1)) * 1000
    m = re.search(r"(\d+(?:\.\d+)?)\s*g\b", q)
    if m:
        return float(m.group(1))
    return 0.0


# A panful, not a spoonful. Matches build-nutrition.py's FRY_BATH_GRAMS: below
# this the oil is a measured amount that mostly ends up in the food, above it
# the food is sitting in a bath and most of it goes back in the bottle.
FRY_BATH_ML = 100
BATH = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|g|l\b|litres?|liters?)", re.I)


def is_oil_bath(qty_text):
    """True if this quantity describes deep frying rather than a few spoons."""
    if not re.search(r"\bfry|\bfrying\b", qty_text, re.I):
        return False
    for m in BATH.finditer(qty_text):
        unit = m.group(2).lower()
        ml = float(m.group(1)) * (1000 if unit.startswith(("l", "lit")) else 1)
        if ml >= FRY_BATH_ML:
            return True
    return False


def assess(r):
    """Return (is_healthy, reason_it_failed_or_None)."""
    serves = max(1, r.get("servings") or 4)
    ess = [i for i in r["ingredients"] if i.get("essential", True)]
    ids = {i["id"] for i in ess}
    text = " ".join([s["text"] for s in r["steps"]] +
                    [s.get("tip") or "" for s in r["steps"]] +
                    # The oil ingredient too, but only when the quantity is a
                    # bath. Reading only the method let murukku, thattai,
                    # chakli and seedai through — all four a pan of oil deep,
                    # all four tagged healthier — because their steps say "fry
                    # on medium until the bubbling stops" and never say deep,
                    # while the ingredient line says "500ml for deep frying".
                    #
                    # The quantity has to decide it, not the phrase: kathal ki
                    # sabzi says "6 tbsp, 4 for frying the jackfruit" and
                    # macha besara "5 tbsp, 4 for frying the fish". Both match
                    # "for frying" and neither is deep-fried. Same threshold
                    # build-nutrition.py uses to decide what to discount for
                    # absorption.
                    [t for i in r["ingredients"]
                     for t in [(i.get("qty") or "") + " " + (i.get("note") or "")]
                     if is_oil_bath(t)])

    # The method text alone missed dishes that announce frying up front —
    # "fried breads", "fried paneer" — so the name and subtitle count too.
    # "stir-fried" is excluded; that is a dry pan technique, not deep frying.
    label = r["name"] + " " + r.get("subtitle", "")
    if FRY.search(text) or re.search(r"(?<!stir-)(?<!stir )\bfried\b", label, re.I):
        return False, "fried"
    if DESSERT.search(r["name"]) or DESSERT.search(r.get("subtitle", "")):
        return False, "dessert"
    if "maida" in ids:
        return False, "refined flour"

    fat = sum(tbsp_of(i["qty"]) for i in ess if i["id"] in FATS)
    if fat / serves > 1.5:
        return False, "fat %.1f tbsp/serving" % (fat / serves)

    sweet = sum(tbsp_of(i["qty"]) for i in ess if i["id"] in SWEETS)
    if sweet / serves > 1 / 3.0:          # 1 tsp per serving
        return False, "sugar %.1f tsp/serving" % (sweet / serves * 3)

    meat_g = sum(grams_of(i["qty"]) for i in ess if i["id"] in MEAT)
    if meat_g / serves > MAX_MEAT_G_PER_SERVING:
        return False, "portion %.0fg meat/serving" % (meat_g / serves)

    if not (ids & PULSES or ids & LEAN or ids & RED or len(ids & VEG) >= 2):
        return False, "no vegetable, pulse or protein backbone"

    # The finished dish, not just what went into it.
    #
    # Every rule above this line constrains what is *added* to a recipe, and
    # for a long time that was the whole test. It did not work. Measured
    # against the site's own nutrition figures, the tagged set had a median of
    # 391 kcal against 401 for the database, 18.4g of fat against 18.5, and
    # slightly *more* saturated fat than the average recipe. Paneer Butter
    # Masala at 48.8g of fat was tagged. So was a cake.
    #
    # The reason is that the added-fat rule counts ghee and oil poured in, and
    # misses fat that arrives inside an ingredient — cream, cashew paste,
    # coconut, paneer — while the added-sugar rule misses the sugar already in
    # jaggery-sweet vegetables. The figures below are computed and printed on
    # every recipe page; not consulting them here was the whole bug.
    n = (r.get("nutrition") or {}).get("perServing")
    if not n:
        # No figures means no way to stand behind the claim.
        return False, "no nutrition figures"
    if n["kcal"] > MAX_KCAL:
        return False, "kcal %d/serving" % n["kcal"]
    if n["fat"] > MAX_FAT_G:
        return False, "fat %.0fg/serving" % n["fat"]
    if n["satFat"] > MAX_SATFAT_G:
        return False, "satfat %.0fg/serving" % n["satFat"]
    if n["sugars"] > MAX_SUGAR_G:
        return False, "sugar %.0fg/serving" % n["sugars"]

    return True, None


def main(write=False):
    path = os.path.join(ROOT, "data", "recipes.json")
    db = json.load(open(path, encoding="utf-8"))
    healthy, rejected = [], {}
    for r in db["recipes"]:
        ok, why = assess(r)
        tags = [t for t in r["tags"] if t != "healthier"]
        if ok:
            tags.append("healthier")
            healthy.append(r["id"])
        else:
            rejected.setdefault(why.split()[0], []).append(r["id"])
        # Sorted, not appended. Appending put "healthier" last while every
        # other tool leaves the list alphabetical, so a run of this script
        # rewrote the tag order on 290 recipes and showed up as a 290-file
        # diff that changed nothing anyone could see.
        r["tags"] = sorted(tags)

    print("healthier: %d of %d (%.0f%%)" % (len(healthy), len(db["recipes"]),
                                          100.0 * len(healthy) / len(db["recipes"])))
    print("\nrejected by reason:")
    for why, ids in sorted(rejected.items(), key=lambda x: -len(x[1])):
        print("  %-16s %3d" % (why, len(ids)))

    if write:
        json.dump(db, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("\nwritten to data/recipes.json")
    else:
        print("\n(report only — pass --write to apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main("--write" in sys.argv))
