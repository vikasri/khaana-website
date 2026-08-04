#!/usr/bin/env python3
"""Generate fun-facts.html from data/trivia.json.

    python3 tools/build-trivia.py

Four questions a day out of sixty, chosen by the date, so the whole set comes
round every fifteen days and everybody looking at the page on the same day sees
the same four.

Why the questions are written into the page rather than fetched
---------------------------------------------------------------

All sixty ship in the HTML, and the script picks today's four on load. That is
the wrong instinct for a big dataset and the right one for this: sixty
questions is about 18 KB, less than one recipe photograph, and it buys three
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
PER_DAY = 4


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
<meta name="description" content="Four food trivia questions a day, from %d in all. Where the chilli came from, why milk beats water on a burnt tongue, and what vindaloo is actually named after." />
<link rel="canonical" href="https://khaana.com/fun-facts.html" />

<meta property="og:type" content="website" />
<meta property="og:site_name" content="Khaana" />
<meta property="og:title" content="Food Trivia | Khaana" />
<meta property="og:description" content="Four food trivia questions a day, from %d in all." />
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
    <p class="trivia-intro">Four questions a day, drawn from %d. They change at
      midnight and the whole set comes round every %d days, so there is no way
      to binge it and no reason to come back twice in one day.</p>

    <div class="trivia-head">
      <p class="trivia-day" id="trivia-day"></p>
      <p class="trivia-score" id="trivia-score" hidden></p>
    </div>

    <ol class="trivia-list" id="trivia-list">
%s
    </ol>

    <p class="trivia-foot" id="trivia-foot" hidden>
      That is today's four. <a href="cook.html">Go and cook something</a>, or
      come back tomorrow for the next set.</p>

    <noscript><p class="trivia-intro">All %d questions are listed above, with
      their answers. The four-a-day version needs JavaScript.</p></noscript>
  </div>
</section>

%s

<script src="script.js"></script>
<script src="assets/js/trivia.js"></script>
</body>
</html>
""" % (len(qs), len(qs), nav, len(qs), days, body, len(qs), foot)

    open(OUT, "w", encoding="utf-8").write(page)
    print("fun-facts.html written: %d questions, %d a day, a %d-day cycle"
          % (len(qs), PER_DAY, days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
