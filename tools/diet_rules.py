#!/usr/bin/env python3
"""The ingredient groups that decide an allergen or a diet tag.

Imported by tools/derive-allergens.py, which writes the values, and by
tools/validate-recipes.py, which checks them. One definition, so the deriver
and the checker cannot drift apart and agree on something wrong.

These encode labelling rules, not pantry structure, which is why they live
here and not in data/pantry.json.
"""

# --- allergens -------------------------------------------------------------

DAIRY = {"butter", "buttermilk", "condensed-milk", "cream", "ghee", "khoya",
         "milk", "paneer", "yogurt"}

# rava (semolina) and dalia (broken wheat) are wheat despite not being called
# flour; leaving them out would let a gluten-free tag through on an upma.
GLUTEN = {"atta", "maida", "bread", "pav", "vermicelli", "dalia", "rava",
          # Soy sauce is brewed with wheat and egg noodles are wheat.
          "noodles", "soy-sauce",
          # Farsan made only of besan is gluten-free, and plenty of shop
          # mixes carry maida. Listed here because of the two ways to be
          # wrong about a bought mixture, this is the one that costs a
          # coeliac reader nothing.
          "farsan"}

SOY = {"soy-sauce", "tofu"}

# Tree nuts only. Peanut is a legume and a separate declaration everywhere it
# is regulated, so someone allergic to one is not necessarily allergic to the
# other and a single "nuts" line tells them nothing useful.
NUTS = {"almonds", "cashew", "pistachios", "walnuts", "melon-seeds"}

# Groundnut oil is declared alongside whole peanut. Highly refined peanut oil
# is exempt from labelling under both FDA and UK rules, but the exemption is
# for *highly refined* oil, and the groundnut oil sold for Indian cooking is
# very often cold-pressed or filtered, which retains protein. A recipe cannot
# know which bottle the reader owns. Over-declaring costs someone a dish;
# under-declaring costs them a hospital visit.
PEANUT = {"peanut", "groundnut-oil"}

# US labelling counts coconut as a tree nut; Indian cooking never does, and
# treating it as one would put a nuts warning on most of Kerala and Goa. So
# coconut does not force a declaration or block `nut-free` — but a recipe that
# declares nuts because of it is not flagged as over-declaring.
NUT_ADJACENT = NUTS | PEANUT | {"coconut", "dried-coconut", "coconut-milk"}

EGG = {"eggs"}

SESAME = {"sesame", "sesame-oil"}

# panch phoron is a five-spice blend and one of the five is mustard seed.
MUSTARD = {"mustard-seeds", "mustard-oil", "mustard-greens", "panch-phoron"}

# Finned fish and crustaceans are separate declarations under FDA and UK rules.
FISH = {"fish", "dried-fish"}
CRUSTACEAN = {"prawns", "crab"}

# name -> ingredient ids. Order is the order they print on the page.
ALLERGEN_GROUPS = [
    ("dairy", DAIRY),
    ("gluten", GLUTEN),
    ("egg", EGG),
    ("fish", FISH),
    ("crustacean", CRUSTACEAN),
    ("nuts", NUTS),
    ("peanut", PEANUT),
    ("sesame", SESAME),
    ("mustard", MUSTARD),
    ("soy", SOY),
]
ALLERGENS = {name for name, _ in ALLERGEN_GROUPS}

# What justifies a declaration that has no exact ingredient match, so an
# over-cautious label is not reported as an error.
JUSTIFIES = {"nuts": NUT_ADJACENT, "peanut": NUT_ADJACENT}


# --- diet tags -------------------------------------------------------------

MEAT = {"beef", "chicken", "duck", "mutton", "pork"}
SEAFOOD = FISH | CRUSTACEAN | {"squid"}
ALLIUM = {"onion", "garlic", "shallot", "spring-onion"}

# Vegetarian on this site excludes egg. That is what the word means to most
# people cooking Indian food, and a filter that returned akuri to someone
# who ticked "vegetarian" would be worse than useless to them. Egg dishes are
# still findable by name, by region and by ingredient.
NON_VEGETARIAN = MEAT | SEAFOOD | EGG
NON_VEGAN = NON_VEGETARIAN | DAIRY | {"honey"}

# Course tags say what kind of dish it is rather than who may eat it. They ride
# in the same list because the Cook page filters on `tags`, and a second list
# would mean a second filter mechanism for no gain.
COURSE = {"soup"}

TAGS = {"vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free",
        "egg-free", "no-onion-garlic", "pescatarian",
        # Derived by tools/tag-healthy.py from explicit thresholds.
        "healthier"} | COURSE

# tag -> ingredients that contradict it
TAG_BLOCKERS = {
    "vegan": NON_VEGAN,
    "vegetarian": NON_VEGETARIAN,
    "dairy-free": DAIRY,
    "gluten-free": GLUTEN,
    "nut-free": NUTS | PEANUT,
    "egg-free": EGG,
    "no-onion-garlic": ALLIUM,
    "pescatarian": MEAT,
}
