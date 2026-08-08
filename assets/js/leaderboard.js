/* Fun facts: the shared boards under the chart.
 *
 * What a score is
 * ---------------
 * The best run of consecutive games, not the session total. A game is one
 * question solved in the trivia and one board solved in the matching game —
 * the same distinction score-chart.js draws between a game and a trial, and
 * for the same reason: a question can take four presses and is still one
 * question. How many presses it took is already priced in, because each wrong
 * one costs a point.
 *
 * So the window slides. Every solved game pushes its own net onto a queue of
 * ten (five for the matching game), the queue is summed, and the highest that
 * sum ever reaches is the score. Nothing stops, nothing resets, no round is
 * declared over. A block of ten with a scoring beat at the end would have put
 * back the "come back tomorrow" pause the trivia was rewritten to remove.
 *
 * Ties break on the clock: same score, quicker wins. That is not decoration.
 * Ten questions answered clean is twenty and there is no twenty-one, so
 * without a second key a perfect run could never be beaten and the board would
 * close the first time somebody had a good afternoon.
 *
 * Where it lives
 * --------------
 * On the server now, not in this browser. Everyone playing anywhere is on the
 * same board, which is the whole point of it and is why the page has to ask
 * for it rather than remember it. The API is a small Cloudflare Worker in
 * front of a D1 table; the site itself is still static files on GitHub Pages
 * and has not moved.
 *
 * Everything here is written so the games do not care whether that works. No
 * network, slow network, Worker down: the quiz and the matching game play
 * exactly as they do now and the board simply is not there. Nothing waits on a
 * fetch and nothing is blocked by one failing.
 *
 * Your own best still comes from this session and is shown whether or not it
 * is good enough for the board. On a board of two that matters more, not less:
 * almost nobody is on it, and without their own number a player would have
 * nothing to read but two strangers' scores.
 */
