/* Fun facts: the noises the games make.
 *
 * Lifted out of the trivia, which is where all of this was written and where it
 * was the only game that made a sound. The map game wanted the same two notes,
 * and a second copy of an oscillator is a second thing to keep in tune — worse,
 * a second mute flag, so a reader who turned the sound off in one game would be
 * shouted at by the other.
 *
 * One switch, one preference, one audio context. The context is built on the
 * first sound rather than on load: browsers refuse to start one before the
 * reader has done something, and a page that asks on arrival gets a warning in
 * the console and nothing else.
 *
 * The stored key is still khaana-trivia-sound. It reads oddly now that it
 * governs three games, but it is what everyone who has already turned the sound
 * off has in their browser, and renaming it would silently switch them all back
 * on.
 */
(function () {
  'use strict';

  var KEY = 'khaana-trivia-sound';
  var Ctx = window.AudioContext || window.webkitAudioContext;
  var audio = null;
  var watchers = [];
  var muted;

  /* Off by default for anyone who has asked for reduced motion. They have said
   * they want less happening at them, and a noise is something happening at
   * them. Anyone who has set it explicitly gets what they set. */
  try {
    muted = localStorage.getItem(KEY) === 'off';
    if (localStorage.getItem(KEY) === null) {
      muted = !!(window.matchMedia &&
                 window.matchMedia('(prefers-reduced-motion: reduce)').matches);
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

  function play(fn) {
    var a = ready();
    if (!a) return;
    try { fn(a, a.currentTime); } catch (e) { /* no audio is not a broken game */ }
  }

  window.KhaanaSound = {
    available: !!Ctx,
    muted: function () { return muted; },

    /* Right: a quick major arpeggio that jumps an octave at the end. Triangle
     * rather than sine, which is the difference between a lift chime and
     * something with a bit of arcade in it. */
    cheer: function () {
      play(function (a, t0) {
        [1046.5, 1318.5, 1568.0, 2093.0].forEach(function (hz, n) {
          blip(a, t0 + n * 0.07, hz, n === 3 ? 0.34 : 0.16, 'triangle', 0.085);
        });
      });
    },

    /* Wrong: the two-note descending womp. A sawtooth sliding down a minor
     * third, twice, each landing lower than the last. Comic rather than harsh —
     * it should read as "ah, no" and not as an error dialog. */
    womp: function () {
      play(function (a, t0) {
        blip(a, t0, [311.1, 261.6], 0.20, 'sawtooth', 0.055);
        blip(a, t0 + 0.19, [261.6, 174.6], 0.38, 'sawtooth', 0.055);
      });
    },

    /* A piece put down. One short note and a quiet one: this fires on every
     * placement, several times a round, and anything with a shape to it would
     * be the loudest thing in the game by the end of a sitting. */
    tick: function () {
      play(function (a, t0) { blip(a, t0, 880, 0.07, 'triangle', 0.03); });
    },

    /* A piece taken back off. The tick, downward, so the pair read as a thing
     * going down and the same thing coming up. */
    undo: function () {
      play(function (a, t0) { blip(a, t0, [740, 560], 0.09, 'triangle', 0.028); });
    },

    /* The end of a run. The cheer with two more notes on the top of it, so
     * finishing does not sound like getting one more right. */
    fanfare: function () {
      play(function (a, t0) {
        [784.0, 1046.5, 1318.5, 1568.0, 2093.0, 2637.0].forEach(function (hz, n) {
          blip(a, t0 + n * 0.09, hz, n === 5 ? 0.5 : 0.18, 'triangle', 0.08);
        });
      });
    },

    toggle: function () {
      muted = !muted;
      try { localStorage.setItem(KEY, muted ? 'off' : 'on'); }
      catch (e) { /* not remembering it is survivable */ }
      watchers.forEach(function (fn) { fn(muted); });
      if (!muted) window.KhaanaSound.cheer();  // so you hear what you turned on
      return muted;
    },

    /* Told whenever the switch moves, so a toggle in one panel can repaint a
     * toggle in another. There is one on the page today; there was nearly a
     * second the moment a third game wanted sound. */
    onChange: function (fn) { watchers.push(fn); }
  };
})();
