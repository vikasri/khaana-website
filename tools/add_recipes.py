#!/usr/bin/env python3
"""Append recipes to data/recipes.json from a compact authoring format.

Recipes are written here as terse tuples and expanded into the full schema, so
authoring effort goes into the cooking rather than JSON punctuation. Re-running
is safe: an id that already exists is skipped, never duplicated.

    python3 tools/add_recipes.py
"""
import collections, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Photos are credited per file in CREDITS.md. Key = filename, value = (alt, credit, licence).
# Only dishes whose photo genuinely depicts them get one; everything else runs
# photo-less rather than borrowing a picture of a different dish.
PHOTO = {
 "awadhi-g1.jpg":   ("Galouti kebabs", "Fatimahope", "CC BY-SA 4.0"),
 "awadhi-g2.jpg":   ("Nalli nihari", "Nilanjan Sasmal", "CC BY-SA 4.0"),
 "awadhi-hero.jpg": ("Lucknowi mutton dum biryani", "Kalesh", "CC BY-SA 4.0"),
 "bengali-g1.jpg":  ("Rasgulla in syrup", "Mdsmds0", "CC BY-SA 4.0"),
 "bengali-g2.jpg":  ("Shorshe ilish, hilsa in mustard", "Unknown", "See CREDITS.md"),
 "bengali-hero.jpg":("Kosha mangsho, slow-cooked mutton", "Unknown", "See CREDITS.md"),
 "goan-g2.jpg":     ("Bebinca, the layered Goan cake", "Warren Noronha", "CC BY 2.0"),
 "goan-hero.jpg":   ("Vindaloo", "Alpha from Melbourne, Australia", "CC BY-SA 2.0"),
 "gujarati-g2.jpg": ("Undhiyu", "Jatan1992", "CC BY-SA 4.0"),
 "hyderabadi-g1.jpg":("Hyderabadi haleem", "Chandu7299", "CC BY-SA 4.0"),
 "hyderabadi-g2.jpg":("Qubani ka meetha", "Miansari66", "CC0"),
 "hyderabadi-hero.jpg":("Hyderabadi dum biryani", "Mahi Tatavarty", "CC BY-SA 4.0"),
 "kashmiri-g1.jpg": ("Kashmiri pulav", "Renupradhul", "CC BY-SA 4.0"),
 "kashmiri-hero.jpg":("A Kashmiri wazwan spread, in which rogan josh is served",
                      "Draabidwani1", "CC0"),
 "kerala-g2.jpg":   ("Appam served with a curry", "Aiwin Soji", "CC BY-SA 4.0"),
 "kerala-hero.jpg": ("An Onam sadya, the feast avial belongs to", "Bhuvana Meenakshi", "CC BY 4.0"),
 "maharashtrian-g1.jpg":("Kolhapuri misal pav", "Unknown", "See CREDITS.md"),
 "maharashtrian-g2.jpg":("Ukadiche modak", "imutkarshpatil", "CC BY-SA 4.0"),
 "northeast-g1.jpg":("Naga smoked pork with bamboo shoot", "Satdeep Gill", "CC BY-SA 4.0"),
 "northeast-g2.jpg":("Steamed momos", "efk.apple", "CC BY-SA 4.0"),
 "odia-g1.jpg":     ("Chhena poda", "Subhransuphotography", "CC BY-SA 4.0"),
 "rajasthani-g2.jpg":("Raj kachori", "Jaipuriamanasi", "CC BY-SA 4.0"),
 "rajasthani-hero.jpg":("Dal baati", "Unknown", "See CREDITS.md"),
 "south-indian-g1.jpg":("Idli", "Unknown", "See CREDITS.md"),
 "south-indian-g2.jpg":("Sambar", "Unknown", "See CREDITS.md"),
}

REGION_PAGE = {
 "Awadhi/Lucknowi": "awadhi-lucknowi.html", "Kashmiri": "kashmiri.html",
 "Punjabi": "punjabi.html", "Rajasthani": "rajasthani.html",
 "Gujarati": "gujarati.html", "Maharashtrian": "maharashtrian.html",
 "Goan": "goan.html", "Kerala": "kerala.html", "South Indian": "south-indian.html",
 "Hyderabadi": "hyderabadi.html", "Odia": "odia.html", "Bengali": "bengali.html",
 "Northeast Indian": "northeast-indian.html",
 # Cuisines without a region page of their own yet. recipe.js renders the
 # region as plain text rather than a dead link when this is None.
 "Bihari": None, "Sindhi": None, "Parsi": None, "Chettinad": None,
 "Himachali": None,
}


def R(rid, name, region, sub, serves, prep, cook, diff, equip, tags, allerg,
      ings, notes, steps, storage, gloss=(), photo=None):
    """ings: (id, qty, note|None, essential). steps: (text, tip|None, glossary|None)."""
    rec = collections.OrderedDict()
    rec["id"] = rid
    rec["name"] = name
    rec["subtitle"] = sub
    rec["region"] = region
    rec["regionPage"] = REGION_PAGE[region]
    if photo:
        alt, credit, lic = PHOTO[photo]
        rec["image"] = collections.OrderedDict([
            ("src", "assets/images/" + photo), ("alt", alt),
            ("credit", credit), ("license", lic),
            ("sourceUrl", "https://commons.wikimedia.org/"),
        ])
    else:
        rec["image"] = None
    rec["servings"] = serves
    rec["prepMinutes"] = prep
    rec["cookMinutes"] = cook
    rec["difficulty"] = diff
    rec["equipment"] = list(equip)
    rec["tags"] = list(tags)
    rec["allergens"] = list(allerg)
    rec["ingredients"] = [
        collections.OrderedDict(
            [("id", i[0]), ("qty", i[1])]
            + ([("note", i[2])] if i[2] else [])
            + [("essential", i[3])]
        ) for i in ings
    ]
    rec["prepNotes"] = list(notes)
    rec["steps"] = [
        collections.OrderedDict(
            [("text", s[0])]
            + ([("tip", s[1])] if len(s) > 1 and s[1] else [])
            + ([("glossary", s[2])] if len(s) > 2 and s[2] else [])
        ) for s in steps
    ]
    rec["storage"] = storage
    rec["glossary"] = list(gloss)
    rec["provenance"] = collections.OrderedDict([
        ("recipeVersion", "1.0.0"), ("updated", "2026-07-31"),
        ("source", "Khaana editorial"),
    ])
    return rec


def install(new_recipes):
    path = os.path.join(ROOT, "data", "recipes.json")
    db = json.load(open(path, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
    have = {r["id"] for r in db["recipes"]}
    added = 0
    for rec in new_recipes:
        if rec["id"] in have:
            continue
        db["recipes"].append(rec)
        have.add(rec["id"])
        added += 1
    db["recipes"].sort(key=lambda r: (r["region"], r["name"]))
    db["version"] = "2.0.0"
    json.dump(db, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("added %d, total %d" % (added, len(db["recipes"])))
    return 0


if __name__ == "__main__":
    from recipes_batch import BATCH
    sys.exit(install(BATCH))
