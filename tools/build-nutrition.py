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
import importlib.util, json, math, os, re, sys

# Shared copy. Python puts this script's own directory on sys.path, so a
# plain import finds tools/site_text.py.
import site_text as T

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
FRYING = re.compile(r"for (deep[- |]?)?fry|for frying|for (shallow|pan|deep)[- ]?fry|"
                    r"to (shallow|pan|deep)[- ]?fry", re.I)
# Absorption only applies to a bath the food sits in and most of which goes
# back in the bottle. "400ml, for shallow frying" is a bath; "4 tbsp, for
# shallow frying" is a measured amount that mostly ends up in the food, and
# discounting it by 85% would understate a fried dish rather than overstate it.
FRY_BATH_GRAMS = 100

# Rice quantities are sometimes given already cooked ("2 cups cooked", "600g
# cooked and cooled"), but the USDA entry behind `rice` is raw. Pricing 600 g
# of cooked rice as 600 g of raw rice overstated it nearly threefold, which is
# where Dahi Pakhala's 854 kcal came from.
#
# Cooked rice is raw rice plus water and water has no energy, so the fix is to
# convert the quantity rather than swap in another food. Dividing the raw USDA
# values by 2.77 reproduces USDA's published cooked figures on energy (130),
# protein (2.38), carbohydrate (29) and fat (0.2) simultaneously, which is what
# says the factor is right rather than merely plausible.
HYDRATION = 2.77
COOKED_CUP_G = 180.0        # 195 g raw per cup, hydrated, over the ~3 cups it yields
RICE_IDS = {"rice", "basmati-rice"}
# "1 cup raw, cooked and cooled" is already a raw measure and must not be
# converted again.
COOKED_QTY = re.compile(r"\bcooked|\bleftover|\bday[- ]old", re.I)
RAW_QTY = re.compile(r"\braw\b", re.I)

# Counts whose USDA portion list has no single-item weight that means anything
# in an Indian kitchen. These are ordinary kitchen weights, not USDA figures,
# and they are here because the alternative is worse than an approximation:
#
#   green chilli   USDA's only count portion is "pepper", a bell pepper at 45 g.
#                  An Indian green chilli is about 5 g, so every one of the 304
#                  places a chilli is counted was nine times too heavy.
#   curry leaves   priced at 20 g a sprig across 141 recipes. A sprig carries
#                  ten or twelve leaves and weighs a gram or two.
#   eggplant       "6 small, slit" was matching a portion meaning one whole
#                  1-1/4 lb aubergine, so six small brinjals came to 2.7 kg and
#                  undhiyu to 945 g a serving.
#   chicken pieces 12 winglets came out at 200 g each, a whole quarter bird,
#                  and put Chicken Lollipop at 754 g a serving.
#
# Keyed by (ingredient, word in the quantity); "" matches a bare count.
PIECE_GRAMS = {
    ("chicken", "winglet"): 45.0, ("chicken", "wing"): 45.0,
    ("chicken", "drumstick"): 90.0, ("chicken", "thigh"): 115.0,
    ("green-chilli", ""): 5.0,
    ("curry-leaves", "sprig"): 2.5, ("curry-leaves", ""): 0.3,
    ("coriander-leaves", "sprig"): 3.0,
    ("eggplant", "small"): 60.0, ("eggplant", "brinjal"): 60.0,
}

# A quantity can name a liquid that is not the ingredient: "lime-sized ball,
# soaked in 500ml water" was reading as 500 g of tamarind. The ml belongs to
# the soaking water, which is already weightless in this model.
SOAKING = re.compile(r"soaked in|dissolved in|with \d+\s*ml|in \d+\s*ml (?:of )?(?:warm |hot )?water", re.I)

