/* Fun facts: show five of the hundred questions, chosen by today's date.
 *
 * The page ships all hundred in the markup so it works without JavaScript and
 * so a crawler sees the lot. This hides all but today's five and turns them
 * into something you can answer.
 *
 * Picking the five
 * ----------------
 * Deterministic from the date, never random: everyone gets the same five on
 * the same day, and a reload does not reshuffle them mid-quiz.
 *
 *   day    days since the epoch, in local time
 *   slot   which group of five within the twenty-day cycle
 *   cycle  which twenty-day cycle we are in
 *
 * Index = (slot * 5 + i + cycle * SHIFT) mod 100.
 *
 * The (slot * 5 + i) part walks 0..99 exactly once across a cycle, so twenty
 * days covers every question with none repeated. Adding cycle * SHIFT moves
 * the whole deck each cycle, and because SHIFT shares no factor with 100 the
 * questions land in different groups of five every time round. Without it the
 * same five would always appear together, which gets stale faster than the
 * questions do.
 */
(function () {
  'use strict';

  var PER_DAY = 5;
  // Coprime with 100, so the per-cycle shift visits every offset before
  // repeating. 10 or 25 would collapse into a handful of arrangements.
  var SHIFT = 7;
  var list = document.getElementById('trivia-list');
  if (!list) return;

  var all = Array.prototype.slice.call(list.querySelectorAll('.tq'));
  if (!all.length) return;

  var total = all.length;
  var days = Math.floor(total / PER_DAY);

  // Local midnight, not UTC: the day should turn over when the reader's day
  // does, not at some hour that depends on where they are.
  var now = new Date();
  var midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  var day = Math.floor(midnight.getTime() / 86400000);
  var slot = ((day % days) + days) % days;
  var cycle = Math.floor(day / days);

  var todays = [];
  for (var i = 0; i < PER_DAY; i++) {
    var idx = (((slot * PER_DAY + i + cycle * SHIFT) % total) + total) % total;
    todays.push(all[idx]);
  }

  all.forEach(function (el) { el.hidden = true; });
  todays.forEach(function (el, n) {
    el.hidden = false;
    var num = el.querySelector('.tq-n');
    if (num) num.textContent = (n + 1) + '. ';
    list.appendChild(el);              // reorder into today's sequence
  });

  var dayLine = document.getElementById('trivia-day');
  if (dayLine) {
    dayLine.textContent = now.toLocaleDateString(undefined, {
      weekday: 'long', day: 'numeric', month: 'long'
    });
  }

  /* --- the celebratory noise ---------------------------------------------
   *
   * Two sounds, synthesised rather than loaded: a rising arpeggio for a right
   * answer and a descending womp for a wrong one. Generating them costs a few
   * lines and no download, and every envelope fades to silence rather than
   * stopping dead, which is what stops a short tone clicking at the edges.
   *
   * Sound on a web page is rude by default, so:
   *   - it only ever plays in response to a click the reader made on purpose.
   *     Browsers require that gesture anyway before audio may start.
   *   - it is quiet. Peak gain 0.09.
   *   - there is a mute button, and the choice is remembered.
   *   - anyone who has asked their system for reduced motion gets it off to
   *     begin with; that setting is the closest thing we have to "do not
   *     surprise me".
   */
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

  var answered = 0, right = 0;
  var scoreEl = document.getElementById('trivia-score');
  var footEl = document.getElementById('trivia-foot');

  function scoreLine() {
    if (!scoreEl) return;
    scoreEl.hidden = false;
    scoreEl.textContent = right + ' of ' + answered + ' right';
    scoreEl.setAttribute('data-all', answered === PER_DAY ? 'done' : 'part');
  }

  list.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('.tq-opt') : null;
    if (!btn) return;
    var q = btn.closest('.tq');
    if (!q || q.classList.contains('answered')) return;   // one go per question

    var correct = parseInt(q.getAttribute('data-answer'), 10);
    var chose = parseInt(btn.getAttribute('data-i'), 10);
    q.classList.add('answered');

    q.querySelectorAll('.tq-opt').forEach(function (b) {
      var i = parseInt(b.getAttribute('data-i'), 10);
      b.disabled = true;
      if (i === correct) b.classList.add('is-right');
      else if (i === chose) b.classList.add('is-wrong');
    });

    // The note is the payoff, so it shows either way. Getting it wrong and
    // then being told nothing would be the worst of both.
    var note = q.querySelector('.tq-note');
    if (note) note.hidden = false;

    answered++;
    if (chose === correct) { right++; cheer(); } else { womp(); }
    scoreLine();
    if (answered === PER_DAY && footEl) footEl.hidden = false;
  });
})();
