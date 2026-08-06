"""Recipe batch, expanded by tools/add_recipes.py into data/recipes.json.

Four shorbas.

On the region. Shorba is a Persian word that came in with the Mughals, and the
kitchen on this site that carries that inheritance is Awadhi/Lucknowi. Murgh
shorba belongs there without argument — a clear, whole-spice chicken broth is
Mughlai court cooking doing what it does.

The three vegetable shorbas are a looser fit and are filed there because it is
the nearest shelf, not because Lucknow invented them. Tomato-coriander, carrot
and spinach shorbas are twentieth-century hotel and restaurant cooking: the
shorba idea applied to a soup course by kitchens cooking for people who
expected one. That is said in each recipe rather than left for the reader to
assume, and all four stay out of the matching game, where the answer would be
"the nearest available shelf".

On thickening. None of these are thickened with flour. The vegetable ones are
blended and passed, which is what makes them a shorba rather than a puree with
cream in it, and the chicken one is not thickened at all.
"""
from add_recipes import R

E, M, A = "easy", "moderate", "advanced"
STOVE, PC, STEAM, BLEND, OVEN, KADHAI, TAWA = (
    "stovetop", "pressure-cooker", "steamer", "blender", "oven", "kadhai", "tawa")
VEG, VGN, GF, DF, NF, NOG = (
    "vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free", "no-onion-garlic")

