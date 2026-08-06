"""Recipe batch, expanded by tools/add_recipes.py into data/recipes.json.

One dish: baati chokha, the Bhojpuri belt's plain cousin to litti chokha.

On the region. Baati chokha belongs to Purvanchal — Banaras, Ghazipur, Ballia
— and western Bihar, which is one food culture across a state line. Of the
twenty-one cuisines here, Bihari is the one that already carries it: its page
is "a Gangetic plain cuisine built on roasted gram, mustard oil and live
embers", which is this dish described. Awadhi is the wrong shelf despite being
the same state, because Awadhi on this site means the Nawabs' court kitchen
and this is a field lunch cooked on cow-dung cakes.

On the difference from litti. The litti is stuffed with sattu and the baati is
not, and everything else follows from that: the baati is quicker, it is
kneaded a little richer to make up for the plain middle, and it wants more
ghee at the end.
"""
from add_recipes import R

E, M, A = "easy", "moderate", "advanced"
STOVE, PC, STEAM, BLEND, OVEN, KADHAI, TAWA = (
    "stovetop", "pressure-cooker", "steamer", "blender", "oven", "kadhai", "tawa")
VEG, VGN, GF, DF, NF, NOG = (
    "vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free", "no-onion-garlic")

BATCH = [

# ---------------------------------------------------------------- Bihari
R("baati-chokha", "Baati Chokha", "Bihari",
  "Plain wheat balls baked till they crack, drowned in ghee, with a smoky mash of "
  "brinjal, tomato and potato",
  4, 30, 45, M, [OVEN, STOVE], [VEG, NF], ["dairy", "gluten", "mustard"],
  [("atta", "400g", None, True),
   ("ghee", "8 tbsp", "4 into the dough, 4 to drown the baatis at the end", True),
   ("ajwain", "1 tsp", None, True),
   ("nigella", "1/2 tsp", None, False),
   ("eggplant", "1 large, about 400g", "the big round kind, not the slim purple one", True),
   ("tomato", "3 medium", None, True),
   ("potato", "2 medium, about 250g", None, True),
   ("garlic", "8 cloves", "4 roasted whole in the brinjal, 4 raw and crushed", True),
   ("green-chilli", "4, finely chopped", None, True),
   ("onion", "1 small, finely chopped", None, True),
   ("mustard-oil", "3 tbsp", "raw, stirred into the chokha at the end", True),
   ("coriander-leaves", "1/2 cup, chopped", None, False),
   ("lemon", "1", None, False),
   ("salt", "to taste", None, True),
   ("water", "about 200ml, for the dough", None, True)],
  ["A baati is not a litti. There is no sattu filling, so the dough carries the "
   "whole dish: knead 4 tbsp of ghee into the flour before any water goes in, "
   "and it bakes short and crumbly rather than hard.",
   "The dough wants to be firm — firmer than a chapati dough and nowhere near a "
   "puri's. Too soft and the balls slump and steam instead of cracking open.",
   "Over coals is the original and still the best. A hot oven is the honest "
   "substitute; a gas tandoor or an air fryer both work. What none of them give "
   "you is the smoke, which is why the chokha is charred rather than roasted."],
  [("Rub the ghee into the atta with the ajwain, nigella and salt until it clumps "
    "when squeezed. Add water a little at a time to a firm dough. Rest 30 minutes, "
    "covered.",
    "Rub the fat in before the water. Afterwards it sits on the surface and the "
    "baati bakes hard."),
   ("Heat the oven to 200C. Rub the brinjal with a little oil, push the four whole "
    "garlic cloves into slits in it, and roast it with the tomatoes and the "
    "unpeeled potatoes for 35-40 minutes, until the brinjal has collapsed and its "
    "skin is blistered black.",
    "Charred skin is the point, not an accident. That is where the smoke comes "
    "from without a fire."),
   ("Divide the dough into 8 and roll each into a smooth ball, sealing every crack "
    "with your palms. Bake at 200C for 25 minutes, turn them over, and give them "
    "another 15-20 until they are deep gold and split across the top.",
    "The split is how you know: a baati that has not cracked open is still raw in "
    "the middle."),
   ("Peel the roasted vegetables while they are warm. Mash the brinjal, tomato, "
    "potato and roasted garlic together coarsely — a mash, not a puree.",),
   ("Beat in the raw crushed garlic, green chilli, onion, mustard oil, salt, "
    "coriander and a squeeze of lemon. Taste it: chokha should be sharp enough to "
    "cut through the ghee that is coming.",
    "The mustard oil goes in raw and last. Cooked, it loses the pungency the dish "
    "is built around."),
   ("Dunk each hot baati in melted ghee, crush it open with your hand, and eat it "
    "with the chokha.",
    "Crushed by hand, at the table. Cutlery makes crumbs of it.")],
  "Chokha keeps two days refrigerated and is arguably better on the second, though "
  "the raw mustard oil fades — beat in another spoonful. Baatis are best within the "
  "hour; after that they go dense, and reviving them means 10 minutes in a hot oven "
  "and fresh ghee.",
  ["tadka"], None),

]