(function () {
  'use strict';

  var API = 'https://khaana-board.vikasri.workers.dev';
  /* Three, and it must match TOP_N in the Worker. The last row on screen is
   * the bar — it is what `beats` compares a finished run against — so a page
   * expecting more rows than the server sends would read a full board as one
   * with a free slot and prompt people who had not earned it. Every run is
   * still stored server-side; this is the display and the threshold, not a
   * limit on what is kept. */
  var KEEP = 3;
  var MAX_NAME = 13;               // and the maxlength in tools/build-trivia.py

  /* --- names ---------------------------------------------------------------
   *
   * The server runs this same check and its answer is the one that counts:
   * anything can post to a public endpoint, so a rule that only exists in the
   * browser is not a rule. This copy is here to refuse a name instantly rather
   * than after a round trip, and the two lists are kept identical on purpose —
   * if you edit one, edit worker/src/index.js too.
   *
   * Three passes, each narrower than the last, because the wide one is what
   * generates false positives. The flattened name is scanned for the words in
   * BLOCK; single words of the name are matched whole against LOOSE, which
   * holds everything short or ambiguous enough that scanning for it inside a
   * longer name would catch real ones — "ass" inside Assam, "gand" inside
   * Gandhi, "tit" inside Titli, "nazi" inside Nazia. Then the same whole-word
   * match again with repeated letters collapsed, which is what catches a
   * stretched-out spelling without collapsing legitimate names into each
   * other.
   *
   * ALLOW is the short list of real names that the scan would otherwise take:
   * Shital and Sheetal are names, and the goddess Shitala is a name, and all
   * three contain a word in BLOCK. Add to it when a real name is refused.
   */
  var LEET = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b',
    '@': 'a', '$': 's', '!': 'i', '+': 't', '|': 'i'
  };

  var BLOCK = [
    'fuck', 'phuck', 'shit', 'cunt', 'bitch', 'bastard', 'asshole', 'arsehole',
    'motherfuck', 'pussy', 'penis', 'vagina', 'whore', 'slut', 'wank', 'wanker',
    'bollock', 'bugger', 'twat', 'prick', 'dickhead', 'blowjob', 'handjob',
    'cocksuck', 'dumbass', 'jackass', 'nigger', 'nigga', 'faggot', 'fagot',
    'retard', 'spastic', 'hitler', 'porn', 'chutiya', 'chutiye', 'madarchod',
    'madarchood', 'behenchod', 'bhenchod', 'bhosdi', 'bhosda', 'bhosadi',
    'gaand', 'gandu', 'harami', 'kutiya', 'chinal'
  ];

  var LOOSE = [
    'ass', 'arse', 'anal', 'sex', 'tit', 'tits', 'cock', 'dick', 'cum', 'fag',
    'homo', 'shag', 'rape', 'rapist', 'randi', 'lund', 'gand', 'chut', 'nazi',
    'chamar', 'bhangi', 'wtf', 'stfu', 'fck', 'fuk', 'fuq', 'boob', 'boobs',
    'turd', 'crap', 'piss', 'hoe', 'slag', 'minge', 'knob'
  ];

  var ALLOW = ['shital', 'sheetal', 'shitala', 'scunthorpe'];

  function letters(s) {
    var out = '';
    for (var i = 0; i < s.length; i++) {
      var c = s.charAt(i).toLowerCase();
      if (LEET[c]) c = LEET[c];
      if (c >= 'a' && c <= 'z') out += c;
    }
    return out;
  }

  function squash(s) { return s.replace(/(.)\1+/g, '$1'); }

  function words(name) {
    var parts = name.split(/[^0-9A-Za-z@$!+|]+/);
    var out = [];
    for (var i = 0; i < parts.length; i++) {
      var w = letters(parts[i]);
      if (w) out.push(w);
    }
    return out;
  }

  function inList(list, w) {
    for (var i = 0; i < list.length; i++) if (list[i] === w) return true;
    return false;
  }

  function decent(name) {
    var w = words(name);
    var i, j;

    // The wide scan runs on the name with any allow-listed word taken out, so
    // "Shital" is nothing to scan and "Shital fuck" is still caught.
    var flat = '';
    for (i = 0; i < w.length; i++) if (!inList(ALLOW, w[i])) flat += w[i];
    for (i = 0; i < BLOCK.length; i++) {
      if (flat.indexOf(BLOCK[i]) >= 0) return false;
    }

    for (i = 0; i < w.length; i++) {
      if (inList(ALLOW, w[i])) continue;
      var tight = squash(w[i]);
      for (j = 0; j < LOOSE.length; j++) {
        if (w[i] === LOOSE[j] || tight === squash(LOOSE[j])) return false;
      }
      for (j = 0; j < BLOCK.length; j++) {
        if (tight === squash(BLOCK[j])) return false;
      }
    }
    return true;
  }

  /* --- comparing runs ------------------------------------------------------ */

  /* Score first, then the clock, and strictly better both ways — equal on both
   * is not better, so an incumbent is never displaced by being matched. */
  function better(run, than) {
    if (!than) return true;
    if (run.s !== than.s) return run.s > than.s;
    return run.t < than.t;
  }

  /* Whole seconds under a minute, m:ss over it. Tenths would suggest the clock
   * is doing more than breaking ties, and it is not. */
  function clock(ms) {
    var s = Math.round(ms / 1000);
    if (s < 60) return s + 's';
    var m = Math.floor(s / 60);
    s -= m * 60;
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  /* --- one board ----------------------------------------------------------- */

  var boards = {};

  function make(key, cfg) {
    var root = document.getElementById(cfg.root);
    if (!root) return null;
    var b = {
      key: key,
      span: cfg.span,
      name: cfg.name,
      root: root,
      rowsEl: root.querySelector('.board-rows'),
      youEl: root.querySelector('.board-you'),
      rows: [],                    // the board as the server last gave it
      got: false,                  // whether that has ever arrived
      runs: [],                    // the last `span` games, newest last
      best: null,                  // best window this session, {s, t}
      mine: null,                  // the name submitted this session
      asked: false,                // the name has been asked for, or waived
      sending: false
    };
    boards[key] = b;
    paint(b);
    pull(b);
    return b;
  }

  /* --- talking to the board ------------------------------------------------
   *
   * Every call is wrapped so a failure is a board that does not appear rather
   * than a game that does not work. There is no retry loop and no spinner: the
   * reader came here to answer questions about samosas, and a page that nags
   * about its own network is worse than one that quietly has no board.
   */
  function pull(b) {
    if (!window.fetch) return;
    fetch(API + '/top?game=' + encodeURIComponent(b.key), { mode: 'cors' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !data.rows) return;
        b.rows = clean(data.rows);
        b.got = true;
        paint(b);
      })
      .catch(function () { /* no board is survivable; the games are not */ });
  }

  /* Nothing off the network is trusted into the DOM unchecked, even from our
   * own Worker: a bad row should cost a row, not the page. */
  function clean(rows) {
    var out = [];
    for (var i = 0; i < rows.length && out.length < KEEP; i++) {
      var e = rows[i];
      if (!e || typeof e.n !== 'string') continue;
      if (typeof e.s !== 'number' || !isFinite(e.s)) continue;
      if (typeof e.t !== 'number' || !isFinite(e.t) || e.t < 0) continue;
      out.push({ n: e.n.slice(0, MAX_NAME), s: Math.round(e.s), t: Math.round(e.t) });
    }
    return out;
  }

  /* One request at a time, and the last word wins.
   *
   * A sliding window improves in steps: once the good games start landing,
   * every one of them beats the window before it, so ten in a row can each ask
   * to be sent while the first request is still in the air. Dropping those was
   * the obvious guard and the wrong one — it published the first improvement
   * and threw away the nine better ones after it, so a run finishing at 33s
   * went up as 46s.
   *
   * So a request arriving mid-flight is remembered rather than dropped, and
   * fires again when the line is clear, reading b.best as it is by then. The
   * server keeps the best run per name, so an overtaken one landing late
   * cannot demote anybody.
   */
  function send(b, name) {
    if (!window.fetch || !b.best) return;
    b.mine = name;
    if (b.sending) { b.pending = true; return; }
    b.sending = true;
    b.pending = false;

    var done = function (data) {
      b.sending = false;
      if (data && data.rows) {
        b.rows = clean(data.rows);
        b.got = true;
        paint(b);
      }
      if (b.pending) send(b, b.mine);        // something better arrived meanwhile
    };

    fetch(API + '/score', {
      method: 'POST',
      mode: 'cors',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ game: b.key, name: name, score: b.best.s, ms: b.best.t })
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(done)
      .catch(function () { done(null); });
  }

  /* The bar to clear: the last row on a full board, and nothing at all while
   * the board has room. An empty slot takes any run, which is what seeds a new
   * season — the first ten runs are on it whatever they scored, and the
   * eleventh is the first that has to earn it.
   *
   * A board that has not arrived yet has no bar, so nobody is prompted against
   * a standard that might not be real. */
  function beats(b, run) {
    if (!b.got) return false;
    return b.rows.length < KEEP || better(run, b.rows[KEEP - 1]);
  }

  /* --- drawing ------------------------------------------------------------- */

  /* The player's own best, once they have a full run behind them.
   *
   * Shown whether or not it is good enough for the board, and that is the
   * point: a window of ten only exists after the tenth game, so before it
   * there is nothing to say, and after it a player who is nowhere near the
   * last row still gets to watch their own number move. Without this a shared
   * board is a wall to everyone who is not on it. */
  function paintYou(b) {
    if (!b.youEl) return;
    b.youEl.hidden = b.best === null;
    if (b.best === null) return;
    b.youEl.textContent = '';
    cells(b.youEl, '', 'You', b.best);
  }

  /* One row's four columns: place, who, how long, how much. */
  function cells(row, rank, who, run) {
    var a = document.createElement('span');
    a.className = 'board-rank';
    a.textContent = rank;
    var b2 = document.createElement('span');
    b2.className = 'board-who';
    b2.textContent = who;
    var c = document.createElement('span');
    c.className = 'board-time';
    c.textContent = clock(run.t);
    var d = document.createElement('span');
    d.className = 'board-score';
    d.textContent = run.s;
    row.appendChild(a);
    row.appendChild(b2);
    row.appendChild(c);
    row.appendChild(d);
  }

  /* The heading and the box it titles, hidden and shown together. Open while
   * either half is, so the frame arrives with the first board rather than
   * sitting empty beside a game nobody has played yet — and so the word
   * "Leaderboard" is never left standing over nothing. */
  function paintPanel() {
    var wrap = document.getElementById('fun-boards-wrap');
    if (!wrap) return;
    var open = false;
    for (var k in boards) {
      if (boards.hasOwnProperty(k) && !boards[k].root.hidden) open = true;
    }
    wrap.hidden = !open;
  }

  function paint(b) {
    b.root.hidden = !(b.rows.length > 0 || b.best !== null);
    paintPanel();
    paintYou(b);
    if (!b.rowsEl) return;
    b.rowsEl.textContent = '';
    b.rows.forEach(function (e, i) {
      var li = document.createElement('li');
      li.className = 'board-row';
      // Their own row, if they have named one this session. Names are not
      // accounts, so this is "the name you just used" and nothing stronger.
      if (b.mine && e.n === b.mine) li.setAttribute('data-mine', '1');
      cells(li, (i + 1) + '.', e.n, e);
      b.rowsEl.appendChild(li);
    });
  }

  /* --- the prompt ----------------------------------------------------------
   *
   * One dialog, shared. Getting on the board is the one thing on this page
   * worth interrupting for and it used to be a line of small print under a
   * panel nobody was looking at, so most people would have earned a place and
   * never known. It fires at most once a sitting, per game, and only to
   * somebody who has just beaten the bottom of a board that actually arrived.
   *
   * The form lives inside the dialog. A browser with no showModal gets it
   * moved back into the board it belongs to and shown there, which is where it
   * used to be — worse, but not nothing.
   */
  var dlg = document.getElementById('board-prompt');
  var joinEl = document.getElementById('board-join');
  var nameEl = document.getElementById('board-name');
  var errEl = document.getElementById('board-error');
  var cheerEl = document.getElementById('board-prompt-cheer');
  var whatEl = document.getElementById('board-prompt-what');
  var asking = null;               // the board being asked about, while open
  var modal = !!(dlg && dlg.showModal);

  function fail(why) {
    if (!errEl) return;
    errEl.textContent = why;
    errEl.hidden = false;
    nameEl.focus();
    nameEl.select();
  }

  function shut() {
    if (modal && dlg.open) dlg.close();
    else if (joinEl) joinEl.hidden = true;
    asking = null;
  }

  if (joinEl) {
    joinEl.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!asking) return;
      var raw = (nameEl.value || '').replace(/\s+/g, ' ').trim().slice(0, MAX_NAME);
      if (!raw || !letters(raw)) return fail('Enter a name.');
      if (!decent(raw)) return fail('Pick another name.');
      var b = asking;
      errEl.hidden = true;
      nameEl.value = '';
      shut();
      send(b, raw);
    });
    var skip = joinEl.querySelector('.board-skip');
    if (skip) skip.addEventListener('click', shut);
  }
  // Esc, or the backdrop: taken as "not now". `asked` is already set, so it
  // does not come back this session however it was closed.
  if (dlg) {
    dlg.addEventListener('close', function () { asking = null; });
    dlg.addEventListener('click', function (e) {
      if (e.target === dlg) shut();          // the backdrop, not the card
    });
  }

  /* Top of the board reads differently from merely on it, and the difference
   * is worth a word: one is a record and the other is a place in a list. */
  function cheerFor(b) {
    var top = !b.rows.length || better(b.best, b.rows[0]);
    return top ? '🏆 Top of the board!' : '🎉 You are on the board!';
  }

  function ask(b) {
    b.asked = true;
    paint(b);
    if (!joinEl) return;
    if (cheerEl) cheerEl.textContent = cheerFor(b);
    if (whatEl) {
      whatEl.textContent = b.name + ' — ' + b.best.s + ' in ' + clock(b.best.t);
    }
    if (errEl) errEl.hidden = true;
    if (nameEl) nameEl.value = '';
    asking = b;
    if (modal) {
      dlg.setAttribute('data-game', b.key);
      dlg.showModal();
      /* Focused after the burst rather than with it. The form is held back by
       * a CSS delay so the fireworks land first, and pulling focus into
       * something still fading in scrolls some browsers to it mid-animation. */
      setTimeout(function () { if (dlg.open && nameEl) nameEl.focus(); }, 700);
    } else {
      b.root.appendChild(joinEl);            // no dialog: back under the board
      joinEl.hidden = false;
      paint(b);
    }
  }

  /* --- the sliding window -------------------------------------------------- */

  function record(b, net, ms) {
    b.runs.push({ net: net, ms: (typeof ms === 'number' && ms >= 0) ? ms : 0 });
    if (b.runs.length > b.span) b.runs.shift();
    if (b.runs.length < b.span) return;      // no full run yet, so no score

    /* The clock is the sum of the games themselves, not wall time across the
     * window. What sits between them is reading the fact under a solved
     * question, or leaving the tab open over lunch, and neither is the thing
     * being measured. Nobody should lose a tie-break for reading the answer. */
    var s = 0, t = 0;
    for (var i = 0; i < b.runs.length; i++) { s += b.runs[i].net; t += b.runs[i].ms; }
    var run = { s: s, t: t };
    if (!better(run, b.best)) return;
    b.best = run;

    // Already named this session: the run goes up quietly, which is the point
    // of asking once. Anything else would interrupt a sliding window over and
    // over on the way to a good score.
    if (b.mine) { send(b, b.mine); paint(b); return; }
    if (!b.asked && beats(b, b.best)) ask(b);      // ask() paints
    else paint(b);
  }

  /* --- what the games call ------------------------------------------------- */

  window.KhaanaBoard = {
    /* key, and {span, root, name}: how many consecutive games make a score,
     * the id of the section to draw it in, and what to call the game. */
    track: function (key, cfg) {
      if (!boards[key]) make(key, cfg);
    },
    /* One solved game, and what it was worth net of the misses on the way,
     * with how long it took in milliseconds. */
    game: function (key, net, ms) {
      var b = boards[key];
      if (b && typeof net === 'number' && isFinite(net)) record(b, net, ms);
    }
  };
})();