BATCH = [

R("tomato-dhaniya-shorba", "Tomato Dhaniya Shorba", "Awadhi/Lucknowi",
  "Tomatoes simmered with whole spice and blended smooth, finished with enough "
  "coriander to taste green",
  4, 10, 25, E, [STOVE, BLEND], [VEG, GF, NF], ["dairy"],
  [("tomato", "800g ripe, roughly chopped", "the whole dish; use the reddest you can find", True),
   ("coriander-leaves", "1 large bunch, stalks and all", "stalks carry more flavour than the leaves", True),
   ("onion", "1 medium, sliced", None, True),
   ("garlic", "4 cloves, crushed", None, True),
   ("ginger", "1 tbsp, chopped", None, True),
   ("cumin-seeds", "1 tsp", None, True),
   ("bay-leaf", "1", None, False),
   ("black-pepper", "1 tsp, coarsely cracked", None, True),
   ("butter", "1 tbsp", "or oil, which makes it vegan", True),
   ("sugar", "1/2 tsp", "only if the tomatoes are sharp", False),
   ("salt", "to taste", None, True),
   ("water", "700ml", None, True)],
  ["Shorba means a thin soup, and thin is the point: this is not a tomato "
   "puree with water in it. If it coats the spoon, it has been reduced too far.",
   "The coriander goes in twice — the stalks early, where they have time to give "
   "up their flavour, and the leaves at the end, where they keep it."],
  [("Warm the butter and crackle the cumin, then add the bay leaf, onion, garlic "
    "and ginger and cook 4-5 minutes until soft but not coloured.",
    "Not coloured. Browning gives a sweetness that fights the tomato."),
   ("Add the tomatoes, the coriander stalks, the cracked pepper, salt and the "
    "water. Simmer covered 20 minutes, until the tomato skins are curling away.",),
   ("Fish out the bay leaf, blend smooth, and pass through a sieve. Press hard on "
    "what is left in the sieve; that is where the body is.",
    "Sieving is not optional. Tomato skin and seed make it gritty however long "
    "the blender runs."),
   ("Return to the pan, thin with a little hot water if needed, and check the "
    "salt. Add the sugar only if it tastes sharp rather than sweet.",),
   ("Stir in most of the chopped coriander leaves off the heat and serve hot, "
    "with the rest scattered on top.",
    "Off the heat. Coriander boiled for even a minute goes from green to hay.")],
  "Keeps 3 days refrigerated and freezes well, though the coriander fades; hold "
  "back half and add it fresh on reheating.",
  [], None),

R("murgh-shorba", "Murgh Shorba", "Awadhi/Lucknowi",
  "Clear chicken broth drawn slowly off bone and whole spice, peppery and "
  "finished with lemon",
  4, 15, 60, M, [STOVE], [GF, DF, NF], [],
  [("chicken", "700g on the bone, thighs and wings", "bone and skin are what make it a broth", True),
   ("onion", "1 large, quartered", None, True),
   ("ginger", "2 tbsp, sliced", None, True),
   ("garlic", "6 cloves, bruised", None, True),
   ("black-pepper", "2 tsp, whole", "cracked, not ground; ground clouds it", True),
   ("cinnamon", "1 stick", None, True),
   ("cardamom", "4 green, bruised", None, True),
   ("cloves", "4", None, False),
   ("bay-leaf", "2", None, False),
   ("coriander-leaves", "a handful, to finish", None, False),
   ("lemon", "1", None, True),
   ("salt", "to taste", None, True),
   ("water", "1.5 litres", None, True)],
  ["A shorba is judged on clarity. The whole business of skimming and never "
   "letting it boil is what separates a broth from a pale chicken curry.",
   "Whole spices, never powder. Powder cannot be strained out and turns the "
   "surface muddy."],
  [("Cover the chicken with the cold water and bring it slowly to the point of "
    "trembling — not a boil. Skim the grey foam off as it rises, several times.",
    "Cold water and slow heat draw the scum to the top where you can take it. "
    "Straight into hot water and it stays in, and the broth goes cloudy."),
   ("Add the onion, ginger, garlic, peppercorns, cinnamon, cardamom, cloves, bay "
    "leaves and a little salt.",),
   ("Cook uncovered at the barest simmer for 45-50 minutes. A bubble every few "
    "seconds, no more.",
    "A rolling boil emulsifies the fat back into the liquid and no amount of "
    "straining will clear it afterwards."),
   ("Lift out the chicken. Strain the broth through the finest sieve you own, "
    "and skim the fat from the top.",),
   ("Pull the meat off the bone in small pieces and return as much as you want "
    "to the pot. Check the salt, which will need more than seems right.",
    "Broth takes salt in a way a curry does not; season it hot and taste again."),
   ("Finish with a good squeeze of lemon and the coriander, and serve very hot.",
    "The lemon is not a garnish. Without it the whole thing tastes flat.")],
  "Broth keeps 3 days refrigerated and freezes for 3 months. The fat sets on top "
  "in the fridge and lifts off in a sheet, which is the easiest way to degrease it.",
  [], None),

R("gajar-shorba", "Gajar Shorba", "Awadhi/Lucknowi",
  "Carrots cooked down with ginger and blended smooth, sweet against black pepper",
  4, 10, 30, E, [STOVE, BLEND], [VEG, GF, NF], ["dairy"],
  [("carrot", "600g, peeled and chopped", None, True),
   ("onion", "1 medium, chopped", None, True),
   ("ginger", "1 tbsp, chopped", "carries the whole dish against the sweetness", True),
   ("garlic", "2 cloves", None, False),
   ("cumin-seeds", "1 tsp", None, True),
   ("black-pepper", "1 tsp, coarsely cracked", None, True),
   ("butter", "1 tbsp", "or oil, which makes it vegan", True),
   ("cream", "2 tbsp, to finish", "optional; a swirl, not a dose", False),
   ("coriander-leaves", "to finish", None, False),
   ("salt", "to taste", None, True),
   ("water", "800ml", None, True)],
  ["Carrots are sweet and a sweet soup is dull, so the pepper and the ginger are "
   "not seasoning here, they are the other half of the dish. Be heavier with both "
   "than feels right.",
   "Old winter carrots make a better shorba than young ones. They have less water "
   "and more sugar."],
  [("Warm the butter and crackle the cumin. Add the onion, ginger and garlic and "
    "cook 5 minutes until soft.",),
   ("Add the carrots, salt and water. Simmer covered 20-25 minutes, until a piece "
    "crushes against the side of the pan with no resistance.",
    "Undercooked carrot will not blend smooth; it goes fibrous instead of silky."),
   ("Blend until completely smooth, then pass through a sieve.",
    "Carrot has enough fibre to stay slightly rough however good the blender. "
    "The sieve is what makes it a shorba."),
   ("Return to the pan, thin to a pouring consistency with hot water, and add the "
    "cracked pepper. Simmer 2 minutes more so the pepper opens up.",),
   ("Check the salt, swirl in the cream if using, and finish with coriander.",
    "Taste before the cream. It rounds off the pepper, and if the pepper was too "
    "shy to begin with it will disappear altogether.")],
  "Keeps 3 days refrigerated and freezes for a month without the cream, which is "
  "better stirred in on reheating.",
  [], None),

R("palak-shorba", "Palak Shorba", "Awadhi/Lucknowi",
  "Spinach wilted and blended while still green, sharp with garlic and pepper",
  4, 10, 20, E, [STOVE, BLEND], [VEG, GF, NF], ["dairy"],
  [("spinach", "400g, washed", None, True),
   ("onion", "1 small, chopped", None, True),
   ("garlic", "4 cloves, chopped", None, True),
   ("ginger", "2 tsp, chopped", None, True),
   ("green-chilli", "1, slit", None, False),
   ("cumin-seeds", "1 tsp", None, True),
   ("black-pepper", "1 tsp, coarsely cracked", None, True),
   ("butter", "1 tbsp", "or oil, which makes it vegan", True),
   ("milk", "100ml", "optional; softens the iron edge", False),
   ("lemon", "1/2", None, False),
   ("salt", "to taste", None, True),
   ("water", "700ml", None, True)],
  ["Everything here is about keeping it green. Spinach turns from bright to army "
   "khaki in about four minutes of boiling, and no amount of cream brings it back.",
   "Have the blender ready before the spinach goes in. This is a soup that is "
   "cooked in the order of a stir-fry."],
  [("Warm the butter and crackle the cumin, then add the onion, garlic, ginger and "
    "chilli and cook 4 minutes until soft.",),
   ("Add the water and salt and bring to a boil.",),
   ("Drop in the spinach, push it under, and cook 2 minutes at most — until it has "
    "collapsed and no longer.",
    "Two minutes. This is the step the dish lives or dies on."),
   ("Take it off the heat immediately and blend, then pass through a sieve.",
    "Blending it hot off the heat rather than after it has sat keeps the colour; "
    "so does not putting the lid on afterwards."),
   ("Return to the pan, add the cracked pepper and the milk if using, and bring "
    "back to just below a simmer. Do not boil it again.",),
   ("Check the salt, sharpen with lemon, and serve at once.",
    "At once. It is at its best within ten minutes and merely good after thirty.")],
  "Best the day it is made — it dulls in colour overnight, though it still tastes "
  "right. Keeps 2 days refrigerated; reheat gently and never boil.",
  [], None),

]
