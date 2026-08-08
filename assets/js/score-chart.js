/* Fun facts: the running score, drawn.
 *
 * One frame, two games. The trivia and the matching game both score the same
 * way — two for a right answer, one off for a wrong one — so both produce the
 * same shape of number: a total that climbs, dips and can go negative. Given
 * two frames the reader would compare them side by side, which is not the
 * comparison worth making; given one, the chart is about the game they are
 * playing right now and the title says which.
 *
 * A trial is one scored move: an answer in the trivia, a marked attempt in the
 * matching game. Trial 0 is the score before either has happened, so every
 * line starts at the origin and the first move is a visible step off it.
 *
 * The frame is redrawn from the series each time rather than patched. A score
 * line is at most a few dozen points and rebuilding it is what makes the axis
 * free to rescale — which it must, since the range is not known until the
 * reader stops playing.
 *
 * Progressive enhancement, as with the matching game: the section carries
 * `hidden` in the markup and the first game to register un-hides it, so a
 * reader with no JavaScript never gets an empty frame.
 */
(function () {
  'use strict';

  var panel = document.getElementById('score-chart');
  var svg = document.getElementById('score-chart-svg');
  var titleEl = document.getElementById('score-chart-title');
  var readEl = document.getElementById('score-chart-read');
  if (!panel || !svg) return;

  var NS = 'http://www.w3.org/2000/svg';

  /* Deliberately small, and drawn at the width it is actually shown at, so one
   * unit here is one pixel there. Fixing the viewBox and letting the
   * stylesheet scale it would have been less code and it made the axis labels
   * illegible on a phone: 11px of text in a 600-wide frame squeezed into a
   * 300px column comes out under 6px on the glass.
   *
   * This started as the page's centrepiece and it is not one: readers have
   * said the plot confuses them, and a running score against trial number is
   * genuinely more than most people came here for. It is now a sidelight — a
   * small frame with its label beside it rather than a full-width figure with
   * a heading over it. Anyone who wants to read it still can, and anyone who
   * does not is no longer looking at 640 by 200 of it before they reach the
   * next question.
   *
   * Shorter again on a narrow box. The frame is drawn at true pixel size, so
   * on a phone every pixel here is one the reader has to scroll past. The
   * margins do not shrink with it — they hold the axis labels — so the
   * picture loses the slack rather than the text losing room. */
  var H_WIDE = 150, H_NARROW = 132, NARROW = 420;
  /* Narrower again, at the same height. The x axis is trials and they keep
   * coming, so width is the axis that was being spent on stretching a line
   * sideways rather than on showing anything more — the shape of the run is
   * as readable across 300 as across 400. Height is left alone: that one is
   * score, and squashing it is what makes a plot hard to read. */
  var H = H_WIDE, W_MAX = 340, W_MIN = 230;
  /* The margins are set by the labels the stylesheet draws in them: room on
   * the left for a negative, and enough below for a row of numbers with the
   * axis name under it. Trimmed with the frame — at 150 tall the old 46px
   * bottom margin was a third of the whole picture. */
  var PAD_L = 38, PAD_R = 12, PAD_T = 10, PAD_B = 34;
  var X0 = PAD_L, Y0 = PAD_T, Y1 = H - PAD_B;
  var MIN_TRIALS = 4, MIN_SPAN = 2;   // an empty axis still spans something
  var Y_TICKS = 3, X_LABELS = 5;      // fewer, so a small frame is not crowded

  /* key -> {label, points, bench}. bench is {step, label, mark, ends}: what one
   * completed game is worth to a benchmark player, what to call them, an
   * optional glyph, and the trial each of the reader's finished games ended on.
   *
   * A benchmark player only has a score at those moments. They earn a game's
   * worth per game, not a fraction of one per trial, so a line drawn across
   * every trial was claiming a standing for them on trials where they have
   * none — and worse, it climbed in steps that landed nowhere near the reader's
   * own. It is a short flat mark at step * k on the trial the reader's kth game
   * ended: where chance stood at the moment the reader stood there too. */
  var series = {};
  var active = null;
  var drawnBox = 0;                // the box width the frame was last drawn at

  function el(name, attrs) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) n.setAttribute(k, attrs[k]);
    return n;
  }

  /* A step of 1, 2, 5 or a power of ten of one of those. Anything else gives
   * an axis labelled 3, 6, 9, which is a correct division of the range and
   * still reads as though the numbers mean something they do not. */
  function niceStep(span, want) {
    var raw = (span || 1) / want;
    var pow = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10));
    var n = raw / pow;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * pow;
  }

  function draw() {
    var s = active && series[active];
    if (!s) return;
    var pts = s.points;

    if (titleEl) titleEl.textContent = s.label;
    // The stylesheet gives each game its own colour off this, so the frame
    // changing hands is visible before the title has been read.
    panel.setAttribute('data-game', active);

    var box = Math.round(svg.parentNode.clientWidth) || W_MAX;
    drawnBox = box;
    var W = Math.max(W_MIN, Math.min(W_MAX, box));
    var X1 = W - PAD_R;
    // Set before anything is placed: every y below is measured off Y1.
    H = box < NARROW ? H_NARROW : H_WIDE;
    Y1 = H - PAD_B;
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);

    /* The x axis is trials and they are whole numbers, so it runs 0..n. It
     * never runs shorter than four, or the first answer would arrive as a line
     * across the whole frame and the second would halve it. */
    var xMax = Math.max(pts.length - 1, MIN_TRIALS);

    var lo = 0, hi = 0, i;
    for (i = 0; i < pts.length; i++) {
      if (pts[i] < lo) lo = pts[i];
      if (pts[i] > hi) hi = pts[i];
    }
    /* Every benchmark mark is part of the picture, so the axis has to reach
     * them. Left out of this, a reader losing to the benchmark saw it vanish
     * off the top of the frame at the moment it mattered most. */
    var b = s.bench, ends = (b && b.ends) || [];
    for (i = 0; i < ends.length; i++) {
      var bv = b.step * (i + 1);
      if (bv < lo) lo = bv;
      if (bv > hi) hi = bv;
    }
    // Zero is always on the axis: a line that never crosses it still means
    // something different above it than below. And the axis never spans less
    // than two, so an unplayed game is a frame with room in it rather than a
    // rule with the origin sitting on it.
    if (hi - lo < MIN_SPAN) hi = lo + MIN_SPAN;
    // Scores are whole numbers, so the gridlines are too: left to itself the
    // step for a range of nothing came out at 0.5, and two lines half a point
    // apart both rounded to labels a point apart.
    var step = Math.max(1, Math.round(niceStep(hi - lo, Y_TICKS)));
    lo = Math.floor(lo / step) * step;
    hi = Math.ceil(hi / step) * step;
    if (hi === lo) hi = lo + step;

    function px(n) { return X0 + (X1 - X0) * (n / xMax); }
    function py(v) { return Y1 - (Y1 - Y0) * ((v - lo) / (hi - lo)); }

    svg.textContent = '';
    // Where the benchmark's name ended up, so the reader's own label can keep
    // out of it: {x1, x2, y}, or null until it has been drawn and measured.
    var benchBox = null;

    // Horizontal rules, one per labelled value, with zero picked out.
    for (var v = lo; v <= hi + 1e-9; v += step) {
      var y = py(v);
      svg.appendChild(el('line', {
        'class': v === 0 ? 'sc-zero' : 'sc-grid',
        x1: X0, y1: y, x2: X1, y2: y
      }));
      var lab = el('text', { 'class': 'sc-tick sc-tick-y', x: X0 - 8, y: y + 5 });
      lab.textContent = String(Math.round(v));
      svg.appendChild(lab);
    }

    // The two axes themselves, so the frame closes on the left and below.
    svg.appendChild(el('line', { 'class': 'sc-axis', x1: X0, y1: Y0, x2: X0, y2: Y1 }));
    svg.appendChild(el('line', { 'class': 'sc-axis', x1: X0, y1: Y1, x2: X1, y2: Y1 }));

    var xStep = Math.ceil(xMax / X_LABELS) || 1;
    for (i = 0; i <= xMax; i += xStep) {
      /* 15 below the axis, not 20. At the old full height there was room for
       * both this row and the axis name under it; at 132 the two were 8px
       * apart and "Trials" was printed through the tick that sat above it. */
      var xl = el('text', { 'class': 'sc-tick sc-tick-x', x: px(i), y: Y1 + 15 });
      xl.textContent = String(i);
      svg.appendChild(xl);
    }

    var xt = el('text', { 'class': 'sc-axis-name', x: (X0 + X1) / 2, y: H - 3 });
    xt.textContent = 'Trials';
    svg.appendChild(xt);
    var yt = el('text', {
      'class': 'sc-axis-name', x: 0, y: 0,
      transform: 'translate(16,' + ((Y0 + Y1) / 2) + ') rotate(-90)'
    });
    yt.textContent = 'Score';
    svg.appendChild(yt);

    /* The benchmark: one short flat mark per game the reader has finished, at
     * what chance would have been worth by then — half a point a solved
     * question in the trivia, 3.28 a completed board in the matching game. Each
     * is a step up on the last, so the row of them slopes across the frame at
     * the rate the reader has to beat, and the gaps between them are the trials
     * spent inside a game, where the benchmark has nothing to say.
     *
     * Drawn before the score line so the reader's own line is never the one
     * interrupted. */
    if (ends.length) {
      /* Wide enough to read as a level rather than a dot, and well short of the
       * gap between two trials — at 0.45 of it a run of questions answered
       * first time left the marks a pixel apart and closed the row back into
       * the line this used to be. */
      var half = Math.max(3, Math.min(8, (X1 - X0) / xMax * 0.35));
      var lastX = X0, lastY = Y1;
      for (i = 0; i < ends.length; i++) {
        var mx = px(ends[i]), my = py(b.step * (i + 1));
        // Trimmed at the frame rather than hung over it: the newest game is
        // often the last trial, and a level sticking out past the axis reads
        // as a line that has escaped rather than as one that ends there.
        svg.appendChild(el('line', {
          'class': 'sc-bench', y1: my, y2: my,
          x1: Math.max(X0, mx - half), x2: Math.min(X1, mx + half)
        }));
        lastX = mx; lastY = my;
      }
      /* The glyph is placed before the name is, because the name has to end
       * short of it. Both belong to the head of the slope and the glyph is the
       * one with nowhere else to go — a monkey shunted left lands on the game
       * before last, where the words can simply stop sooner. */
      var mkX = 0, mkY = 0, mkAt = 'start', mkLeft = X1;
      if (b.mark) {
        mkX = lastX + half + 3; mkY = lastY + 6;
        /* Up onto the mark rather than back along the row, once the slope has
         * reached the right-hand edge — which is where a long run always leaves
         * it, and on a phone is most of them. */
        if (mkX > X1 - 18) {
          mkX = Math.min(X1, lastX + half); mkY = lastY - 6; mkAt = 'end';
          mkLeft = mkX - 20;             // an emoji is about that wide at 18px
        }
      }

      /* Named once, trailing back from the newest mark. Set over the first one
       * instead — the low end of the slope, where the frame is emptiest — the
       * words ran straight through every mark that came after it. Behind the
       * head of the slope there is nothing but the trials the benchmark has
       * already passed. Below the mark when the slope has reached the top of
       * the frame and above would put the words outside it. */
      var labY = lastY - 8 < Y0 + 10 ? lastY + 16 : lastY - 8;
      var labX = Math.min(lastX - half - 5, mkLeft - 4), labAt = 'end';
      var room = labX - X0 - 2;
      // Too early in the run for anything to trail: back to the left edge,
      // where a first mark two trials in leaves no room behind it.
      if (room < 70) { labX = X0 + 6; labAt = 'start'; room = (X1 - X0) - 56; }
      var bl = el('text', {
        'class': 'sc-bench-label', x: labX, y: labY, 'text-anchor': labAt
      });
      bl.textContent = b.label;
      svg.appendChild(bl);
      /* Shrunk to fit rather than cut.
       *
       * The label is whatever the game calls its benchmark and the words are
       * not this file's to shorten, but the frame is now a third of the width
       * it was drawn for: "Chance with Elimination Benchmark" at full size
       * runs past the right-hand edge and straight under the running total.
       * So it is measured and scaled down until it fits, leaving room at the
       * end for that total. Down to 8px and no further — below that it stops
       * being readable, and an unreadable label is worse than a wrapped
       * layout. */
      try {
        var wide = bl.getComputedTextLength();
        if (wide > room) {
          /* Inline, not an attribute: the stylesheet sets a size for this
           * class, and in SVG a CSS declaration beats a presentation
           * attribute — set that way the shrink was silently ignored and the
           * label went on running under the total. The base is read from the
           * stylesheet rather than repeated here, so changing it there does
           * not quietly break the arithmetic. */
          var base = parseFloat(getComputedStyle(bl).fontSize) || 13.5;
          bl.style.fontSize = Math.max(8, base * (room / wide)) + 'px';
          wide = bl.getComputedTextLength();
        }
        benchBox = {
          x1: labAt === 'end' ? labX - wide : labX,
          x2: labAt === 'end' ? labX : labX + wide,
          y: labY
        };
      } catch (e) { }
      /* A glyph standing on the newest mark, if the game gave one. The trivia's
       * benchmark is what a reader scores by guessing, so it gets a monkey —
       * the label says blind and the picture says the rest. It sits at
       * the top of the slope because that is where the benchmark has got to,
       * and beside the mark rather than over it so it does not cover the level
       * it is standing on. Drawn as text rather than an image so there is no
       * file to fetch, nothing to licence, and it scales with the frame. */
      if (b.mark) {
        var bm = el('text', {
          'class': 'sc-bench-mark', x: mkX, y: mkY, 'text-anchor': mkAt
        });
        bm.textContent = b.mark;
        svg.appendChild(bm);
      }
    }

    // The line, then the points on top of it.
    if (pts.length > 1) {
      var d = [];
      for (i = 0; i < pts.length; i++) d.push(px(i) + ',' + py(pts[i]));
      svg.appendChild(el('polyline', { 'class': 'sc-line', points: d.join(' ') }));
    }

    /* The reader's own line, named.
     *
     * The benchmark beside it has carried a label since it was drawn, and an
     * unlabelled line next to a labelled one reads as though the labelled one
     * is the subject — which is backwards here. It goes over the middle of the
     * run rather than either end: the right end already has the running total
     * beside it. */
    if (pts.length > 2) {
      /* Start at the middle and walk right until the label is clear of the
       * benchmark's. Put at the midpoint flat, it landed inside "A blindfolded
       * guesser" and the frame read "A blindfolded Youesser". Never past the
       * second-to-last point, because the running total is already sitting at
       * the end of the line.
       *
       * Both directions are checked, not just across. The benchmark's name used
       * to sit at whatever height the benchmark did and the two labels were
       * kept apart by column alone, which was safe and far too cautious: with
       * the name now trailing the head of the slope, a horizontal test would
       * push "You" to the end of the run to avoid words half the frame below
       * it. */
      var clash = function (at) {
        if (!benchBox) return false;
        var x = px(at), y = py(pts[at]);
        return x + 20 > benchBox.x1 && x - 20 < benchBox.x2 &&
               Math.abs(y - benchBox.y) < 18;
      };
      var mid = Math.floor((pts.length - 1) / 2);
      while (mid < pts.length - 2 && clash(mid)) mid++;
      var midY = py(pts[mid]);
      /* Above the line normally. Below it if the walk ran out of room and the
       * benchmark's label is still under this one — a long benchmark label can
       * span the whole of a 250px frame, and there is then nowhere to the right
       * to go. Below also when the line is near the top of the frame and above
       * would put the word outside the picture. */
      var crowded = clash(mid);
      var above = midY - 8 >= Y0 + 4 && !crowded;
      var you = el('text', {
        'class': 'sc-you', x: px(mid), 'text-anchor': 'middle',
        y: above ? midY - 8 : midY + 16
      });
      you.textContent = 'You';
      svg.appendChild(you);
    }

    for (i = 0; i < pts.length; i++) {
      /* Green for a trial that gained and maroon for one that lost, which is
       * what those two colours already mean on this page. The origin is
       * neither, since nothing has been answered yet. */
      var tone = i === 0 ? 'sc-dot' :
                 pts[i] > pts[i - 1] ? 'sc-dot sc-up' : 'sc-dot sc-down';
      svg.appendChild(el('circle', {
        'class': tone + (i === pts.length - 1 ? ' sc-last' : ''),
        cx: px(i), cy: py(pts[i]), r: i === pts.length - 1 ? 5 : 3.5
      }));
    }

    // The latest total beside the point it belongs to, flipped to the left of
    // it once the line has reached the right-hand edge of the frame.
    var last = pts.length - 1;
    if (last > 0) {
      var lx = px(last), ly = py(pts[last]), left = lx > X1 - 40;
      // Above the point, or below it when the point is at the top of the frame
      // and above would put the number outside the picture — which is where a
      // run of right answers always ends up.
      var ly2 = ly - 9 < Y0 + 4 ? ly + 18 : ly - 9;
      var val = el('text', {
        'class': 'sc-value', x: lx + (left ? -10 : 10),
        y: ly2, 'text-anchor': left ? 'end' : 'start'
      });
      val.textContent = (pts[last] > 0 ? '+' : '') + pts[last];
      svg.appendChild(val);
    }

    var read = s.label + ': ' + pts[last] + ' after ' + last +
               (last === 1 ? ' trial' : ' trials');
    svg.setAttribute('aria-label', read);
    if (readEl) readEl.textContent = read;
  }

  /* Measured rather than scaled, so a box that changes width needs the frame
   * drawn again — a phone turned sideways otherwise leaves the old picture in
   * the corner of twice the space.
   *
   * Watching the box rather than the window, because the two are not the same
   * event: the panel is un-hidden after the first draw, and a window that
   * never resized still gave the chart a width it had not been drawn at. The
   * width is compared before redrawing, so the observer cannot chase its own
   * output round in a loop. */
  function refit() {
    if (Math.round(svg.parentNode.clientWidth) !== drawnBox) draw();
  }
  if (window.ResizeObserver) {
    new ResizeObserver(refit).observe(svg.parentNode);
  } else {
    var resized = null;
    window.addEventListener('resize', function () {
      if (resized) clearTimeout(resized);
      resized = setTimeout(refit, 150);
    });
  }

  /* The three things a game does to the chart: say it exists, hand it a new
   * total, and claim the frame when the reader turns to it. */
  window.KhaanaScoreLine = {
    /* bench is optional: {step, label, mark}. step is what one completed game
       adds to the benchmark, label is what to write above the first of its
       marks, and mark is an optional glyph to stand on the newest one. */
    track: function (key, label, bench) {
      if (!series[key]) series[key] = { label: label, points: [0], bench: null };
      if (bench) series[key].bench = { step: bench.step, label: bench.label,
                                       mark: bench.mark || null, ends: [] };
      if (!active) active = key;
      panel.hidden = false;
      draw();
    },
    point: function (key, total) {
      var s = series[key];
      if (!s) return;
      s.points.push(total);
      active = key;                // scoring in a game is the loudest claim on it
      draw();
    },
    /* One more completed game against the benchmark: a question solved in the
       trivia, a board finished in the matching game. Counted separately from
       the points, because a trial and a game are not the same thing — a trivia
       question can take four trials to solve and is still one game.

       The trial it landed on is what gets kept, not just the count: the
       benchmark is drawn where the reader's games ended, so the chart needs to
       know where those were. Both games score the trial before they report the
       game, so the newest point is the one the game ended on. */
    games: function (key, n) {
      var s = series[key];
      if (!s || !s.bench || s.bench.ends.length === n) return;
      var ends = s.bench.ends, at = s.points.length - 1;
      while (ends.length < n) ends.push(at);
      if (ends.length > n) ends.length = n;      // a game count that went back
      draw();
    },
    focus: function (key) {
      if (!series[key] || active === key) return;
      active = key;
      draw();
    }
  };
})();
