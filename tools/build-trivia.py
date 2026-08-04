#!/usr/bin/env python3
"""Generate fun-facts.html from data/trivia.json.

    python3 tools/build-trivia.py

Five questions a day out of a hundred, chosen by the date, so the whole set
comes round every twenty days and everybody looking at the page on the same day
sees the same five.

Nothing about that mechanism appears on the page. The reader gets five
questions and an invitation to come back tomorrow; the rotation is the site's
business, not theirs.

Why the questions are written into the page rather than fetched
---------------------------------------------------------------

All hundred ship in the HTML, and the script picks today's five on load. That
is the wrong instinct for a big dataset and the right one for this: a hundred
questions is about 30 KB, well under one recipe photograph, and it buys three
things a fetch would cost. The page works with no second request. The answers
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
OUT = os.path.join(ROOT, "fun-facts.html")
PER_DAY = 5


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def chrome():
    """Nav and footer, copied from cook.html the way the recipe pages do."""
    src = open(os.path.join(ROOT, "cook.html"), encoding="utf-8").read()
    nav = re.search(r'<header class="site-header">.*?</header>', src, re.S).group(0)
    nav = nav.replace(' class="active"', '')
    foot = re.search(r'<footer class="site-footer">.*?</footer>', src, re.S).group(0)
    return nav, foot


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
        <p class="tq-note" hidden>%s</p>
      </li>""" % (q["answer"], esc(q["id"]), n, esc(q["q"]), opts, esc(q["note"]))


def main():
    db = json.load(open(SRC, encoding="utf-8"))
    qs = db["questions"]
    if len(qs) % PER_DAY:
        print("  ! %d questions is not a whole number of days of %d"
              % (len(qs), PER_DAY))
    nav, foot = chrome()
    body = "\n".join(question_html(n + 1, q) for n, q in enumerate(qs))
    days = len(qs) // PER_DAY

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

    <div class="trivia-head">
      <p class="trivia-day" id="trivia-day"></p>
      <div class="trivia-head-right">
        <p class="trivia-score" id="trivia-score" hidden>Score 0 / 10</p>
        <button type="button" class="trivia-sound" id="trivia-sound"
                aria-pressed="true">Sound on</button>
      </div>
    </div>

    <ol class="trivia-list" id="trivia-list">
%s
    </ol>

    <p class="trivia-foot" id="trivia-foot" hidden>
      More tomorrow. Meanwhile, <a href="cook.html">go and cook something</a>.</p>

    <noscript><p class="trivia-intro">Every question and answer is listed
      above.</p></noscript>
  </div>
</section>

%s

<script src="script.js"></script>
<script src="assets/js/trivia.js"></script>
</body>
</html>
""" % (nav, body, foot)

    open(OUT, "w", encoding="utf-8").write(page)
    print("fun-facts.html written: %d questions, %d a day, a %d-day cycle"
          % (len(qs), PER_DAY, days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
