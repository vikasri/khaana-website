#!/usr/bin/env python3
"""Generate fun-facts.html from data/trivia.json.

    python3 tools/build-trivia.py

Five questions a day out of the whole bank, chosen by the date, so the set
comes round every len(questions) / 5 days and everybody looking at the page on
the same day sees the same five.

Nothing about that mechanism appears on the page. The reader gets five
questions and an invitation to come back tomorrow; the rotation is the site's
business, not theirs.

Why the questions are written into the page rather than fetched
---------------------------------------------------------------

Every question ships in the HTML, and the script picks today's five on load.
That is the wrong instinct for a big dataset and the right one for this: the
whole bank is a few tens of KB, well under one recipe photograph, and it buys
three things a fetch would cost. The page works with no second request. The answers
and the notes are in the markup, so a search engine and a reader with
JavaScript off both get the whole thing as a plain list. And there is no
flash of empty page while a JSON file loads.

The trade is that the answers are visible to anyone who opens the page source.
For a bar-trivia page about where the samosa came from, that is not a threat
model.
"""
import html, json, os, re, sys

import site_text as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "trivia.json")
INDEX = os.path.join(ROOT, "data", "recipes-index.json")
OUT = os.path.join(ROOT, "fun-facts.html")
PER_DAY = 5

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
    "Bihari": ["Aloo Parwal ki Tarkari", "Aloo ki Bhujia", "Anarsa", "Ghugni",
               "Kadhi Bari", "Machhli ka Jhor", "Sarson Wala Aloo",
               "Silbatte ki Chutney"],
    "Goan": ["Patoleo", "Sanna", "Solkadhi"],
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


def chrome():
    """Nav and footer, copied from cook.html the way the recipe pages do."""
    src = open(os.path.join(ROOT, "cook.html"), encoding="utf-8").read()
    nav = re.search(r'<header class="site-header">.*?</header>', src, re.S).group(0)
    nav = nav.replace(' class="active"', '')
    foot = re.search(r'<footer class="site-footer">.*?</footer>', src, re.S).group(0)
    return nav, foot


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
            by_region.setdefault(r["region"], []).append(r["name"])

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
    for region, names in by_region.items():
        skip = set(PAIR_SKIP.get(region, ()))
        names = sorted(n for n in names if n not in skip)
        if len(names) < PAIR_MIN:
            continue
        if len(names) > PAIR_PER_CUISINE:
            step = len(names) / float(PAIR_PER_CUISINE)
            names = [names[int(i * step)] for i in range(PAIR_PER_CUISINE)]
        pool[region] = names
    return pool


def question_html(n, q):
    opts = "\n".join(
        '            <li><button type="button" class="tq-opt" data-i="%d">'
        '<span class="tq-letter">%s</span> %s</button></li>'
        % (i, "ABCD"[i], esc(o)) for i, o in enumerate(q["options"]))
    return """      <li class="tq" data-answer="%d" data-id="%s">
        <p class="tq-q"><span class="tq-n">%d</span>%s</p>
        <ul class="tq-opts">
%s
        </ul>
        <p class="tq-nudge" role="status" aria-live="polite" hidden></p>
        <p class="tq-note" hidden>%s</p>
      </li>""" % (q["answer"], esc(q["id"]), n, esc(q["q"]), opts, esc(q["note"]))


def main():
    db = json.load(open(SRC, encoding="utf-8"))
    qs = db["questions"]
    if len(qs) % PER_DAY:
        print("  ! %d questions is not a whole number of days of %d"
              % (len(qs), PER_DAY))
    nav, foot = chrome()
    # As data, not as script: the page hands the messages to trivia.js without
    # either of them owning a second copy of the copy.
    nudges = json.dumps(db.get("wrongMessages") or [], ensure_ascii=False)
    body = "\n".join(question_html(n + 1, q) for n, q in enumerate(qs))
    days = len(qs) // PER_DAY

    pool = pair_pool()
    pool_json = json.dumps(pool, ensure_ascii=False, sort_keys=True)
    # As with the nudges: the game's lines live in data/trivia.json and reach
    # pair.js through the page, so no script owns a second copy of the copy.
    pair_msgs = json.dumps(db.get("pairMessages") or {}, ensure_ascii=False)

    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Food Trivia: Fun Facts About Indian Cooking | Khaana</title>
