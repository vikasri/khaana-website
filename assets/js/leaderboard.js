/* Fun facts: the best-ten board, and the matching game's best-five.
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
 * Why two rows and not one
 * ------------------------
 * One is a record; two is a board. The second row is the bar a new player has
 * to clear, and it is the number this file compares against, so it belongs on
 * screen. Two is also all that is stored: a score that cannot displace the
 * second row is not written anywhere.
 *
 * Where it lives
 * --------------
 * localStorage, on the one device, like favourites.js. There is no server
 * behind this site and no account, so a name typed here is seen by whoever is
 * holding the phone and by nobody else. That is the whole design and not a
 * limitation of it: the tagline asks you to test your family, and this is a
 * board your family passes around.
 *
 * The name is asked for once a session, the first time a player displaces the
 * second row, and never again — after that their row climbs on its own as
 * their best improves. Asking on every improvement would interrupt a sliding
 * window several times a sitting.
 */
(function () {
  'use strict';

  var KEY = 'khaana-fun-board';
  var KEEP = 2;                    // rows stored, and rows shown
  var MAX_NAME = 16;

  /* --- what is on the board ------------------------------------------------ */

  /* Seasons, ended by hand.
   *
   * A board that is never cleared stops being a competition — two good runs in
   * its first week and everyone after them is playing for third place, which
   * does not exist — so it gets cleared. When is a decision, not a rule: this
   * board runs until somebody ends it.
   *
   * Ending one
   * ----------
   * Change TAG to anything it has not been before — "2", "diwali", a date —
   * and deploy. Every stored board carries the old stamp, none of them match
   * the new one, and the next visit anyone makes starts them empty. That is
   * the whole of a site-wide reset: one string, one push.
   *
   * To clear a single device rather than all of them, in that browser's
   * console:
   *
   *     localStorage.removeItem('khaana-fun-board')
   *
   * Handing it to the calendar instead
   * ----------------------------------
   * PERIOD is the switch, and it is off. Set it to 'month' or 'quarter' and
   * the date joins the stamp, so every board clears itself on the 1st without
   * anyone touching the file again.
   *
   * It ships off on purpose. A calendar rule fires on a date nobody chose,
   * possibly mid-week with somebody halfway through a run, and once it is in
   * the reader's browser it cannot be called back. A reset that happens only
   * when it is asked for is the one that can be timed. The switch is here so
   * that changing your mind is one word rather than a rewrite.
   */
  var TAG = '1';
  var PERIOD = null;               // null | 'month' | 'quarter'

  function season() {
    if (!PERIOD) return TAG;
    var d = new Date(), m = d.getMonth();
    return TAG + ':' + d.getFullYear() + '-' +
           (PERIOD === 'quarter' ? 'q' + (Math.floor(m / 3) + 1) : (m + 1));
  }

  function readAll() {
    try {
      var raw = localStorage.getItem(KEY);
      var all = raw ? JSON.parse(raw) : null;
      if (!all || typeof all !== 'object') return {};
      if (all.season !== season()) {
        localStorage.removeItem(KEY);      // last month's board, so no board
        return {};
      }
      return all;
    } catch (e) {
      return {};                   // storage blocked or corrupt; play without it
    }
  }

  /* Trusting nothing that comes back out: this is the one input to the page
   * that a previous version of this file wrote, and a half-written or
   * hand-edited value should cost a board rather than the game under it. */
  function entriesFor(all, key) {
    var list = all[key];
    if (Object.prototype.toString.call(list) !== '[object Array]') return [];
    var out = [];
    for (var i = 0; i < list.length && out.length < KEEP; i++) {
      var e = list[i];
      if (!e || typeof e.n !== 'string' || typeof e.s !== 'number') continue;
      if (!isFinite(e.s)) continue;
      out.push({ n: e.n.slice(0, MAX_NAME), s: Math.round(e.s), t: time(e.t) });
    }
    return out;
  }

  /* A run with no usable time loses every tie, which is the safe way round: a
   * row written by some earlier version of this file should not outrank a
   * timed one on a technicality. A day, so it is still a number in storage. */
  var SLOW = 86400000;
  function time(v) {
    return (typeof v === 'number' && isFinite(v) && v >= 0) ? Math.round(v) : SLOW;
  }

  function save(key, entries) {
    var all = readAll();
    all.season = season();
    all[key] = entries.map(function (e) { return { n: e.n, s: e.s, t: e.t }; });
    try { localStorage.setItem(KEY, JSON.stringify(all)); }
    catch (e) { /* not remembering it is survivable */ }
  }

  /* --- names ---------------------------------------------------------------
   *
   * A name never leaves the device, so this is not moderation — there is
   * nobody downstream to protect. It is there so that a board the family looks
   * at cannot be scrawled on by whoever had the phone last.
   *
   * Which is also its limit, and worth being honest about: everything here
   * runs in the browser, so anyone willing to open the console can write what
   * they like into storage. It stops the typing, not the determined.
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

  /* --- one board ----------------------------------------------------------- */

  var boards = {};

  function make(key, cfg) {
    var root = document.getElementById(cfg.root);
    if (!root) return null;
    var b = {
      key: key,
      span: cfg.span,
      root: root,
      rowsEl: root.querySelector('.board-rows'),
      joinEl: root.querySelector('.board-join'),
      nameEl: root.querySelector('.board-name-input'),
      errEl: root.querySelector('.board-error'),
      youEl: root.querySelector('.board-you'),
      entries: entriesFor(readAll(), key),
      runs: [],                    // the last `span` games, newest last
      best: null,                  // best window this session, {s, t}
      mine: null,                  // this player's row, once they have named it
      asked: false                 // the name has been asked for, once, or waived
    };
    boards[key] = b;
    wire(b);
    paint(b);
    return b;
  }

  /* Score first, then the clock.
   *
   * Time is the tie-break rather than a score of its own: a run is judged on
   * what it got right, and only two runs that got the same amount right are
   * separated by how long they took. It also keeps the board open. Ten
   * questions answered clean is twenty and there is no twenty-one, so without
   * a second key a perfect run could never be displaced and the board would
   * close the first time somebody had a good afternoon.
   *
   * Strictly better, both ways: equal on both is not better, so an incumbent
   * is never moved by being matched.
   */
  function better(run, than) {
    if (!than) return true;
    if (run.s !== than.s) return run.s > than.s;
    return run.t < than.t;
  }

  /* The bar to get on: the second row, or nothing at all while there are fewer
   * than two rows. An empty slot takes any run, which is what seeds a new
   * device — the first two sittings are on the board whatever they did, and
   * the third is the first that has to earn it. */
  function beats(b, run) {
    return b.entries.length < KEEP || better(run, b.entries[KEEP - 1]);
  }

  /* Whole seconds under a minute, m:ss over it. Tenths would suggest the
   * clock is doing more than breaking ties, and it is not. */
  function clock(ms) {
    if (ms >= SLOW) return '';
    var s = Math.round(ms / 1000);
    if (s < 60) return s + 's';
    var m = Math.floor(s / 60);
    s -= m * 60;
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  /* The player's own best, once they have a full run behind them.
   *
   * Shown whether or not it is good enough for the board, and that is the
   * point: a window of ten only exists after the tenth game, so before it
   * there is nothing to say, and after it a player who is nowhere near the
   * second row still gets to watch their own number move. Without this the
   * board is a wall to everyone who is not on it. */
  function paintYou(b) {
    if (!b.youEl) return;
    b.youEl.hidden = b.best === null;
    if (b.best === null) return;
    /* Laid out in the same three columns as the rows above it, and for a
     * reason beyond neatness: written as a sentence it read "Your best 10",
     * where the 10 is the score and the title above already says ten games.
     * In the score column there is nothing to misread. */
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

  function paint(b) {
    var show = b.entries.length > 0 || b.best !== null ||
               (b.joinEl && !b.joinEl.hidden);
    b.root.hidden = !show;
    paintYou(b);
    if (!b.rowsEl) return;
    b.rowsEl.textContent = '';
    b.entries.forEach(function (e, i) {
      var li = document.createElement('li');
      li.className = 'board-row';
      if (b.mine === e) li.setAttribute('data-mine', '1');
      cells(li, (i + 1) + '.', e.n, e);
      b.rowsEl.appendChild(li);
    });
  }

  /* Score down, clock up, and stable — so a run that matches the one above it
   * on both keys stays below it. Same rule as `better`, applied after the
   * fact: an incumbent is never moved by being matched. */
  function order(b) {
    b.entries.sort(function (x, y) { return x.s === y.s ? x.t - y.t : y.s - x.s; });
    b.entries = b.entries.slice(0, KEEP);
  }

  function place(b, name) {
    var entry = { n: name, s: b.best.s, t: b.best.t };
    b.mine = entry;
    b.entries.push(entry);
    order(b);
    // Trimming can drop the row just added, if the board was full of better
    // scores. It cannot here — nothing is placed unless it beat the second
    // row — but a dropped row must not go on being written to.
    if (b.entries.indexOf(entry) < 0) b.mine = null;
    save(b.key, b.entries);
    paint(b);
  }

  function wire(b) {
    if (!b.joinEl) return;
    b.joinEl.addEventListener('submit', function (e) {
      e.preventDefault();
      var raw = (b.nameEl.value || '').replace(/\s+/g, ' ').trim().slice(0, MAX_NAME);
      if (!raw || !letters(raw)) return fail(b, 'Enter a name.');
      if (!decent(raw)) return fail(b, 'Pick another name.');
      b.errEl.hidden = true;
      b.joinEl.hidden = true;
      b.nameEl.value = '';
      place(b, raw);
    });
    var skip = b.joinEl.querySelector('.board-skip');
    if (skip) {
      skip.addEventListener('click', function () {
        b.joinEl.hidden = true;    // asked already, so it does not come back
        paint(b);
      });
    }
  }

  function fail(b, why) {
    if (!b.errEl) return;
    b.errEl.textContent = why;
    b.errEl.hidden = false;
    b.nameEl.focus();
    b.nameEl.select();
  }

  function ask(b) {
    if (!b.joinEl) return;
    b.asked = true;
    b.joinEl.hidden = false;
    paint(b);
  }

  /* --- the sliding window -------------------------------------------------- */

  function record(b, net, ms) {
    b.runs.push({ net: net, ms: time(ms) });
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

    if (b.mine) {
      // Already named this session: the row climbs quietly, which is the point
      // of asking once. It can overtake the row above it, hence the re-sort.
      if (better(b.best, b.mine)) {
        b.mine.s = b.best.s;
        b.mine.t = b.best.t;
        order(b);
        save(b.key, b.entries);
      }
      paint(b);
      return;
    }
    if (!b.asked && beats(b, b.best)) ask(b);      // ask() paints
    else paint(b);
  }

  /* --- what the games call ------------------------------------------------- */

  window.KhaanaBoard = {
    /* key, and {span, root}: how many consecutive games make a score, and the
     * id of the section to draw it in. */
    track: function (key, cfg) {
      if (!boards[key]) make(key, cfg);
    },
    /* One solved game: what it was worth net of the misses on the way, and
     * how long it took in milliseconds. */
    game: function (key, net, ms) {
      var b = boards[key];
      if (b && typeof net === 'number' && isFinite(net)) record(b, net, ms);
    }
  };
})();