# Cup weights for ingredients where USDA gives neither a cup nor a tablespoon.
# Ordinary kitchen figures; the alternative is a cup of water at 240 g. Besan
# (92) and maida (125) come from USDA and are left alone.
CUP_GRAMS = {"atta": 120.0, "cashew": 137.0, "dried-coconut": 80.0}


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
    """Return (grams, how) or (None, reason).

    Grams are always the *raw* weight of the ingredient, because that is what
    the USDA entries behind them describe.
    """
    q = (qty or "").strip()
    if not q:
        return None, "no quantity"

    # Rice given in a cooked measure, converted to its raw equivalent first.
    if ing_id in RICE_IDS and COOKED_QTY.search(q) and not RAW_QTY.search(q):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(g|kg)\b", q, re.I)
        if m:
            cooked = float(m.group(1)) * (1000 if m.group(2).lower() == "kg" else 1)
            return cooked / HYDRATION, "cooked grams, raw equivalent"
        head = re.match(r"^\s*(\d+\s+\d/\d|\d+/\d+|\d+(?:\.\d+)?)\s*(.*)$", q)
        if head and head.group(2).lower().startswith("cup"):
            n = num(head.group(1))
            if n is not None:
                return n * COOKED_CUP_G / HYDRATION, "cooked cups, raw equivalent"

    # An explicit gram figure anywhere wins: "4 large (about 500g)" is 500 g.
    m = re.search(r"(\d+(?:\.\d+)?)\s*(g|kg)\b", q, re.I)
    if m:
        g = float(m.group(1)) * (1000 if m.group(2).lower() == "kg" else 1)
        return g, "stated grams"

    # "l" alone matched but "litre", "litres" and "liter" did not, so 69
    # recipes had their largest liquid ingredient silently counted as zero.
    # Harmless for water; it meant 22 milk sweets were missing their milk.
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|millilitres?|litres?|liters?|l)\b", q, re.I)
    if m and not SOAKING.search(q):
        unit = m.group(2).lower()
        ml = float(m.group(1)) * (1 if unit.startswith(("ml", "milli")) else 1000)
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
        if g:
            return n * g, "cup"
        if ing_id in CUP_GRAMS:
            return n * CUP_GRAMS[ing_id], "cup (kitchen weight)"
        # USDA often gives a tablespoon but no cup. Sixteen of its own
        # tablespoons beats falling back to a cup of water, which is what put
        # 3 cups of atta at 720 g and dal baati churma at 1514 kcal.
        tbsp = portions.get("tbsp")
        if tbsp:
            return n * tbsp * 16, "cup (16 x USDA tbsp)"
        return n * 240 * DENSITY["default"], "cup (generic 240 ml)"

    # A count: "2 medium", "15", "4 cloves". USDA portion keys are messy, and a
    # naive substring test picks disastrous ones: eggs have "cup (4.86 large
    # eggs)" at 243 g, which matched on "large" and turned 4 eggs into 972 g;
    # almonds have "oz (23 whole kernels)" at 28 g, which matched on "whole" and
    # turned 15 almonds into 425 g. Volume and weight units are excluded first.
    # Longest word first, so ("curry-leaves", "sprig") is tried before the
    # bare-count fallback ("curry-leaves", "").
    for (iid, word), g in sorted(PIECE_GRAMS.items(), key=lambda kv: -len(kv[0][1])):
        if ing_id == iid and (word in rest if word else True):
            return n * g, "count (%s, kitchen weight)" % (word or "each")
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


def cached_table():
    """The per-ingredient figures already pulled out of the USDA download.

    data/nutrition.json holds the per-100 g values and portion weights for all
    174 mapped ingredients, which is everything the recipe arithmetic needs.
    The 13 MB source archive is not kept in the repository, so a rerun that
    only changes how quantities are interpreted can work from this instead of
    requiring the download again. Pass the archive path to rebuild the table
    itself, which is needed only when an ingredient is added or remapped.
    """
    return json.load(open(OUT, encoding="utf-8"))["ingredients"]


def main(usda_path=None):
    if not usda_path:
        table = cached_table()
        print("using the cached ingredient table (%d entries); pass the USDA "
              "archive path to rebuild it" % len(table))
        return compute(table)

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

    return compute(table)


def compute(table):
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
            elif (FRYING.search((ing.get("qty") or "") + " " + (ing.get("note") or ""))
                  and g >= FRY_BATH_GRAMS):
                # "500ml" with a note of "for deep frying" is a panful, not an
                # ingredient. Only the absorbed share reaches the plate. A few
                # spoonfuls for shallow frying is not a panful and is counted
                # whole; see FRY_BATH_GRAMS.
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
        # Rounded up, not to nearest: these figures already run low because
        # anything added to taste counts as zero.
        n["per100g"]["kcal"] = math.ceil(tot["kcal"] / grams * 100)

        # Not every figure deserves equal trust. Two things degrade it: a large
        # share of the ingredient list that could not be turned into grams, and
        # dishes where much of the weighed input is not eaten — syrup a sweet
        # soaks in, batter that yields more than the stated servings.
        share = len(n["unquantified"]) / max(1, len(r["ingredients"]))
        blob = (r["name"] + " " + (r.get("subtitle") or "")).lower()
        # A dish that curdles milk and throws the whey away has most of the
        # weighed milk leaving the pan. Counting the full 2 litres against a
        # sandesh made from 400 g of chhena is as wrong in one direction as
        # counting none of it was in the other.
        method = " ".join(x["text"] for x in r.get("steps", [])).lower()
        whey = any(w in method for w in ("whey", "curdle", "chhena", "muslin"))
        soaky = whey or any(w in blob for w in
                            ("syrup", "soaked in", "batter", "fermented batter"))
        n["confidence"] = ("low" if share > 0.30 or soaky
                           else "medium" if share > 0.15 else "good")

        # Which way the error runs matters more than that there is one.
        # Anything that could not be weighed is counted as zero, so the real
        # figure is HIGHER than shown — those are marked with a + on the number.
        # Syrup and batter dishes run the other way: the weighed input overstates
        # what is actually eaten, so a + there would be a lie.
        if soaky:
            n["direction"] = "overstated"
            n["caveat"] = (T.NUTRITION_OVERSTATED_WHEY if whey
                           else T.NUTRITION_OVERSTATED_SYRUP)
        elif share > 0.10:
            n["direction"] = "understated"
            # No caveat stored: the page writes NUTRITION_UNDERSTATED from
            # the direction, and storing a second copy is how this line came
            # to be printed twice, one of them still pointing at a "+" that
            # had been taken off the numbers.
            n.pop("caveat", None)
        else:
            n["direction"] = "ok"
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
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
