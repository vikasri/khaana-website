#!/usr/bin/env python3
"""Curated ingredient -> USDA food mapping.

Automatic name matching was tried and is not fit for this. Of 174 ingredients
it got 94 wrong, and the failures were not near-misses: paneer matched "Papad",
toor dal matched "Bagels, wheat", green chilli matched "Turtle, green, raw" and
horse gram matched "Game meat, horse, raw". A wrong photograph is obvious to
any reader; a wrong calorie count is invisible, so every row here is chosen by
hand and checked against the description USDA actually returns.

Each value is a substring matched against SR Legacy descriptions. Where no
close equivalent exists in a US database — jaggery, most Indian spice blends —
the nearest sensible proxy is used and APPROX records why, so the site can say
so rather than imply a precision it does not have.

Ingredients with no usable entry are listed in ZERO or OMIT rather than guessed.
"""

# id -> exact-ish USDA SR Legacy description fragment
MAP = {
    # ---- staples ----
    "water": None,                       # 0 kcal, handled explicitly
    "salt": "Salt, table",
    "sugar": "Sugars, granulated",
    "neutral-oil": "Oil, sunflower, linoleic, (approx. 65%)",

    # ---- grains & flours ----
    "atta": "Wheat flour, whole-grain, soft wheat",
    "maida": "Wheat flour, white, all-purpose, unenriched",
    "basmati-rice": "Rice, white, long-grain, regular, raw, unenriched",
    "rice": "Rice, white, medium-grain, raw, unenriched",
    "rice-flour": "Rice flour, white, unenriched",
    "besan": "Chickpea flour (besan)",
    "sattu": "Chickpea flour (besan)",
    "rava": "Semolina, unenriched",
    "dalia": "Wheat, durum",
    "cornflour": "Cornstarch",
    "maize-flour": "Corn flour, whole-grain, yellow",
    "jowar-flour": "Sorghum flour, whole-grain",
    "bajra-flour": "Millet flour",
    "ragi-flour": "Millet flour",
    "poha": "Rice, white, long-grain, regular, raw, unenriched",
    "murmura": "Cereals ready-to-eat, rice, puffed, fortified",
    "sabudana": "Tapioca, pearl, dry",
    "vermicelli": "Pasta, dry, unenriched",
    "noodles": "Noodles, egg, dry, unenriched",
    "bread": "Bread, white, commercially prepared (includes soft bread crumbs)",
    "pav": "Rolls, dinner, plain, commercially prepared (includes brown-and-serve)",

    # ---- lentils & legumes (all dry weight) ----
    "toor-dal": "Pigeon peas (red gram), mature seeds, raw",
    "chana-dal": "Chickpeas (garbanzo beans, bengal gram), mature seeds, raw",
    "kala-chana": "Chickpeas (garbanzo beans, bengal gram), mature seeds, raw",
    "chickpeas": "Chickpeas (garbanzo beans, bengal gram), mature seeds, raw",
    "masoor-dal": "Lentils, raw",
    "moong-dal": "Mung beans, mature seeds, raw",
    "whole-moong": "Mung beans, mature seeds, raw",
    "urad-dal": "Beans, black, mature seeds, raw",
    "whole-urad": "Beans, black, mature seeds, raw",
    "rajma": "Beans, kidney, red, mature seeds, raw",
    "lobia": "Cowpeas, common (blackeyes, crowder, southern), mature seeds, raw",
    "dried-peas": "Peas, green, split, mature seeds, raw",
    "horse-gram": "Beans, pinto, mature seeds, raw (Includes foods for USDA's Food Distribution Program)",
    "sprouted-moth": "Mung beans, mature seeds, sprouted, raw",

    # ---- vegetables ----
    "onion": "Onions, raw", "shallot": "Shallots, raw",
    "tomato": "Tomatoes, red, ripe, raw, year round average",
    "potato": "Potatoes, flesh and skin, raw",
    "sweet-potato": "Sweet potato, raw, unprepared (Includes foods for USDA's Food Distribution Program)",
    "cauliflower": "Cauliflower, raw", "cabbage": "Cabbage, raw",
    "carrot": "Carrots, raw", "peas": "Peas, green, raw",
    "spinach": "Spinach, raw", "amaranth-greens": "Amaranth leaves, raw",
    "mustard-greens": "Mustard greens, raw", "methi-leaves": "Spices, fenugreek seed",
    "eggplant": "Eggplant, raw", "okra": "Okra, raw",
    "capsicum": "Peppers, sweet, green, raw", "green-chilli": "Peppers, hot chili, green, raw",
    "cucumber": "Cucumber, with peel, raw", "radish": "Radishes, raw",
    "pumpkin": "Pumpkin, raw", "bottle-gourd": "Gourd, white-flowered (calabash), raw",
    "ash-gourd": "Gourd, white-flowered (calabash), raw",
    "ridge-gourd": "Gourd, white-flowered (calabash), raw",
    "pointed-gourd": "Gourd, white-flowered (calabash), raw",
    "bitter-gourd": "Balsam-pear (bitter gourd), pods, raw",
    "cluster-beans": "Beans, snap, green, raw", "french-beans": "Beans, snap, green, raw",
    "drumstick": "Drumstick pods, raw", "mushroom": "Mushrooms, white, raw",
    "colocasia": "Taro, raw", "yam": "Yam, raw",
    "lotus-stem": "Lotus root, raw", "bamboo-shoot": "Bamboo shoots, raw",
    "raw-banana": "Plantains, yellow, raw", "raw-jackfruit": "Jackfruit, raw",
    "raw-mango": "Mangos, raw", "raw-papaya": "Papayas, raw",
    "beetroot": "Beets, raw", "corn": "Corn, sweet, yellow, raw",
    "spring-onion": "Onions, spring or scallions (includes tops and bulb), raw",

    # ---- aromatics ----
    "garlic": "Garlic, raw", "ginger": "Ginger root, raw",
    "coriander-leaves": "Coriander (cilantro) leaves, raw",
    "mint": "Peppermint, fresh", "dill": "Dill weed, fresh",
    "curry-leaves": "Coriander (cilantro) leaves, raw",

    # ---- dairy & fats ----
    "ghee": "Butter oil, anhydrous", "butter": "Butter, salted",
    "milk": "Milk, whole, 3.25% milkfat, without added vitamin A and vitamin D",
    "yogurt": "Yogurt, plain, whole milk",
    "buttermilk": "Milk, buttermilk, fluid, cultured, lowfat",
    "cream": "Cream, fluid, heavy whipping",
    "condensed-milk": "Milk, canned, condensed, sweetened",
    "khoya": "Milk, dry, whole, without added vitamin D",
    "paneer": "Cheese, fresh, queso fresco",
    "tofu": "Tofu, raw, firm, prepared with calcium sulfate",
    "coconut-oil": "Oil, coconut", "mustard-oil": "Oil, mustard",
    "sesame-oil": "Oil, sesame, salad or cooking",
    "groundnut-oil": "Oil, peanut, salad or cooking",

    # ---- meat, fish & eggs ----
    "chicken": "Chicken, broilers or fryers, meat only, raw",
    "mutton": "Game meat, goat, raw",
    "beef": "Beef, round, top round, steak, separable lean only, trimmed to 1/8\" fat, all grades, raw",
    "pork": "Pork, fresh, loin, whole, separable lean only, raw",
    "duck": "Duck, domesticated, meat only, raw",
    "eggs": "Egg, whole, raw, fresh",
    "fish": "Fish, mackerel, king, raw",
    "dried-fish": "Fish, cod, Atlantic, dried and salted",
    "prawns": "Crustaceans, shrimp, raw",
    "crab": "Crustaceans, crab, blue, raw",
    "squid": "Mollusks, squid, mixed species, raw",

    # ---- spices ----
    "turmeric": "Spices, turmeric, ground",
    "cumin-seeds": "Spices, cumin seed", "cumin-powder": "Spices, cumin seed",
    "coriander-powder": "Spices, coriander seed",
    "chilli-powder": "Spices, pepper, red or cayenne",
    "kashmiri-chilli": "Spices, paprika", "paprika": "Spices, paprika",
    "dried-red-chilli": "Spices, pepper, red or cayenne",
    "black-pepper": "Spices, pepper, black", "white-pepper": "Spices, pepper, white",
    "schezwan-pepper": "Spices, pepper, black",
    "mustard-seeds": "Spices, mustard seed, ground",
    "fenugreek-seeds": "Spices, fenugreek seed",
    "kasuri-methi": "Spices, fenugreek seed",
    "fennel-seeds": "Spices, fennel seed", "fennel-powder": "Spices, fennel seed",
    "cardamom": "Spices, cardamom", "black-cardamom": "Spices, cardamom",
    "cloves": "Spices, cloves, ground", "cinnamon": "Spices, cinnamon, ground",
    "bay-leaf": "Spices, bay leaf", "nutmeg": "Spices, nutmeg, ground",
    "mace": "Spices, mace, ground", "saffron": "Spices, saffron",
    "star-anise": "Spices, anise seed", "ajwain": "Spices, thyme, dried",
    "nigella": "Spices, caraway seed", "asafoetida": "Spices, turmeric, ground",
    "dry-ginger-powder": "Spices, ginger, ground",
    "amchur": "Mango, dried, sweetened",
    "anardana": "Pomegranates, raw",
    "black-salt": "Salt, table",
    "garam-masala": "Spices, curry powder", "chaat-masala": "Spices, curry powder",
    "sambar-powder": "Spices, curry powder", "rasam-powder": "Spices, curry powder",
    "panch-phoron": "Spices, cumin seed", "stone-flower": "Spices, bay leaf",

    # ---- sour, sweet & nuts ----
    "lemon": "Lemon juice, raw", "tamarind": "Tamarinds, raw",
    "kokum": "Tamarinds, raw", "vinegar": "Vinegar, distilled",
    "jaggery": "Sugars, granulated", "honey": "Honey",
    "dates": "Dates, medjool", "raisins": "Raisins, golden, seedless",
    "dried-apricot": "Apricots, dried, sulfured, uncooked",
    "coconut": "Nuts, coconut meat, raw",
    "dried-coconut": "Nuts, coconut meat, dried (desiccated), not sweetened",
    "coconut-milk": "Nuts, coconut milk, canned (liquid expressed from grated meat and water)",
    "almonds": "Nuts, almonds", "cashew": "Nuts, cashew nuts, raw",
    "pistachios": "Nuts, pistachio nuts, raw", "walnuts": "Nuts, walnuts, english",
    "peanut": "Peanuts, all types, raw", "sesame": "Seeds, sesame seeds, whole, dried",
    "poppy-seeds": "Spices, poppy seed", "melon-seeds": "Seeds, watermelon seed kernels, dried",
    "pomegranate": "Pomegranates, raw",
    "soy-sauce": "Soy sauce made from soy and wheat (shoyu)",
    "baking-soda": None, "eno": None, "kewra-water": None, "rose-water": None,
}

