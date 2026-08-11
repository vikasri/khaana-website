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
import html, json, math, os, re, sys

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


NAME_MAX = 13          # and MAX_NAME in assets/js/leaderboard.js, which enforces it


def board_half(game, name, span):
    """One game's high-score board. leaderboard.js fills it from the server.

    The game's name leads the title. Side by side the two boards are told
    apart by their colour, which is no use to anyone who cannot see it and no
    use at all once they wrap to stacked on a phone — at that point "(10
    consecutive games)" and "(5 consecutive games)" are the only difference,
    and a reader has to know the rules to work out which is which. The name is
    written the same way the chart below writes it: Trivia and Matching.
    """
    return """      <div class="board" id="board-{g}" data-game="{g}" hidden
           aria-labelledby="board-{g}-title">
        <h2 class="board-title" id="board-{g}-title"><span
          class="board-game">{name}</span> best scores <span
          class="board-rule">({span} consecutive games)</span></h2>
        <ol class="board-rows"></ol>
        <p class="board-you" role="status" aria-live="polite" hidden></p>
      </div>
""".format(g=game, name=esc(name), span=span, cap=NAME_MAX)


def sparks(n=16):
    """The burst over the dialog: spans thrown outward by CSS.

    Every particle's direction, distance and delay is worked out here and
    handed to the stylesheet as custom properties, so the animation stays one
    keyframe rule and the page ships no code to run it. Three distances and
    four delays off the index give it the unevenness a real one has without
    anything random, which matters because a build that changes on every run
    is a build nobody can diff.
    """
    out = ['        <div class="board-sparks" aria-hidden="true">']
    for i in range(n):
        ang = math.radians(360.0 / n * i - 90)
        far = 44 + (i % 3) * 13
        out.append('          <span style="--dx:%.1fpx; --dy:%.1fpx; --d:%dms"></span>'
                   % (math.cos(ang) * far, math.sin(ang) * far, (i % 4) * 70))
    out.append('        </div>')
    return "\n".join(out)


def prompt_html():
    """The dialog that asks for a name, shared by both boards.

    Getting on the board is the one moment in the page worth interrupting for,
    and it used to be a line of small print under a panel the reader had no
    reason to be looking at. Most people would have earned a place and never
    known. A modal is the right size for it: it happens at most once a sitting,
    only to somebody who has just beaten a standing score, and it is the only
    point where the page needs something typed.

    One dialog rather than one per board, because only one can be open. Which
    game it belongs to is written into it when it opens.

    It carries the form, so a browser without <dialog> is not left with nothing
    to submit: leaderboard.js moves this form back into the board it belongs to
    and shows it there instead.
    """
    return """    <dialog class="board-prompt" id="board-prompt">
      <div class="board-prompt-in">
{sparks}
        <p class="board-prompt-cheer" id="board-prompt-cheer"></p>
        <p class="board-prompt-what" id="board-prompt-what"></p>
        <form class="board-join" id="board-join">
          <label class="sr-only" for="board-name">Your name</label>
          <input class="board-name-input" id="board-name" type="text"
                 maxlength="{cap}" autocomplete="off" spellcheck="false"
                 placeholder="Your name" />
          <button type="submit" class="board-add">Add me</button>
          <button type="button" class="board-skip">Not now</button>
          <p class="board-error" id="board-error" role="alert" hidden></p>
        </form>
      </div>
    </dialog>
""".format(sparks=sparks(), cap=NAME_MAX)


def boards_html():
    """Both boards in one panel at the top of the page, side by side.

    It sat under the chart while the board was per-device, because a board kept
    in one browser is empty for everyone arriving for the first time and the
    best position on the page should not be held for something usually not
    there. A shared board is never empty once anybody has played, so the
    argument went with the architecture: it is now the first thing on the page,
    which is where a score to beat belongs.

    They were also a panel each, one under its own game, which read well and
    cost two full-width blocks of a page that already stacks a quiz, a chart
    and a matching game down it. A board of three rows is a narrow thing: side
    by side they take one block instead of two, and both are readable without
    scrolling between them.

    The heading sits outside the box rather than in it, so it reads as a title
    for the thing rather than a fourth label inside a panel that already has
    two. It is wrapped with the box so the two hide together — a heading over
    nothing is worse than no heading.

    The wrapper and the halves ship carrying `hidden`. leaderboard.js opens a
    half when it has something to show and the wrapper when either half is
    open, so a page with no boards yet has no empty frame on it, and neither
    does one with JavaScript off.
    """
    return """    <div class="fun-boards-wrap" id="fun-boards-wrap" hidden>
      <h2 class="fun-boards-title">Leaderboard</h2>
      <section class="fun-boards" id="fun-boards">
%s%s      </section>
    </div>
%s""" % (board_half("trivia", "Trivia", 10), board_half("pair", "Matching", 5),
         prompt_html())


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
%s
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
            <p class="trivia-rule">Correct +2 points, wrong -1 point</p>
            <p class="trivia-score" id="trivia-score" hidden>Score: 0 / 2</p>
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
        <h2 id="pair-title">Match Dishes to Cuisine Category</h2>
        <div class="pair-scoring">
          <p class="pair-rule">Correct +2 points, wrong -1 point</p>
          <p class="pair-meter">
            <span class="pair-attempt" id="pair-attempt">Attempt 1</span>
            <span class="pair-score" id="pair-score" data-neg="0">Score: 0 / 8</span>
          </p>
        </div>
      </div>
      <p class="pair-how">Drag a cuisine to a box, or tap one then the other.</p>
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

    <section class="region" id="region-game" hidden
             aria-labelledby="region-title">
      <div class="region-head">
        <h2 id="region-title">Place the Cuisines on the Map</h2>
        <div class="region-scoring">
          <p class="region-rule">Correct +2 points, wrong -1 point</p>
          <p class="region-meter">
            <span class="region-left" id="region-left"></span>
            <span class="region-score" id="region-score" data-neg="0">Score: 0</span>
          </p>
        </div>
      </div>
      <p class="region-how">Drag a cuisine onto its zone, or tap one then the
        other.</p>
      <div class="region-board">
        <div class="region-map" id="region-map" role="group"
             aria-label="Map of India with the cuisine zones left unnamed"></div>
        <div class="region-bank" id="region-bank" role="group"
             aria-label="Cuisines to place"></div>
      </div>
      <div class="region-foot">
        <p class="region-verdict" id="region-verdict" role="status"
           aria-live="polite" hidden></p>
      </div>
    </section>

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
<script src="assets/js/region.js"></script>
</body>
</html>
""" % (nav, boards_html(), body, nudges, pool_json, pair_msgs, foot)

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
