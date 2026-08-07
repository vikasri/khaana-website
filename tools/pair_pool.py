#!/usr/bin/env python3
"""The dish pool the matching game deals from, built from the recipe index.

Imported, not run. Two tools need the same list and neither owns it:
build-trivia.py writes it into the page and build-pair-thumbs.py cuts a
thumbnail for every dish in it. A second copy of these rules would drift, and
the way that would show is a dish in the game with an empty square beside it.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "data", "recipes-index.json")


# Dishes per cuisine in the matching game's pool. Twelve of each is 252 names,
# about 5 KB, which is small enough to ship in the page like the questions and
# deep enough that a reader who plays ten rounds is not seeing repeats.
PAIR_PER_CUISINE = 12
# Four rows a round, so a cuisine with fewer dishes than this could not fill
# the pool honestly and is left out rather than padded.
PAIR_MIN = 4

# Dishes the game will not ask about, because the answer is arguable.
#
# The pairing key is the region a recipe is filed under, and for most of the
# 651 that is uncontroversial. For these it is not, in three ways:
#
#   * Pan-Indian. Samosa, jalebi, masala chai, naan, gajar ka halwa. Filed
#     under Punjabi here and cooked in every one of the other twenty kitchens.
#   * Pan-regional. Idli, dosa, sambar, rasam, upma are no more Tamil than
#     they are Kannadiga or Malayali, and all three cuisines are on the board.
#     The same goes for korma and do-pyaza across Awadhi and Hyderabadi, and
#     for kadhi, phirni, kulfi and rabri across the north.
#   * The same dish under two entries. Solkadhi and Sol Kadhi, Mash Ki Dal and
#     Mah Di Dal, shahi tukda and double ka meetha: whichever the round deals,
#     a reader who knows the other one is right to object.
#
# A regional name in a regional language stays, even where a neighbour has its
# own version under its own name — puran poli against obbattu, patra against
# alu vadi against patrode. Knowing which language a dish is named in is the
# game. Not knowing whether Delhi or Lahore has the better claim is not.
PAIR_SKIP = {
    "Anglo-Indian": ["Bread Pudding", "Coconut Toffee", "Kalkals",
                     "Mutton Cutlets", "Rissoles", "Yellow Coconut Rice"],
    "Awadhi/Lucknowi": ["Arhar ki Dal", "Bhindi do Pyaza", "Boti Kebab",
                        "Gulab Jamun", "Imarti", "Kali Mirch ka Murgh",
                        "Kathal ki Sabzi", "Kulfi", "Murgh Korma",
                        "Murgh Musallam", "Mutton Kaliya", "Mutton Korma",
                        "Nalli Nihari", "Navratan Korma", "Nihari",
                        "Paneer Do Pyaza", "Rabri", "Shahi Tukda",
                        "Shami Kebab", "Zarda", "Zarda Pulao"],
    "Bengali": ["Rasgulla", "Rasmalai"],
    # Baati chokha is Purvanchal before it is Bihari, and eastern Uttar
    # Pradesh is not a cuisine on this site. The recipe stays and says where it
    # is from; the game does not ask a question whose answer is the nearest
    # available shelf. Bafauri sat here for the same reason and has since been
    # removed from the site for having no photograph.
    "Bihari": ["Aloo Parwal ki Tarkari", "Aloo ki Bhujia", "Anarsa",
               "Baati Chokha", "Ghugni", "Kadhi Bari",
               "Machhli ka Jhor", "Sarson Wala Aloo", "Silbatte ki Chutney"],
    # Goan-Portuguese, and so is the Mangalorean Catholic kitchen that is more
    # usually credited with it. Sorpotel and chicken cafreal are Goan without
    # the argument, and the pool has both.
    "Goan": ["Patoleo", "Pork Indad", "Sanna", "Solkadhi"],
    "Gujarati": ["Shrikhand"],
    "Hyderabadi": ["Chicken Biryani", "Methi Murgh", "Murgh do Pyaza",
                   "Mutton Do Pyaza", "Sheer Khurma", "Tala Hua Gosht",
                   "Til Ki Chutney", "Vegetable Biryani"],
    "Indo-Chinese": ["Hot and Sour Soup", "Spring Rolls", "Sweet Corn Soup",
                     "Wonton Soup"],
    "Kashmiri": ["Phirni"],
    "Kerala": ["Semiya Payasam", "Vegetable Korma"],
    "Maharashtrian": ["Chakli", "Pani Puri / Golgappa", "Shankarpali",
                      "Sol Kadhi"],
    "Northeast Indian": ["Momos", "Sel Roti", "Thukpa"],
    "Odia": ["Khaja"],
    "Pahari": ["Mash Ki Dal"],
    "Parsi": ["Chelo Kebab", "Sev"],
    "Punjabi": ["Achari Chicken", "Aloo Chaat", "Aloo Gobi", "Aloo Methi",
                "Aloo Paratha", "Aloo Tikki", "Atte Ka Halwa",
                "Baingan Bharta", "Bharwa Karela", "Bhindi Masala",
                "Boondi Raita", "Bread Pakora", "Chana Masala",
                "Chapati / Phulka", "Chicken Tikka Masala", "Chole",
                "Cucumber Raita", "Dahi Bhalla", "Dal Tadka", "Egg Bhurji",
                "Egg Curry", "Fish Tikka", "Gajar ka Halwa", "Garlic Naan",
                "Jalebi", "Jeera Rice", "Kadai Chicken", "Kadai Paneer",
                "Keema Matar", "Laccha Paratha", "Lauki Kofta",
                "Malai Kofta", "Mango Lassi", "Mango Pickle", "Masala Chai",
                "Matar Paneer", "Methi Malai Matar", "Mint-Coriander Chutney",
                "Missi Roti", "Mixed Vegetable Pakora", "Mooli Paratha",
                "Naan", "Onion Pakora", "Palak Paneer", "Paneer Bhurji",
                "Paneer Butter Masala", "Paneer Tikka", "Papdi Chaat",
                "Samosa", "Seekh Kebab", "Shahi Paneer",
                "Sweet or Salted Lassi", "Tamarind-Date Chutney"],
    "Rajasthani": ["Aam ki Launji", "Aloo Pyaaz ki Sabzi", "Bajre ki Roti",
                   "Besan ki Chakki", "Dahi Wale Aloo", "Moong Dal Halwa"],
    "Tamil Nadu": ["Coconut Chutney", "Curd Rice", "Idli", "Lemon Rice",
                   "Masala Dosa", "Medu Vada", "Paruppu Payasam",
                   "Plain Dosa", "Rasam", "Rava Dosa", "Sambar",
                   "Tomato Chutney", "Upma", "Uttapam"],
}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def pair_pool():
    """Dishes grouped by cuisine, for the matching game to deal rounds from.

    Three kinds of name are dropped, all because they would make a round not
    worth playing:

      * Anything carrying a cuisine's own name. "Hyderabadi Dum Biryani" is
        not a question, it is a label, and one free row in four is most of
        the round. Forty-one of the 651 recipes read that way.
      * Any name held by more than one region, since the pairing key here is
        the region a recipe is filed under and a name filed twice has no
        single right answer. There are none today; this keeps it that way if
        one is ever added.
      * Everything named in PAIR_SKIP above, where the dish is real and the
        filing is reasonable but the answer is arguable.

    Twelve are kept per cuisine, taken at even spacing through the region's
    alphabetical list rather than off the top of it, or every cuisine would
    offer the reader a column of dishes beginning with A.

    Each entry is (name, id, image path or None). The id is what the thumbnail
    is filed under and the image is what it is cut from; a dish the site has no
    photograph of keeps its place in the game and shows a plain square.
    """
    recipes = json.load(open(INDEX, encoding="utf-8"))["recipes"]
    regions = sorted({r["region"] for r in recipes if r.get("region")})
    # "Tamil Nadu" and "Awadhi/Lucknowi" give away a dish by either word, so
    # the test is per word rather than on the whole label.
    words = {w.lower() for reg in regions for w in re.split(r"[ /-]", reg) if w}

    seen = {}
    for r in recipes:
        seen.setdefault(r["name"].lower(), []).append(r)

    by_region = {}
    for name, rows in seen.items():
        if len(rows) > 1 or any(w in name for w in words):
            continue
        r = rows[0]
        if r.get("region"):
            by_region.setdefault(r["region"], []).append(
                (r["name"], r["id"], (r.get("image") or {}).get("src")))

    # Loudly, not quietly. A skipped name that no longer exists means a recipe
    # was renamed or removed, and the entry beside it in PAIR_SKIP is now
    # guarding nothing — which is exactly how a pan-Indian dish would find its
    # way back into the game without anyone noticing.
    known = {r["name"] for r in recipes}
    missing = sorted(n for names in PAIR_SKIP.values() for n in names
                     if n not in known)
    if missing:
        raise SystemExit("PAIR_SKIP names no longer in the index: %s"
                         % ", ".join(missing))

    pool = {}
    for region, entries in by_region.items():
        skip = set(PAIR_SKIP.get(region, ()))
        entries = sorted(e for e in entries if e[0] not in skip)
        if len(entries) < PAIR_MIN:
            continue
        if len(entries) > PAIR_PER_CUISINE:
            step = len(entries) / float(PAIR_PER_CUISINE)
            entries = [entries[int(i * step)] for i in range(PAIR_PER_CUISINE)]
        pool[region] = entries
    return pool