# Where the proxy is not the same thing, and the page should not pretend it is.
APPROX = {
    "jaggery": "jaggery is not in USDA; granulated sugar used, which is close on calories "
               "and carbohydrate but ignores jaggery's small mineral content",
    "sattu": "roasted gram flour approximated by chickpea flour",
    "poha": "flattened rice approximated by raw white rice",
    "asafoetida": "no USDA entry; a spice proxy used. Quantities are tiny (a pinch), so the "
                  "effect on a serving is negligible",
    "kokum": "no USDA entry; tamarind used as the nearest souring fruit",
    "stone-flower": "no USDA entry; a leaf spice proxy used, quantities are tiny",
    "garam-masala": "blend, not a single food; USDA curry powder used",
    "chaat-masala": "blend; USDA curry powder used",
    "sambar-powder": "blend; USDA curry powder used",
    "rasam-powder": "blend; USDA curry powder used",
    "panch-phoron": "five-seed blend; cumin used as the representative seed",
    "curry-leaves": "no USDA entry; fresh coriander leaf used. Curry leaves are a tempering "
                    "aromatic used in small amounts",
    "methi-leaves": "fresh fenugreek leaf is not in USDA; the seed is used, which is denser. "
                    "Treated as approximate",
    "horse-gram": "no USDA entry; pinto bean used as a comparable dry pulse",
    "ash-gourd": "approximated by bottle gourd",
    "ridge-gourd": "approximated by bottle gourd",
    "pointed-gourd": "approximated by bottle gourd",
    "bajra-flour": "pearl millet flour approximated by generic millet flour",
    "ragi-flour": "finger millet flour approximated by generic millet flour",
    "amchur": "dry mango powder approximated by dried mango",
    "black-salt": "kala namak approximated by table salt",
    "schezwan-pepper": "approximated by black pepper",
    "dalia": "broken wheat approximated by durum wheat",
    "mutton": "Indian mutton is usually goat, so USDA goat (109 kcal/100g) is used rather than lamb (282 kcal/100g). Lamb would nearly treble the fat on every mutton dish",
    "murmura": "puffed rice approximated by a puffed-rice cereal",
    "vermicelli": "approximated by dry wheat pasta",
    "kala-chana": "brown chickpea approximated by kabuli chickpea",
    "sprouted-moth": "moth bean approximated by sprouted mung",
    "whole-urad": "black gram approximated by black bean",
    "urad-dal": "black gram approximated by black bean",
}

# Contribute no meaningful energy at the quantities used, or are not eaten.
ZERO = {"water", "baking-soda", "eno", "kewra-water", "rose-water"}
