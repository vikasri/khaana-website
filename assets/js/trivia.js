/* Fun facts: one question at a time, drawn at random.
 *
 * The page ships every question in the markup, so it works without JavaScript
 * and a crawler sees the lot. This hides all but one and turns that one into
 * something you can answer.
 *
 * Picking them
 * ------------
 * Random, and no repeat: each question drawn is removed from the pool, so a
 * session works through the bank without ever asking twice. When the pool runs
 * out it refills and reshuffles rather than stopping — a reader who wants to
 * keep going keeps going, which is the whole point of a page like this.
 *
 * The old scheme picked five a day by date so that everyone saw the same five.
 * That is the right design for a daily ritual and the wrong one for somebody
 * who is enjoying themselves: it ran out after five and told them to come back
 * tomorrow.
 */
(function () {
  'use strict';

  var list = document.getElementById('trivia-list');
  if (!list) return;

  var all = Array.prototype.slice.call(list.querySelectorAll('.tq'));
  if (!all.length) return;

  var pool = [];                 // questions not yet asked this session
  var current = null;
  var served = 0;                // questions shown, which sets the denominator

  // Every question is in the markup, for a crawler and for a reader with no
  // JavaScript. With JavaScript they all go, and one comes back at a time.
  all.forEach(function (el) { el.hidden = true; });

  function refill() {
    pool = all.slice();
  }

  function show() {
    if (current) current.hidden = true;
    if (!pool.length) refill();
    var i = Math.floor(Math.random() * pool.length);
    current = pool.splice(i, 1)[0];
    current.hidden = false;
    served++;
    var num = current.querySelector('.tq-n');
    if (num) num.textContent = served + '. ';
    // A question asked twice would have its previous answer still marked, so
    // anything the reader did to it last time comes off before it is asked
    // again. Only reachable once the bank has been through a full pass.
    qNet = 0;                      // a new question, so a new game for the board
    qStart = Date.now();           // and its clock starts when it is put up
    current.classList.remove('answered', 'is-holding');
    current.querySelectorAll('.tq-opt').forEach(function (b) {
      b.disabled = false;
      b.classList.remove('is-right', 'is-wrong');
    });
    var note = current.querySelector('.tq-note');
    if (note) note.hidden = true;
    var nudged = current.querySelector('.tq-nudge');
    if (nudged) nudged.hidden = true;
    if (nextBtn) nextBtn.hidden = true;
  }

  var nextBtn = document.getElementById('trivia-next');

  var Ctx = window.AudioContext || window.webkitAudioContext;
  var audio = null;
  var muted;
  try {
    muted = localStorage.getItem('khaana-trivia-sound') === 'off';
    if (localStorage.getItem('khaana-trivia-sound') === null) {
      muted = window.matchMedia &&
              window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
  } catch (e) {
    muted = false;                       // storage blocked; sound on, not broken
  }

  function ready() {
    if (muted || !Ctx) return null;
    try {
      if (!audio) audio = new Ctx();
      if (audio.state === 'suspended') audio.resume();
      return audio;
    } catch (e) { return null; }
  }

  /* A short blip. hz may be a number, or [from, to] to slide between them. */
  function blip(a, at, hz, dur, type, peak) {
    var osc = a.createOscillator();
    var gain = a.createGain();
    osc.type = type;
    if (hz.length) {
      osc.frequency.setValueAtTime(hz[0], at);
      osc.frequency.exponentialRampToValueAtTime(hz[1], at + dur);
    } else {
      osc.frequency.value = hz;
    }
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(peak, at + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    osc.connect(gain).connect(a.destination);
    osc.start(at);
    osc.stop(at + dur + 0.02);
  }

  /* Right: a quick major arpeggio that jumps an octave at the end. Triangle
   * rather than sine, which is the difference between a lift chime and
   * something with a bit of arcade in it. */
  function cheer() {
    var a = ready();
    if (!a) return;
    try {
      var t0 = a.currentTime;
      [1046.5, 1318.5, 1568.0, 2093.0].forEach(function (hz, n) {
        blip(a, t0 + n * 0.07, hz, n === 3 ? 0.34 : 0.16, 'triangle', 0.085);
      });
    } catch (e) { /* no audio is not a broken quiz */ }
  }

  /* Wrong: the two-note descending womp. A sawtooth sliding down a minor
   * third, twice, each landing lower than the last. Comic rather than harsh —
   * it should read as "ah, no" and not as an error dialog. */
  function womp() {
    var a = ready();
    if (!a) return;
    try {
      var t0 = a.currentTime;
      blip(a, t0, [311.1, 261.6], 0.20, 'sawtooth', 0.055);
      blip(a, t0 + 0.19, [261.6, 174.6], 0.38, 'sawtooth', 0.055);
    } catch (e) { /* as above */ }
  }

  var soundBtn = document.getElementById('trivia-sound');
  function paintSound() {
    if (!soundBtn) return;
    soundBtn.setAttribute('aria-pressed', muted ? 'false' : 'true');
    soundBtn.textContent = muted ? 'Sound off' : 'Sound on';
  }
  if (soundBtn) {
    if (!Ctx) soundBtn.hidden = true;    // nothing to toggle
    paintSound();
    soundBtn.addEventListener('click', function () {
      muted = !muted;
      try { localStorage.setItem('khaana-trivia-sound', muted ? 'off' : 'on'); }
      catch (e) { /* not remembering it is survivable */ }
      paintSound();
      if (!muted) cheer();               // so you hear what you just turned on
    });
  }

  /* Keep guessing until you get it.
   *
   * A wrong pick greys itself out and the question stays open, so the reader
   * works down to the answer instead of being told off once and shut out. Only
   * the right answer closes the question and reveals the note, which also
   * means the note is never a consolation prize for having failed.
   *
   * Scoring is what stops that being free. Two for a right answer, one off for
   * a wrong one, so a question solved first time is worth 2, after one miss 1,
   * after two 0, and after three -1. Counting rights alone would put everybody
   * on full marks by the end of the page, which is not a score, it is a
   * participation note.
   *
   * Both run for the session rather than resetting per question: the
   * denominator is two for every question asked, so 14 / 18 says nine
   * questions in and mostly right. The total is allowed to go negative.
   */
  var RIGHT = 2, WRONG = -1;
  var HOLD_MS = 2000;
  var NEXT_MS = 800;               // before Next answers to a click
  var score = 0;
  var scoreEl = document.getElementById('trivia-score');

  /* The score line under the panel, shared with the matching game. A trial
   * there is an answer here: every option pressed moves the total, so every
   * option pressed is a point. The chart is optional — the quiz works the same
   * whether or not the script that draws it loaded.
   *
   * The dotted benchmark on it is half a point per question solved, which is
   * what a blind guesser scores here. Four options, two for the right one and
   * one off for each wrong one, and a wrong pick is eliminated rather than
   * ending the question — so the guesser's wrong count is 0, 1, 2 or 3 with
   * equal chance and the question is worth (2 + 1 + 0 - 1) / 4. A reader under
   * that line is scoring worse than guessing would. */
  var chart = window.KhaanaScoreLine;
  var solved = 0;                  // questions got right, which is games played
  if (chart) chart.track('trivia', 'Trivia',
                         { step: 0.5, label: 'A blindfolded guesser',
                           mark: '🙈' });

  /* The board under the panel wants a score per question rather than the
   * running total: it sums the last ten of them and keeps the best that sum
   * ever reaches. So this is the one question's worth — two, less a point for
   * every wrong press on the way to it — and it resets when a question does.
   * Optional, like the chart: no board script, no board, same quiz.
   *
   * The clock runs from the question going up to it being solved, and stops
   * there. The pause afterwards is the reader reading the fact and deciding to
   * press Next, and timing that would put a stopwatch on the part of the page
   * that is not a game. */
  var board = window.KhaanaBoard;
  var qNet = 0, qStart = 0;
  if (board) board.track('trivia', { span: 10, root: 'board-trivia', name: 'Trivia' });

  /* A friendly line on a wrong answer, and two seconds to read it.
   *
   * Without the pause the messages are pointless: a reader who is guessing
   * clicks straight through the next option and the line changes before their
   * eye has reached it. Two seconds is long enough to read ten words and short
   * enough not to feel like a punishment.
   *
   * The messages come from data/trivia.json by way of a JSON block in the page,
   * so the copy has one home and it is not this file.
   */
  var nudges = [];
  var nudgeEl = document.getElementById('trivia-nudges');
  if (nudgeEl) {
    try { nudges = JSON.parse(nudgeEl.textContent) || []; } catch (e) { nudges = []; }
  }
  var lastNudge = -1;

  function nudge(q) {
    var el = q.querySelector('.tq-nudge');
    if (!el || !nudges.length) return;
    var i = Math.floor(Math.random() * nudges.length);
    // Never the same line twice running; with ten of them that would look
    // less like randomness and more like the page repeating itself.
    if (nudges.length > 1 && i === lastNudge) i = (i + 1) % nudges.length;
    lastNudge = i;
    el.textContent = nudges[i];
    el.hidden = false;
  }

  function hold(q) {
    q.classList.add('is-holding');
    var live = [];
    q.querySelectorAll('.tq-opt').forEach(function (b) {
      if (!b.disabled) { b.disabled = true; live.push(b); }
    });
    setTimeout(function () {
      q.classList.remove('is-holding');
      // Re-enable only what was live when we locked. A question solved in the
      // meantime cannot happen, but re-enabling blindly would undo the
      // permanent disable on the options already spent.
      if (!q.classList.contains('answered')) {
        live.forEach(function (b) { b.disabled = false; });
      }
    }, HOLD_MS);
  }

  function scoreLine() {
    if (!scoreEl) return;
    scoreEl.hidden = false;
    scoreEl.textContent = 'Score ' + score + ' / ' + (served * RIGHT);
    scoreEl.setAttribute('data-all', score === served * RIGHT ? 'done' : 'part');
    scoreEl.setAttribute('data-neg', score < 0 ? '1' : '0');
  }

  list.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('.tq-opt') : null;
    if (!btn || btn.disabled) return;
    var q = btn.closest('.tq');
    if (!q || q.classList.contains('answered')) return;   // already solved

    var correct = parseInt(q.getAttribute('data-answer'), 10);
    var chose = parseInt(btn.getAttribute('data-i'), 10);

    if (chose !== correct) {
      btn.classList.add('is-wrong');
      btn.disabled = true;                 // that one is spent; the rest are not
      score += WRONG;
      qNet += WRONG;
      womp();
      scoreLine();
      if (chart) chart.point('trivia', score);
      nudge(q);
      hold(q);
      return;
    }

    q.classList.add('answered');
    btn.classList.add('is-right');
    q.querySelectorAll('.tq-opt').forEach(function (b) { b.disabled = true; });

    // The nudge was an encouragement to try again. They have, so it goes and
    // the fact takes its place.
    var nudged = q.querySelector('.tq-nudge');
    if (nudged) nudged.hidden = true;

    var note = q.querySelector('.tq-note');
    if (note) note.hidden = false;

    score += RIGHT;
    qNet += RIGHT;
    solved++;                      // the question is over, so a game is done
    cheer();
    scoreLine();
    if (chart) { chart.point('trivia', score); chart.games('trivia', solved); }
    if (board) board.game('trivia', qNet, Date.now() - qStart);
    /* The button goes to where the answer is, not to the foot of the panel.
     * It reads as the end of this question rather than as furniture, and it
     * shares a line with the fact so the two shrink to the same block. */
    if (nextBtn) {
      var after = q.querySelector('.tq-after');
      if (after) after.appendChild(nextBtn);
      nextBtn.hidden = false;
      /* Shown at once so the layout settles, but dead for a second. It used to
       * arrive live and focused on the same frame as the answer, so anyone
       * still clicking through the options hit it before they had read the
       * fact it sits beside, and the question was gone. Long enough to stop
       * the stray click, short enough not to be a gate. */
      nextBtn.disabled = true;
      setTimeout(function () {
        nextBtn.disabled = false;
        nextBtn.focus();
      }, NEXT_MS);
    }
  });

  if (nextBtn) {
    nextBtn.addEventListener('click', function () {
      show();
      scoreLine();
      // Asking for another question is turning back to this game, so the
      // shared frame comes back to it even though nothing has scored yet.
      if (chart) chart.focus('trivia');
    });
  }

  show();                                // the first question, on load
  scoreLine();
})();
