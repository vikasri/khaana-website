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
  * it has a real vegetable, pulse or lean-protein backbone — at least two
    vegetables, or a pulse, or fish/chicken/eggs

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
          "whole-moong", "whole-urad"}
LEAN = {"fish", "prawns", "crab", "squid", "chicken", "eggs", "paneer"}
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


def assess(r):
    """Return (is_healthy, reason_it_failed_or_None)."""
    serves = max(1, r.get("servings") or 4)
    ess = [i for i in r["ingredients"] if i.get("essential", True)]
    ids = {i["id"] for i in ess}
    text = " ".join([s["text"] for s in r["steps"]] +
                    [s.get("tip") or "" for s in r["steps"]])

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

    if not (ids & PULSES or ids & LEAN or len(ids & VEG) >= 2):
        return False, "no vegetable, pulse or lean protein backbone"
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
        r["tags"] = tags

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