<meta name="description" content="Food trivia from India and beyond. Where the chilli really came from, why milk beats water on a burnt tongue, and what vindaloo is actually named after." />
<link rel="canonical" href="https://khaana.com/fun-facts.html" />

<meta property="og:type" content="website" />
<meta property="og:site_name" content="Khaana" />
<meta property="og:title" content="Food Trivia | Khaana" />
<meta property="og:description" content="Where the chilli really came from, why milk beats water on a burnt tongue, and what vindaloo is actually named after." />
<meta property="og:url" content="https://khaana.com/fun-facts.html" />
<meta property="og:image" content="https://khaana.com/assets/images/home-hero.jpg" />
<meta name="twitter:card" content="summary_large_image" />

<link rel="stylesheet" href="style.css" />
</head>
<body>

%s

<section class="tight">
  <div class="container trivia-page">
    <div class="section-head">
      <div class="eyebrow">Fun facts</div>
      <h1>Food Trivia</h1>
    </div>
    <p class="trivia-intro">Try this food trivia. Come here again tomorrow
      for more fun facts.</p>

    <div class="pair-launch" id="pair-launch" hidden>
      <button type="button" class="pair-start" id="pair-start"
              aria-expanded="false" aria-controls="pair-game">Play Match Dishes
        with Cultural Cuisines</button>
    </div>

    <section class="pair" id="pair-game" hidden aria-labelledby="pair-title">
      <div class="pair-head">
        <h2 id="pair-title">Match each dish to its cuisine</h2>
        <div class="pair-scoring">
          <p class="pair-rule">Correct +2, wrong -1</p>
          <p class="pair-meter">
            <span class="pair-attempt" id="pair-attempt">Attempt 1</span>
            <span class="pair-score" id="pair-score" data-neg="0">Score 0 / 8</span>
          </p>
        </div>
      </div>
      <p class="pair-how">Drag a cuisine onto the box beside a dish, or tap the
        cuisine and then the box.</p>
      <div class="pair-board">
        <ol class="pair-rows" id="pair-rows"></ol>
        <div class="pair-bank" id="pair-bank" role="group"
             aria-label="Cuisines to place"></div>
      </div>
      <p class="pair-verdict" id="pair-verdict" role="status"
         aria-live="polite" hidden></p>
    </section>
    <script type="application/json" id="pair-pool">%s</script>
    <script type="application/json" id="pair-messages">%s</script>

    <div class="trivia-head">
      <p class="trivia-day" id="trivia-day"></p>
      <div class="trivia-head-right">
        <div class="trivia-scoring">
          <p class="trivia-rule">Correct +2, wrong -1</p>
          <p class="trivia-score" id="trivia-score" hidden>Score 0 / 10</p>
        </div>
        <button type="button" class="trivia-sound" id="trivia-sound"
                aria-pressed="true">Sound on</button>
      </div>
    </div>

    <ol class="trivia-list" id="trivia-list">
%s
    </ol>
    <script type="application/json" id="trivia-nudges">%s</script>

    <p class="trivia-foot" id="trivia-foot" hidden>
      More tomorrow. Meanwhile, <a href="cook.html">go and cook something</a>.</p>

    <noscript><p class="trivia-intro">Every question and answer is listed
      above.</p></noscript>
  </div>
</section>

%s

<script src="script.js"></script>
<script src="assets/js/trivia.js"></script>
<script src="assets/js/pair.js"></script>
</body>
</html>
""" % (nav, pool_json, pair_msgs, body, nudges, foot)

    open(OUT, "w", encoding="utf-8").write(page)
    print("fun-facts.html written: %d questions, %d a day, a %d-day cycle"
          % (len(qs), PER_DAY, days))
    print("  matching game: %d dishes across %d cuisines"
          % (sum(len(v) for v in pool.values()), len(pool)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
