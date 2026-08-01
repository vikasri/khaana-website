#!/usr/bin/env python3
"""Compute per-recipe nutrition from USDA data and the curated ingredient map.

    python3 tools/build-nutrition.py /path/to/FoodData_Central_sr_legacy_food_json.json

Writes data/nutrition.json (the per-ingredient reference table) and adds a
"nutrition" block to every recipe in data/recipes.json.

Method, stated here because the site states it to readers too:

  * Nutrients come from USDA FoodData Central SR Legacy, US-government public
    domain. Ingredients are mapped to USDA foods by hand in
    tools/nutrition-map.py — automatic name matching was tried and got 94 of
    174 wrong, including paneer as "Papad" and a cup of water as 37 kcal.

  * Quantities are converted to grams using USDA's own household-measure
    weights for that food, so a teaspoon of turmeric is 3.0 g rather than a
    generic 5 g.

  * Figures are for raw ingredients as bought. Cooking changes weight — water
    boils off, batter absorbs oil — and none of that is modelled.

  * Deep-frying oil is counted at ABSORB_FRACTION of the oil listed, not the
    whole amount, because most of it stays in the pan.

  * Added salt is excluded, so sodium is not reported at all rather than
    reported wrongly.

Anything that cannot be quantified is counted as zero and recorded in
"unquantified", so a recipe's coverage is visible instead of implied.
"""
import json, os, re, sys, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(ROOT, "data", "recipes.json")
OUT = os.path.join(ROOT, "data", "nutrition.json")

spec = importlib.util.spec_from_file_location("nmap", os.path.join(ROOT, "tools", "nutrition-map.py"))
NM = importlib.util.module_from_spec(spec)
spec.loader.exec_module(NM)

WANT = {
    "Energy": "kcal",
    "Protein": "protein",
    "Total lipid (fat)": "fat",
    "Fatty acids, total saturated": "satFat",
    "Fatty acids, total monounsaturated": "monoFat",
    "Fatty acids, total polyunsaturated": "polyFat",
    "Carbohydrate, by difference": "carbs",
    "Fiber, total dietary": "fibre",
    "Total Sugars": "sugars",
}

# Most oil in a deep-frying pan goes back in the bottle. Published absorption
# for battered and fried foods runs roughly 10-20% of the oil used.
ABSORB_FRACTION = 0.15
# ml -> g. Water-like by default; fats are lighter.
DENSITY = {"oil": 0.92, "ghee": 0.91, "milk": 1.03, "default": 1.0}

FRACTIONS = {"1/2": 0.5, "1/4": 0.25, "3/4": 0.75, "1/3": 1/3, "2/3": 2/3,
             "1/8": 0.125, "1 1/2": 1.5, "2 1/2": 2.5}
VAGUE = re.compile(r"to taste|as needed|as required|to finish|to serve|for garnish|"
                   r"a few|handful|pinch|sprig|to drizzle|for dusting", re.I)
FRYING = re.compile(r"for (deep[- ]?)?fry|for frying", re.I)


def num(tok):
    tok = tok.strip()
    if tok in FRACTIONS:
        return FRACTIONS[tok]
    m = re.match(r"^(\d+)\s+(\d)/(\d)$", tok)          # "1 1/2"
    if m:
        return int(m.group(1)) + int(m.group(2)) / int(m.group(3))
    m = re.match(r"^(\d+)/(\d+)$", tok)
    if m:
        return int(m.group(1)) / int(m.group(2))
    try:
        return float(tok)
    except ValueError:
        return None


