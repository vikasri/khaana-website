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
  /* Narrower than it began, at the same height. The x axis is trials and they
   * keep coming, so width was the axis being spent on stretching a line
   * sideways rather than on showing anything more — the shape of the run is
   * as readable across 300 as across 400. Height is left alone: that one is
   * score, and squashing it is what makes a plot hard to read.
   *
   * Some of that width bought back since, because the frame now carries a line
   * of words at each end — the benchmark's key, the reader's total under "You"
   * — and the key is given a gutter of its own to stand in rather than the
   * plot. That gutter comes out of the trials, so the frame has
   * to be wide enough to give one up. This is a ceiling, not a size: the frame
   * is still drawn at whatever its box allows, so a phone is unaffected.
   *
   * It has to match .score-chart-plot's max-width in the stylesheet, and that
   * one is the one that binds — the box is measured, so a cap raised here alone
   * changes nothing. */
  var H = H_WIDE, W_MAX = 500, W_MIN = 230;
  /* The margins are set by the labels the stylesheet draws in them: room on
   * the left for a negative, and enough below for a row of numbers with the
   * axis name under it. Trimmed with the frame — at 150 tall the old 46px
   * bottom margin was a third of the whole picture. */
  var PAD_L = 38, PAD_R = 12, PAD_T = 10, PAD_B = 34;
  var X0 = PAD_L, Y0 = PAD_T, Y1 = H - PAD_B;
  var MIN_TRIALS = 4, MIN_SPAN = 2;   // an empty axis still spans something
  var Y_TICKS = 3, X_LABELS = 5;      // fewer, so a small frame is not crowded
  /* The most of the frame's width the benchmark's name may take as a gutter to
   * stand in. Past this the words shrink instead: the plot is the point of the
   * picture, and a label is not worth half of it. */
  var GUTTER_MAX = 0.42;
  /* And the width the plot keeps whatever the words want. Below this there is
   * no gutter at all and the name goes back inside the picture — a phone has
   * no width to give away. */
  var MIN_PLOT = 210;

  /* key -> {label, points, bench}. bench is {step, label, ends}: what one
   * completed game is worth to a benchmark player, what to call them, and the
   * trial each of the reader's finished games ended on.
   *
   * A benchmark player only has a score at those moments. They earn a game's
   * worth per game, not a fraction of one per trial, so a line drawn across
   * every trial was claiming a standing for them on trials where they have
   * none. What is drawn instead is a point at step * k on the trial the
   * reader's kth game ended — where chance stood at the moment the reader stood
   * there too — with a thin dotted line through them. The line is the
   * benchmark; the points only say where it was pinned. */
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

    svg.textContent = '';

    /* The margin the plot leaves itself on the right, and why the benchmark's
     * name is built before anything is placed.
     *
     * The name belongs beside the newest mark, on its right — that is the end
     * the benchmark has got to. But the newest mark is usually the newest
     * trial, which is the right-hand end of the axis, so there was nothing to
     * its right to write in and the words had to be slid back along the slope
     * to fit. So the plot stops short: the trials are drawn across everything
     * up to XD and the strip from there to the frame's edge is kept clear for
     * the name. The gutter is sized to the words it has to hold, which means
     * measuring them first — hence the text nodes here, moved to the end of the
     * frame afterwards so they are drawn over the picture rather than under it.
     *
     * Only where the frame can spare it. The gutter is capped both as a share
     * of the width and by what the plot must keep, and the name is shrunk to
     * whatever the cap leaves — but never past 8px, below which it stops being
     * readable. On a phone that floor is reached with the words still wider
     * than any gutter worth having: a 250px frame gave up two thirds of itself
     * and left a plot 98 across. So there the gutter is refused outright and
     * the name goes back inside the picture, which is the layout below.
     *
     * Held even before the first game is finished, when there is no mark and no
     * name to draw yet. The alternative is an axis that silently rescales under
     * the reader the moment they solve something. */
    var bl = null, labW = 0, gutter = 0;
    /* lead is the clear space between the plot's edge and the key. Wider than
     * it looks like it needs to be: at 7 the sample sat close enough to the end
     * of the real line, and near enough its height, to read as the line simply
     * carrying on into the margin. */
    var gap = 4, lead = 18, SWATCH = 16;
    if (b) {
      bl = el('text', { 'class': 'sc-bench-label', x: 0, y: 0 });
      bl.textContent = b.label;
      svg.appendChild(bl);
      try {
        labW = bl.getComputedTextLength();
        var fixed = lead + SWATCH + gap;
        var cap = Math.min((X1 - X0) * GUTTER_MAX, (X1 - X0) - MIN_PLOT);
        if (cap - fixed >= 40) {
          if (labW > cap - fixed) {
            /* Set inline, not as an attribute: the stylesheet gives this class
             * a size, and in SVG a CSS declaration beats a presentation
             * attribute, so set that way the shrink was silently ignored. The
             * base is read back from the stylesheet rather than repeated. */
            var base = parseFloat(getComputedStyle(bl).fontSize) || 13.5;
            bl.style.fontSize = Math.max(8, base * ((cap - fixed) / labW)) + 'px';
            labW = bl.getComputedTextLength();
          }
          /* Judged on what the plot is left with, not on whether the words came
           * in under the cap. A string's advance width does not scale to the
           * pixel with its font size — shrunk to fit 151, "A Guesser who
           * Remembers" measured back 151.6 — and a strict test against the cap
           * read that as "does not fit" and threw away a gutter the frame had
           * ample room for. The cap is what the words are shrunk towards; the
           * plot's minimum is the thing that actually has to hold. */
          gutter = fixed + labW;
          if ((X1 - X0) - gutter < MIN_PLOT) gutter = 0;
        }
        if (!gutter) { bl.style.fontSize = ''; labW = bl.getComputedTextLength(); }
      } catch (e) { gutter = 0; }
    }
    var XD = X1 - gutter;

    function px(n) { return X0 + (XD - X0) * (n / xMax); }
    function py(v) { return Y1 - (Y1 - Y0) * ((v - lo) / (hi - lo)); }

    /* The reader's own end of the line: the running total against the point it
     * belongs to, with "You" directly over it.
     *
     * Both to the left of the point and both right-aligned, so the two share an
     * edge and read as one block naming the line rather than as a stray word
     * somewhere along it. Left rather than right because a run of any length
     * puts that last point at the end of the axis.
     *
     * Above the point normally, below it when the line has climbed far enough
     * that two lines of text above would leave the frame — which is where a
     * good run always ends up. "You" stays over the total either way: it is the
     * label and the number is what it labels. */
    var lastI = pts.length - 1;
    var youBox = null;
    if (lastI > 0) {
      var ylx = px(lastI), yly = py(pts[lastI]);
      var over = yly - 26 >= Y0 + 4;
      youBox = {
        x: ylx - 10,                   // the shared right edge of both lines
        valY: over ? yly - 8 : yly + 30,
        youY: over ? yly - 24 : yly + 14
      };
    }

    /* Horizontal rules, one per labelled value, with zero picked out. They stop
     * at XD with the plot: a rule carried on into the gutter would make that
     * strip read as part of the picture, which is the one thing it is not. */
    for (var v = lo; v <= hi + 1e-9; v += step) {
      var y = py(v);
      svg.appendChild(el('line', {
        'class': v === 0 ? 'sc-zero' : 'sc-grid',
        x1: X0, y1: y, x2: XD, y2: y
      }));
      var lab = el('text', { 'class': 'sc-tick sc-tick-y', x: X0 - 8, y: y + 5 });
      lab.textContent = String(Math.round(v));
      svg.appendChild(lab);
    }

    // The two axes themselves, so the frame closes on the left and below.
    svg.appendChild(el('line', { 'class': 'sc-axis', x1: X0, y1: Y0, x2: X0, y2: Y1 }));
    svg.appendChild(el('line', { 'class': 'sc-axis', x1: X0, y1: Y1, x2: XD, y2: Y1 }));

    var xStep = Math.ceil(xMax / X_LABELS) || 1;
    for (i = 0; i <= xMax; i += xStep) {
      /* 15 below the axis, not 20. At the old full height there was room for
       * both this row and the axis name under it; at 132 the two were 8px
       * apart and "Trials" was printed through the tick that sat above it. */
      var xl = el('text', { 'class': 'sc-tick sc-tick-x', x: px(i), y: Y1 + 15 });
      xl.textContent = String(i);
      svg.appendChild(xl);
    }

    var xt = el('text', { 'class': 'sc-axis-name', x: (X0 + XD) / 2, y: H - 3 });
    xt.textContent = 'Trials';
    svg.appendChild(xt);
    var yt = el('text', {
      'class': 'sc-axis-name', x: 0, y: 0,
      transform: 'translate(16,' + ((Y0 + Y1) / 2) + ') rotate(-90)'
    });
    yt.textContent = 'Score';
    svg.appendChild(yt);

    /* The benchmark: a small point per game the reader has finished, at what
     * chance would have been worth by then — half a point a solved question in
     * the trivia, 3.28 a completed board in the matching game — joined by a
     * thin line.
     *
     * Points, because those are the only moments the benchmark has a score at
     * all: it earns a game's worth per game, not a fraction of one per trial.
     * A line across every trial claimed a standing for it on trials where it
     * has none, and a row of flat marks with nothing between them made the
     * reader work out the slope for themselves. Joined up, the thing the frame
     * is actually about — the rate the reader has to beat — is a line they can
     * see, and the points still say where it was really measured.
     *
     * From the origin, because nought games is nought score, and starting there
     * puts the benchmark's line and the reader's on the same footing.
     *
     * Drawn before the score line so the reader's own line is never the one
     * interrupted. */
    if (ends.length) {
      var lastX = X0, lastY = Y1;
      var bpts = [px(0) + ',' + py(0)];
      for (i = 0; i < ends.length; i++) {
        var mx = px(ends[i]), my = py(b.step * (i + 1));
        bpts.push(mx + ',' + my);
        lastX = mx; lastY = my;
      }
      svg.appendChild(el('polyline', {
        'class': 'sc-bench', points: bpts.join(' ')
      }));
      /* Where the line was actually measured, and no more than that. The dotted
       * line is the benchmark; these say which trials it was pinned to. Small
       * enough to be read as marks on it rather than as a second set of scores
       * beside the reader's own — the origin gets none at all, being a shared
       * starting point rather than a game. */
      for (i = 0; i < ends.length; i++) {
        svg.appendChild(el('circle', {
          'class': 'sc-bench-dot', r: 1.5,
          cx: px(ends[i]), cy: py(b.step * (i + 1))
        }));
      }
      /* The benchmark keyed out in the gutter, level with its newest point and
       * to the right of it: a sample of its own line with a point on it, then
       * the words.
       *
       * A key rather than a caption, because the words on their own left the
       * reader to work out which of the two lines they belonged to. The sample
       * is drawn from the same classes as the real thing, so it cannot drift
       * out of step with what is in the plot.
       *
       * Right of the point and nowhere else, which is what the gutter was
       * measured out for. It also settles the frame's other end for nothing:
       * the reader's total is inside the plot and this is outside it, so the
       * two blocks cannot land on each other however close the two lines run.
       *
       * Where the frame was too narrow to spare a gutter the row comes back
       * inside the picture, and both of those conveniences go with it: it
       * slides left along the slope to fit, and it has to stop short of the
       * reader's total when the two lines are running at the same height.
       * Sliding left is the safe direction — the slope climbs, so everything
       * behind the newest point is below the line the row sits on. */
      var labY = Math.max(Y0 + 12, Math.min(Y1 - 2, lastY + 5));
      var blockX;
      if (gutter) {
        blockX = Math.max(lastX + 6, XD + lead);
      } else {
        /* Measured off what the two blocks actually cover rather than a rough
         * band around them. A loose test cost real legibility: the words were
         * pushed clear of a total sitting four pixels below them and shrank to
         * 8px to fit the room that left. */
        var limit = X1;
        if (youBox && labY + 4 > youBox.youY - 14 && labY - 13 < youBox.valY + 4) {
          limit = Math.max(X0 + 90, youBox.x - 46 - 8);
        }
        var fixedW = SWATCH + gap;
        var blockW = fixedW + labW;
        if (blockW > limit - X0 - 4) {
          try {
            var narrow = parseFloat(getComputedStyle(bl).fontSize) || 13.5;
            var fits = (limit - X0 - 4) - fixedW;
            bl.style.fontSize = Math.max(8, narrow * (fits / labW)) + 'px';
            labW = bl.getComputedTextLength();
            blockW = fixedW + labW;
          } catch (e) { }
        }
        blockX = Math.max(X0 + 2, Math.min(lastX + 6, limit - blockW));
      }

      // The sample: a short run of the line with one of its points on it,
      // sitting on the words' own baseline less a little, so the row reads as
      // one line rather than as a rule above some text.
      var swY = labY - 4;
      svg.appendChild(el('polyline', {
        'class': 'sc-bench',
        points: blockX + ',' + swY + ' ' + (blockX + SWATCH) + ',' + swY
      }));
      svg.appendChild(el('circle', {
        'class': 'sc-bench-dot', r: 1.5, cx: blockX + SWATCH / 2, cy: swY
      }));
      bl.setAttribute('x', blockX + SWATCH + gap);
      bl.setAttribute('y', labY);
      // Moved to the end so it sits over the picture: it was built before it,
      // to size the gutter it now stands in.
      svg.appendChild(bl);
    } else if (bl) {
      // The gutter is held from the first draw so the axis does not rescale
      // under the reader the moment they finish something, but until then there
      // is no line to key and the words would be labelling nothing.
      svg.removeChild(bl);
    }

    // The line, then the points on top of it.
    if (pts.length > 1) {
      var d = [];
      for (i = 0; i < pts.length; i++) d.push(px(i) + ',' + py(pts[i]));
      svg.appendChild(el('polyline', { 'class': 'sc-line', points: d.join(' ') }));
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

    // The reader's block, laid out at the top of the draw and set down here so
    // it goes over the line rather than under it.
    var last = lastI;
    if (youBox) {
      var you = el('text', {
        'class': 'sc-you', x: youBox.x, y: youBox.youY, 'text-anchor': 'end'
      });
      you.textContent = 'You';
      svg.appendChild(you);
      var val = el('text', {
        'class': 'sc-value', x: youBox.x, y: youBox.valY, 'text-anchor': 'end'
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
    /* bench is optional: {step, label}. step is what one completed game adds
       to the benchmark and label is what to call it in the key. */
    track: function (key, label, bench) {
      if (!series[key]) series[key] = { label: label, points: [0], bench: null };
      if (bench) series[key].bench = { step: bench.step, label: bench.label,
                                       ends: [] };
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
