/* Fun facts: show four of the sixty questions, chosen by today's date.
 *
 * The page ships all sixty in the markup so it works without JavaScript and so
 * a crawler sees the lot. This hides all but today's four and turns them into
 * something you can answer.
 *
 * Picking the four
 * ----------------
 * Deterministic from the date, never random: everyone gets the same four on
 * the same day, and a reload does not reshuffle them mid-quiz.
 *
 *   day    days since the epoch, in local time
 *   slot   which group of four within the fifteen-day cycle
 *   cycle  which fifteen-day cycle we are in
 *
 * Index = (slot * 4 + i + cycle * 7) mod 60.
 *
 * The (slot * 4 + i) part walks 0..59 exactly once across a cycle, so a
 * fortnight covers every question with none repeated. Adding cycle * 7 shifts
 * the whole deck each cycle, and because 7 and 60 share no factor the shift
 * lands the questions in different groups of four every time round. Without it
 * the same four would always appear together, which gets stale faster than the
 * questions do.
 */
(function () {
  'use strict';

  var PER_DAY = 4;
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
    var idx = (((slot * PER_DAY + i + cycle * 7) % total) + total) % total;
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
    if (chose === correct) right++;
    scoreLine();
    if (answered === PER_DAY && footEl) footEl.hidden = false;
  });
})();