def to_grams(qty, ing_id, portions, note=""):
    """Return (grams, how) or (None, reason)."""
    q = (qty or "").strip()
    if not q:
        return None, "no quantity"

    # An explicit gram figure anywhere wins: "4 large (about 500g)" is 500 g.
    m = re.search(r"(\d+(?:\.\d+)?)\s*(g|kg)\b", q, re.I)
    if m:
        g = float(m.group(1)) * (1000 if m.group(2).lower() == "kg" else 1)
        return g, "stated grams"

    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|l)\b", q, re.I)
    if m:
        ml = float(m.group(1)) * (1000 if m.group(2).lower() == "l" else 1)
        d = DENSITY["oil"] if "oil" in ing_id else DENSITY.get(ing_id, DENSITY["default"])
        return ml * d, "volume"

    head = re.match(r"^\s*(\d+\s+\d/\d|\d+/\d+|\d+(?:\.\d+)?)\s*(.*)$", q)
    if not head:
        if FRYING.search(q):
            return None, "frying oil, unquantified"
        return None, "vague" if VAGUE.search(q) else "unparsed"
    n = num(head.group(1))
    rest = head.group(2).lower()
    if n is None:
        return None, "unparsed"

    if re.match(r"^tbsp|^tablespoon", rest):
        g = portions.get("tbsp")
        return (n * g, "tbsp") if g else (n * 15 * DENSITY["default"], "tbsp (generic 15 ml)")
    if re.match(r"^tsp|^teaspoon", rest):
        g = portions.get("tsp")
        return (n * g, "tsp") if g else (n * 5 * DENSITY["default"], "tsp (generic 5 ml)")
    if rest.startswith("cup"):
        g = next((v for k, v in portions.items() if k.startswith("cup")), None)
        return (n * g, "cup") if g else (n * 240 * DENSITY["default"], "cup (generic 240 ml)")

    # A count: "2 medium", "15", "4 cloves". USDA portion keys are messy, and a
    # naive substring test picks disastrous ones: eggs have "cup (4.86 large
    # eggs)" at 243 g, which matched on "large" and turned 4 eggs into 972 g;
    # almonds have "oz (23 whole kernels)" at 28 g, which matched on "whole" and
    # turned 15 almonds into 425 g. Volume and weight units are excluded first.
    UNIT_KEYS = ("cup", "oz", "tbsp", "tsp", "slice", "ring", "ground", "slivered",
                 "sliced", "chopped", "diced", "gram", "ml", "fl ")
    singles = {k: v for k, v in portions.items() if not any(u in k for u in UNIT_KEYS)}
    for key in ("medium", "large", "small", "whole", "each", "piece", "clove", "pod", "pepper"):
        if key in rest:
            g = next((v for k, v in singles.items() if k == key or k.startswith(key)), None)
            if g:
                return n * g, key
    # No size word: prefer the plainest single-item portion available.
    for key in ("medium", "large", "each", "piece", "fruit", "pepper", "clove", "almond", "nut"):
        g = next((v for k, v in singles.items() if k == key or k.startswith(key)), None)
        if g:
            return n * g, "count (%s)" % key
    if singles:
        k, g = sorted(singles.items(), key=lambda kv: kv[1])[0]
        # A single item weighing over half a kilo is a parsing failure, not a food.
        if g <= 500:
            return n * g, "count (%s)" % k
    return None, "count, no unit weight"


