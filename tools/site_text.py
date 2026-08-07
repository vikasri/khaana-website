#!/usr/bin/env python3
"""Every sentence that appears on more than one page of khaana.com.

    Edit here. Then run:  python3 tools/rebuild.py

This file is the reason you do not have to hunt through 678 pages and a dozen
scripts to change a disclaimer. Nothing here runs; it is only text. The
generators import from it, and the pages are rebuilt from what it says.

The rule for what belongs here: copy that appears on MORE THAN ONE page.
A recipe's own method, a cuisine's history, the note on a single dish are
written for that one page and live with it. The moment a sentence is repeated,
it belongs in this file instead, or the copies drift. They have drifted
before: a contact address went stale on 680 pages, and a caveat kept pointing
at a "+" on the numbers months after the "+" was removed.

Some of these carry legal weight. If you reword the allergen or liability
lines, that is a decision about what the site promises, not a style edit.
"""

# ---------------------------------------------------------------------------
# The footer, on all 678 pages
# ---------------------------------------------------------------------------

BRAND_TAGLINE = ("The history, traditions and recipes behind India's regional "
                 "cuisines.")

FEEDBACK_LINK = "Send feedback"


# ---------------------------------------------------------------------------
# Recipe pages, all 651
# ---------------------------------------------------------------------------

# Under the allergen line. Names what was actually checked, which matters:
# saying "allergens: none" without saying which ten were looked at claims more
# than the site can support.
ALLERGEN_SCOPE = ("Checked against the ingredient list for ten allergens: "
                  "milk, egg, fish, crustaceans, tree nuts, peanuts, sesame, "
                  "mustard, soy and gluten. Brands vary, so read the label on "
                  "anything new to you.")

ALLERGEN_NONE = "none of the ten listed below"

# At the foot of every recipe. The honest statement of what these pages are.
PROVENANCE = ("Times, yields, allergens and nutrition are guidance. "
              "Use your own judgement on doneness and on storing.")


# ---------------------------------------------------------------------------
# Safe internal temperatures, on the 209 recipes with meat, fish or egg
#
# Which of these a recipe prints is decided by tools/derive-doneness.py from
# its ingredients. These sentences sit ALONGSIDE the recipe's own cue, never
# instead of it: "until the oil separates and the mutton pulls off the bone"
# tells a cook something a thermometer cannot, and a temperature tells them
# something the look of the pan cannot.
#
# Figures are the FDA and USDA FSIS minimums. Do not round them; 63C and 145F
# are the same number in two scales and both are the published value.
# ---------------------------------------------------------------------------

DONENESS = {
    "poultry": "Chicken and duck are done at 74°C / 165°F, taken at the "
               "thickest part and clear of the bone.",
    "ground": "Minced meat is done at 71°C / 160°F all the way through.",
    # Braises are the common case here and they overshoot this by an hour, so
    # the sentence says so rather than leaving a cook wondering whether their
    # two-hour rogan josh has somehow undershot.
    "whole-red": "Whole cuts of mutton, beef and pork are done at 63°C / "
                 "145°F, rested 3 minutes. A long braise passes that well "
                 "before the meat is tender.",
    "fish": "Fish is done at 63°C / 145°F, or when it turns opaque and "
            "flakes easily.",
    # FSIS gives no temperature for these, so neither do we.
    "shellfish": "Prawns, crab and squid are done when the flesh is opaque and "
                 "pearly right through.",
    "egg": "Egg dishes are done at 71°C / 160°F; a whole egg when the "
           "yolk and white are both firm.",
}

DONENESS_REHEAT = "Reheat leftovers to 74°C / 165°F."

DONENESS_SOURCE = ("<a href=\"https://www.foodsafety.gov/food-safety-charts/"
                   "safe-minimum-internal-temperatures\" rel=\"noopener\">"
                   "FoodSafety.gov</a>")


# ---------------------------------------------------------------------------
# Nutrition notes
#
# Kept short on purpose. This paragraph once ran to 640 characters and said
# the same thing three times; a caveat nobody finishes reading protects
# nobody. The confidence badge in the heading already gives the level, and
# PROVENANCE above already says the figures are worked out rather than
# measured, so nothing here should repeat either.
# ---------------------------------------------------------------------------

NUTRITION_SOURCE = ("Estimated from raw ingredients using "
                    "<a href=\"https://fdc.nal.usda.gov/\" rel=\"noopener\">"
                    "USDA FoodData Central</a>.")

# Which way the error runs. More useful than saying an error exists.
NUTRITION_UNDERSTATED = ("Ingredients given to taste count as zero, so the "
                         "real figures run a little higher.")

NUTRITION_OVERSTATED_SYRUP = ("Syrup left in the bowl, or batter that yields "
                              "more than the stated servings, means the real "
                              "figures are likely lower.")

NUTRITION_OVERSTATED_WHEY = ("Whey poured away when the milk is curdled means "
                             "much of the weighed input is never eaten, so "
                             "the real figures are likely lower.")

# What became of the cooking water, said only where there is enough of it to
# matter. The per-serving column cannot move either way: nutrients divide by
# servings, not by weight. Only the serving weight and the per-100 g column do.
NUTRITION_WATER = {
    "served wet": ("The serving weight counts the water the dish is served in, "
                   "less what a simmer takes off."),
    "dried off": ("The serving weight counts only the water the pulses and "
                  "grains hold; the rest is cooked off."),
    "drained": ("Water that is drained away is not counted in the serving "
                "weight."),
    "evaporated": ("The serving weight counts the water the pulses and grains "
                   "hold; the rest is taken to boil away."),
    "not cooked": ("Nothing here is cooked, so the serving weight counts the "
                   "water in the glass."),
}


def nutrition_approximated(ingredients):
    """Named when the database had no exact match for an ingredient."""
    shown = ", ".join(i.replace("-", " ") for i in ingredients[:4])
    tail = "." if len(ingredients) <= 4 else ", and others."
    return "Nearest database match used for " + shown + tail


# ---------------------------------------------------------------------------
# Liability, on the About page
#
# This is the one block on the site written to be read by someone deciding
# whether Khaana is answerable for how a dish turned out. Reword it only
# deliberately.
# ---------------------------------------------------------------------------

DISCLAIMER_USE = ("Khaana recipes are helpful guides, not guaranteed outcomes. "
                  "Ingredients, equipment, technique and taste vary, and "
                  "recipes may contain errors or omissions. Please use your "
                  "own judgement and follow appropriate food-safety practices. "
                  "Always check ingredients and product labels for allergens "
                  "or dietary suitability. Khaana is not responsible or liable "
                  "for dissatisfaction, loss, injury or illness resulting from "
                  "use of its recipes or website. Nothing here is medical or "
                  "nutritional advice.")
