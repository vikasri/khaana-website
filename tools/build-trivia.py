#!/usr/bin/env python3
"""Generate fun.html from data/trivia.json.

    python3 tools/build-trivia.py

One question at a time, drawn at random by trivia.js, with no repeat until
the bank is used up and then a reshuffle. There is no daily rotation and no
end: a reader who wants to keep going keeps going.

Nothing about that mechanism appears on the page. The reader gets a question
and a button for the next one.

Why the questions are written into the page rather than fetched
---------------------------------------------------------------

Every question ships in the HTML, and the script shows one of them at a time.
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
from pair_pool import pair_pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "trivia.json")
INDEX = os.path.join(ROOT, "data", "recipes-index.json")
OUT = os.path.join(ROOT, "fun.html")

# The matching game's pool, its rules and its exclusions live in
# tools/pair_pool.py, since build-pair-thumbs.py needs the same list.


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def chrome():
    """Nav and footer, copied from cook.html the way the recipe pages do."""
    src = open(os.path.join(ROOT, "cook.html"), encoding="utf-8").read()
    nav = re.search(r'<header class="site-header">.*?</header>', src, re.S).group(0)
    nav = nav.replace(' class="active"', '')
    foot = re.search(r'<footer class="site-footer">.*?</footer>', src, re.S).group(0)
    return nav, foot


def board_html(game, span):
    """The high-score board under a game.

    Two rows, hidden until there is something to put in them. leaderboard.js
    fills it: the rows, the player's own best once they have a full run, and
    the one-per-session prompt for a name. Nothing is written here that the
    reader would see before they had earned it, so the section ships empty and
    carrying `hidden`, the way the chart and the matching game do.
    """
    return """    <section class="board" id="board-%s" data-game="%s" hidden
             aria-labelledby="board-%s-title">
      <h2 class="board-title" id="board-%s-title">Best scores for %d
        consecutive games</h2>
      <ol class="board-rows"></ol>
      <p class="board-you" role="status" aria-live="polite" hidden></p>
      <form class="board-join" hidden>
        <label class="board-join-label" for="board-%s-name">On the board</label>
        <input class="board-name-input" id="board-%s-name" type="text"
               maxlength="16" autocomplete="off" spellcheck="false"
               placeholder="Your name" />
        <button type="submit" class="board-add">Add</button>
        <button type="button" class="board-skip">Not now</button>
        <p class="board-error" role="alert" hidden></p>
      </form>
    </section>
""" % (game, game, game, game, span, game, game)


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
        <div class="tq-after"><p class="tq-note" hidden>%s</p></div>
      </li>""" % (q["answer"], esc(q["id"]), n, esc(q["q"]), opts, esc(q["note"]))


def main():
    db = json.load(open(SRC, encoding="utf-8"))
    qs = db["questions"]
    nav, foot = chrome()
    # As data, not as script: the page hands the messages to trivia.js without
    # either of them owning a second copy of the copy.
    nudges = json.dumps(db.get("wrongMessages") or [], ensure_ascii=False)
    body = "\n".join(question_html(n + 1, q) for n, q in enumerate(qs))

    # [name, thumbnail id] per dish. The id is dropped where the site has no
    # photograph, and the game draws a plain square instead of a broken one.
    pool = pair_pool()
    slim = {region: [[name, rid if img else None] for name, rid, img in entries]
            for region, entries in pool.items()}
    pool_json = json.dumps(slim, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
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
<link rel="canonical" href="https://khaana.com/fun.html" />

<meta property="og:type" content="website" />
<meta property="og:site_name" content="Khaana" />
<meta property="og:title" content="Food Trivia | Khaana" />
<meta property="og:description" content="Where the chilli really came from, why milk beats water on a burnt tongue, and what vindaloo is actually named after." />
<meta property="og:url" content="https://khaana.com/fun.html" />
<meta property="og:image" content="https://khaana.com/assets/images/home-hero.jpg" />
<meta name="twitter:card" content="summary_large_image" />

<link rel="stylesheet" href="style.css" />
</head>
<body>

%s

<section class="tight trivia-section">
  <div class="container trivia-page">
    <p class="trivia-tagline">Put Your or Friend&rsquo;s and Family&rsquo;s Food
      Knowledge to the Test</p>

    <section class="trivia-panel" aria-labelledby="trivia-title">
      <div class="trivia-head">
        <div class="section-head">
          <div class="eyebrow">Fun facts</div>
          <div class="trivia-title-row">
            <h1 id="trivia-title">Food Trivia</h1>
            <p class="trivia-intro">Select one answer</p>
          </div>
        </div>
        <div class="trivia-head-right">
          <div class="trivia-scoring">
            <p class="trivia-rule">Correct +2, wrong -1</p>
            <p class="trivia-score" id="trivia-score" hidden>Score 0 / 2</p>
          </div>
          <button type="button" class="trivia-sound" id="trivia-sound"
                  aria-pressed="true">Sound on</button>
        </div>
      </div>

      <ol class="trivia-list" id="trivia-list">
%s
      </ol>
      <script type="application/json" id="trivia-nudges">%s</script>

      <button type="button" class="trivia-next" id="trivia-next" hidden>Next
        question</button>

      <noscript><p class="trivia-intro">Every question and answer is listed
        above.</p></noscript>
    </section>

%s

    <section class="score-chart" id="score-chart" hidden
             aria-labelledby="score-chart-title">
      <h2 class="score-chart-title" id="score-chart-title">Trivia</h2>
      <div class="score-chart-plot">
        <svg id="score-chart-svg" viewBox="0 0 600 200" width="600" height="200"
             role="img" aria-label="Score by trial"></svg>
      </div>
      <p class="sr-only" id="score-chart-read" role="status" aria-live="polite"></p>
    </section>

    <section class="pair" id="pair-game" hidden aria-labelledby="pair-title">
      <div class="pair-head">
        <h2 id="pair-title">Match dishes to cuisine category</h2>
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
      <div class="pair-foot">
        <p class="pair-verdict" id="pair-verdict" role="status"
           aria-live="polite" hidden></p>
        <button type="button" class="pair-again" id="pair-again" hidden>Play
          next</button>
      </div>
    </section>

%s
    <script type="application/json" id="pair-pool">%s</script>
    <script type="application/json" id="pair-messages">%s</script>

  </div>
</section>

%s

<script src="script.js"></script>
<!-- Before the two games, which register their series and their boards with
     them as they start. -->
<script src="assets/js/score-chart.js"></script>
<script src="assets/js/leaderboard.js"></script>
<script src="assets/js/trivia.js"></script>
<script src="assets/js/pair.js"></script>
</body>
</html>
""" % (nav, body, nudges, board_html("trivia", 10), board_html("pair", 5),
       pool_json, pair_msgs, foot)

    open(OUT, "w", encoding="utf-8").write(page)
    # No day count here any more. The page draws one question at a time at
    # random and does not repeat until the bank is spent, so "five a day" and
    # the cycle length it implied stopped being true when that changed.
    print("fun.html written: %d questions" % len(qs))
    shown = sum(1 for v in pool.values() for e in v if e[2])
    print("  matching game: %d dishes across %d cuisines, %d with a picture"
          % (sum(len(v) for v in pool.values()), len(pool), shown))
    return 0


if __name__ == "__main__":
    sys.exit(main())