def main(usda_path):
    usda = json.load(open(usda_path, encoding="utf-8"))
    foods = usda.get("SRLegacyFoods") or list(usda.values())[0]
    by_desc = {f["description"]: f for f in foods}

    table = {}
    for iid, desc in NM.MAP.items():
        if iid in NM.ZERO or desc is None:
            table[iid] = {"usda": None, "per100": {k: 0 for k in WANT.values()},
                          "portions": {}, "note": "contributes no energy in the amounts used"}
            continue
        f = by_desc.get(desc)
        if not f:
            print("  ! unresolved: %s -> %s" % (iid, desc))
            continue
        per100 = {}
        for n in f.get("foodNutrients", []):
            nm = (n.get("nutrient") or {}).get("name")
            unit = ((n.get("nutrient") or {}).get("unitName") or "").lower()
            if nm in WANT and (unit in ("g", "kcal")):
                per100[WANT[nm]] = round(n.get("amount") or 0, 2)
        ports = {}
        for p in f.get("foodPortions", []):
            k = (p.get("modifier") or (p.get("measureUnit") or {}).get("name") or "").lower().strip()
            if k and p.get("gramWeight"):
                ports.setdefault(k, p["gramWeight"])
        entry = {"usda": f["description"], "fdcId": f["fdcId"],
                 "per100": per100, "portions": ports}
        if iid in NM.APPROX:
            entry["approx"] = NM.APPROX[iid]
        table[iid] = entry

    doc = json.load(open(RECIPES, encoding="utf-8"))
    keys = ["kcal", "protein", "fat", "satFat", "monoFat", "polyFat", "carbs", "fibre", "sugars"]
    done = 0
    coverage = []
    for r in doc["recipes"]:
        tot = {k: 0.0 for k in keys}
        grams = 0.0
        unquant, approx_used = [], set()
        for ing in r["ingredients"]:
            info = table.get(ing["id"])
            if not info:
                unquant.append(ing["id"]); continue
            if info.get("usda") is None:
                continue                                   # water and friends
            g, how = to_grams(ing.get("qty"), ing["id"], info.get("portions", {}),
                              ing.get("note") or "")
            if g is None:
                if how == "frying oil, unquantified":
                    # counted, but only the share that ends up in the food
                    g = 250 * ABSORB_FRACTION
                    how = "frying oil at %d%% absorption" % (ABSORB_FRACTION * 100)
                else:
                    unquant.append(ing["id"]); continue
            elif FRYING.search((ing.get("qty") or "") + " " + (ing.get("note") or "")):
                # "500ml" with a note of "for deep frying" is a panful, not an
                # ingredient. Only the absorbed share reaches the plate.
                g *= ABSORB_FRACTION
                how += " (frying, %d%% absorbed)" % (ABSORB_FRACTION * 100)
            if "approx" in info:
                approx_used.add(ing["id"])
            grams += g
            for k in keys:
                tot[k] += info["per100"].get(k, 0) * g / 100

        if grams <= 0:
            continue
        servings = r.get("servings") or 4
        n = {
            "perServing": {k: round(tot[k] / servings, 1) for k in keys},
            "per100g": {k: round(tot[k] / grams * 100, 1) for k in keys},
            "totalGrams": round(grams),
            "servingGrams": round(grams / servings),
            "unquantified": sorted(set(unquant)),
            "approximated": sorted(approx_used),
            "method": ("Estimated from raw ingredients using USDA FoodData Central. "
                       "Cooking losses are not modelled and added salt is excluded, "
                       "so sodium is not given."),
        }
        n["perServing"]["kcal"] = round(tot["kcal"] / servings)
        n["per100g"]["kcal"] = round(tot["kcal"] / grams * 100)

        # Not every figure deserves equal trust. Two things degrade it: a large
        # share of the ingredient list that could not be turned into grams, and
        # dishes where much of the weighed input is not eaten — syrup a sweet
        # soaks in, batter that yields more than the stated servings.
        share = len(n["unquantified"]) / max(1, len(r["ingredients"]))
        blob = (r["name"] + " " + (r.get("subtitle") or "")).lower()
        soaky = any(w in blob for w in ("syrup", "soaked in", "batter", "fermented batter"))
        n["confidence"] = ("low" if share > 0.30 or soaky
                           else "medium" if share > 0.15 else "good")
        if soaky:
            n["caveat"] = ("Much of the weighed input may not be eaten — syrup left in the "
                           "bowl, or batter that yields more than the stated servings.")
        r["nutrition"] = n
        done += 1
        coverage.append(len(n["unquantified"]) / max(1, len(r["ingredients"])))

    json.dump({"_method": n["method"], "ingredients": table},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(doc, open(RECIPES, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("ingredient table: %d entries (%d approximate)"
          % (len(table), sum(1 for v in table.values() if "approx" in v)))
    print("recipes with nutrition: %d of %d" % (done, len(doc["recipes"])))
    print("mean share of ingredients unquantified: %.1f%%"
          % (100 * sum(coverage) / max(1, len(coverage))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
