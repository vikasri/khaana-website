/* Fun facts: match four dishes to four cuisines.
 *
 * The page ships a pool of dishes grouped by cuisine (build-trivia.py writes
 * it into #pair-pool). A round is four cuisines drawn at random, no two the
 * same, and one dish drawn at random from each. Place all four and the round
 * is marked: right pairs lock green, wrong ones go red and come back to be
 * tried again, and the attempt count climbs until all four are right.
 *
 * Why the cuisines never move in the DOM
 * --------------------------------------
 * A chip looks like it travels from the bank to a slot, but the element
 * itself stays where it was built and the board is repainted from state. Two
 * reasons. Moving a <button> into a slot that must itself be clickable means
 * nesting one control inside another, which no screen reader reads sensibly.
 * And a placed chip keeps its space in the bank rather than collapsing it, so
 * the chips still on the board do not jump sideways under a moving finger —
 * which they did, and it made a drag land on the wrong chip's old position.
 *
 * Placement works three ways because a board like this is used three ways:
 * drag with a mouse or a finger, tap a cuisine and then tap a slot, or tab to
 * a cuisine and press Enter and do the same to a slot. The pointer path is
 * built on Pointer Events rather than the HTML drag-and-drop API, which does
 * not fire for touch at all.
 */
(function () {
  'use strict';

  var ROWS = 4;                    // dishes a round, and so cuisines a round
  /* Two for a pair that is right, one off for one that is not, which puts a
   * round solved blind at 8 and one solved on the second go at 5. The floor is
   * open: keep guessing badly and the score keeps falling. Counting only the
   * right ones would give everybody 8 in the end, since the round does not
   * finish until they are all right. */
  var RIGHT = 2, WRONG = -1;
  var PER_ROUND = ROWS * RIGHT;      // eight, if a round is solved blind
  /* The board is marked the moment the fourth cuisine lands — a zero timeout
   * rather than a direct call only so the browser paints that last placement
   * before the verdict appears on top of it. The wait below is not the
   * reader waiting to be told; it is the wrong pairs staying put long enough
   * to be read before they go back. */
  var WRONG_MS = 1100;             // how long a wrong pair stays red before it returns
  var DRAG_SLOP = 6;               // px of movement before a press becomes a drag

  var panel = document.getElementById('pair-game');
  var rowsEl = document.getElementById('pair-rows');
  var bankEl = document.getElementById('pair-bank');
  var attemptEl = document.getElementById('pair-attempt');
  var scoreEl = document.getElementById('pair-score');
  var verdictEl = document.getElementById('pair-verdict');
  var againBtn = document.getElementById('pair-again');
  var poolEl = document.getElementById('pair-pool');
  var msgEl = document.getElementById('pair-messages');
  if (!panel || !rowsEl || !bankEl || !poolEl) return;

  var pool;
  try { pool = JSON.parse(poolEl.textContent); } catch (e) { return; }
  var cuisines = Object.keys(pool || {}).filter(function (c) {
    return pool[c] && pool[c].length;
  });
  // Without four cuisines to draw from there is no round to deal, and an empty
  // board is worse than none: the panel stays hidden and the page is just the
  // trivia, which is what a reader without JavaScript gets anyway.
  if (cuisines.length < ROWS) return;

  /* The line after an attempt, by attempt number and how it went. Keyed
   * "1".."5" in data/trivia.json, where "5" also covers the sixth attempt and
   * every one after it — a reader on their ninth go wants a joke, not a
   * counter. Missing copy leaves the line off rather than inventing one. */
  var MSG_LAST = 5;
  var messages = {};
  if (msgEl) {
    try { messages = JSON.parse(msgEl.textContent) || {}; } catch (e) { messages = {}; }
  }

  function messageFor(n, how) {
    var set = messages[String(Math.min(n, MSG_LAST))];
    return (set && set[how]) || '';
  }

  var reduced = window.matchMedia &&
                window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* --- the round ---------------------------------------------------------- */

  var pairs = [];        // [{dish, cuisine}] in the order the rows are shown
  var chipOrder = [];    // the same cuisines, shuffled again for the bank
  var placed = [];       // placed[row] = cuisine name, or null
  var locked = [];       // locked[row] = true once that row has been marked right
  var attempt = 1;
  /* Score and rounds both run for as long as the reader does. A round used to
   * wipe the slate, which made the number a report on the last four dishes
   * rather than on the session: solve three rounds well and a bad fourth left
   * you looking like you had never got one right. The denominator grows with
   * the rounds instead, so 22 / 32 says what it took to get there. */
  var score = 0;
  var rounds = 0;
  var busy = false;      // true while a mark is being shown or a new round dealt
  var selected = null;   // cuisine picked by tap or keyboard, waiting for a slot
  var timers = [];

  function later(fn, ms) { timers.push(setTimeout(fn, ms)); }
  function clearTimers() {
    timers.forEach(clearTimeout);
    timers = [];
  }

  function pick(list, n) {
    // Fisher-Yates on a copy, then the first n. Shuffling the whole list for
    // four of twenty-one costs nothing and is one obviously correct thing
    // rather than a sampling loop that has to think about collisions.
    var a = list.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return n == null ? a : a.slice(0, n);
  }

  function deal() {
    clearTimers();
    busy = false;
    selected = null;
    attempt = 1;
    rounds++;
    var chosen = pick(cuisines, ROWS);
    pairs = chosen.map(function (c) {
      var entry = pick(pool[c], 1)[0];      // [name, thumbnail id or null]
      return { cuisine: c, dish: entry[0], thumb: entry[1] };
    });
    // The bank is shuffled separately, or the first cuisine in the bank would
    // always belong to the first dish and the round would give itself away.
    chipOrder = pick(chosen);
    placed = [null, null, null, null];
    locked = [false, false, false, false];
    build();
    paint();
    if (verdictEl) {
      verdictEl.hidden = true;
      verdictEl.textContent = '';
      verdictEl.removeAttribute('data-tone');
    }
    if (againBtn) againBtn.hidden = true;
    bankEl.classList.remove('is-spent');
  }

  /* --- the board ---------------------------------------------------------- */

  function build() {
    rowsEl.textContent = '';
    pairs.forEach(function (p, i) {
      var li = document.createElement('li');
      li.className = 'pair-row';
      li.setAttribute('data-row', i);

      var dish = document.createElement('span');
      dish.className = 'pair-dish';
      /* The photograph is decorative and carries no alt text: the dish is
       * named in the same box, and a screen reader announcing it twice is
       * worse than not announcing it at all. A dish the site has no picture of
       * gets an empty square rather than a gap, so the rows stay in line. */
      var thumb;
      if (p.thumb) {
        thumb = document.createElement('img');
        thumb.className = 'pair-thumb';
        thumb.alt = '';
        thumb.width = 48;
        thumb.height = 48;
        /* Not lazy, and src set last. Four pictures of 3 KB, on screen the
         * moment the board is, are not worth deferring — and deferring them
         * did not work: the rows are built in the same tick that unhides the
         * panel, so the browser measured them against a layout that had not
         * happened, decided they were out of view, and never asked again.
         * Live, the squares stayed empty and no request was ever made. */
        thumb.decoding = 'async';
        thumb.src = 'assets/images/pair/' + p.thumb + '.jpg';
      } else {
        thumb = document.createElement('span');
        thumb.className = 'pair-thumb pair-thumb-none';
        thumb.setAttribute('aria-hidden', 'true');
      }
      dish.appendChild(thumb);
      dish.appendChild(document.createTextNode(p.dish));

      var slot = document.createElement('button');
      slot.type = 'button';
      slot.className = 'pair-slot';
      slot.setAttribute('data-row', i);

      li.appendChild(dish);
      li.appendChild(slot);
      rowsEl.appendChild(li);
    });

    bankEl.textContent = '';
    chipOrder.forEach(function (c) {
      var chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'pair-chip';
      chip.setAttribute('data-cuisine', c);
      chip.textContent = c;
      bankEl.appendChild(chip);
    });
  }

  function rowOf(cuisine) {
    for (var i = 0; i < placed.length; i++) if (placed[i] === cuisine) return i;
    return -1;
  }

  function paint() {
    var slots = rowsEl.querySelectorAll('.pair-slot');
    for (var i = 0; i < slots.length; i++) {
      var slot = slots[i];
      var name = placed[i];
      slot.textContent = name || '';
      slot.classList.toggle('is-filled', !!name);
      slot.classList.toggle('is-target', !name && !!selected);
      slot.disabled = locked[i] || busy;
      slot.setAttribute('aria-label', name
        ? (locked[i]
            ? name + ', matched with ' + pairs[i].dish
            : name + ', placed on ' + pairs[i].dish + '. Press to take it back.')
        : (selected
            ? 'Put ' + selected + ' on ' + pairs[i].dish
            : 'Empty box for ' + pairs[i].dish));
    }

    var chips = bankEl.querySelectorAll('.pair-chip');
    for (var j = 0; j < chips.length; j++) {
      var chip = chips[j];
      var c = chip.getAttribute('data-cuisine');
      var on = rowOf(c) >= 0;
      chip.classList.toggle('is-placed', on);
      chip.classList.toggle('is-picked', selected === c);
      chip.disabled = on || busy;
      chip.setAttribute('aria-pressed', selected === c ? 'true' : 'false');
    }

    if (attemptEl) attemptEl.textContent = 'Attempt ' + attempt;
    if (scoreEl) {
      scoreEl.textContent = 'Score ' + score + ' / ' + (rounds * PER_ROUND);
      scoreEl.setAttribute('data-neg', score < 0 ? '1' : '0');
    }
  }

  /* --- placing ------------------------------------------------------------ */

  function place(row, cuisine) {
    if (busy || locked[row] || placed[row]) return;
    var from = rowOf(cuisine);
    if (from >= 0) {
      if (locked[from]) return;      // already matched; it stays where it is
      placed[from] = null;
    }
    placed[row] = cuisine;
    selected = null;
    paint();
    if (placed.every(Boolean)) later(mark, 0);
  }

  function lift(row) {
    if (busy || locked[row] || !placed[row]) return;
    placed[row] = null;
    selected = null;
    paint();
  }

  /* --- marking ------------------------------------------------------------ */

  function mark() {
    busy = true;
    var wrong = [];
    var slots = rowsEl.querySelectorAll('.pair-slot');
    pairs.forEach(function (p, i) {
      if (locked[i]) return;
      if (placed[i] === p.cuisine) {
        locked[i] = true;
        score += RIGHT;
        slots[i].classList.add('is-right');
      } else {
        wrong.push(i);
        score += WRONG;
        slots[i].classList.add('is-wrong');
      }
    });
    paint();

    if (!wrong.length) {
      solved();
      return;
    }

    // "Some right" is about the board, not about this attempt alone: a row
    // matched two attempts ago is still sitting there in green, so a reader
    // told "none correct" would be looking straight at one that is.
    say(attempt, locked.some(Boolean) ? 'some' : 'none');

    later(function () {
      wrong.forEach(function (i) {
        placed[i] = null;
        slots[i].classList.remove('is-wrong');
      });
      // The counter is of attempts made, so it moves on the attempt that
      // failed and not on the one about to be made. A round solved first time
      // reads "Attempt 1" throughout, and gets the first-attempt line.
      attempt++;
      busy = false;
      paint();
    }, reduced ? 500 : WRONG_MS);
  }

  /* The line after an attempt, and its colour. A miss reads in the same maroon
   * as a wrong trivia answer and a finished board in the same dark green as a
   * right one, so the two games agree about what red and green mean. */
  function say(n, how) {
    if (!verdictEl) return;
    var line = messageFor(n, how);
    verdictEl.textContent = line;
    verdictEl.hidden = !line;
    verdictEl.setAttribute('data-tone', how === 'all' ? 'win' : 'miss');
  }

  /* A solved board stays solved. It used to deal the next round on a timer,
   * which took the finished board away mid-sentence — the reader had four
   * pairs to look at and about two seconds to do it. Now nothing moves until
   * they ask for another. */
  function solved() {
    say(attempt, 'all');
    // Every chip is placed, so on a phone — where the bank sits under the
    // board rather than beside it — the space it was holding open is now a
    // blank block between the last pair and the reply. Nothing is being
    // dragged any more, so it can safely go.
    bankEl.classList.add('is-spent');
    if (againBtn) {
      againBtn.hidden = false;
      againBtn.focus();
    }
  }

  /* --- pointer, tap and keyboard ------------------------------------------ */

  var drag = null;     // {chip, cuisine, id, x0, y0, moved, ghost}

  function ghostFor(chip, cuisine) {
    var g = document.createElement('div');
    g.className = 'pair-ghost';
    g.textContent = cuisine;
    g.style.width = chip.offsetWidth + 'px';
    document.body.appendChild(g);
    return g;
  }

  function moveGhost(e) {
    drag.ghost.style.left = e.clientX + 'px';
    drag.ghost.style.top = e.clientY + 'px';
    var under = document.elementFromPoint(e.clientX, e.clientY);
    var slot = under && under.closest ? under.closest('.pair-slot') : null;
    if (slot && (slot.disabled || placed[+slot.getAttribute('data-row')])) slot = null;
    var slots = rowsEl.querySelectorAll('.pair-slot');
    for (var i = 0; i < slots.length; i++) {
      slots[i].classList.toggle('is-over', slots[i] === slot);
    }
    return slot;
  }

  function endDrag(e, drop) {
    var slots = rowsEl.querySelectorAll('.pair-slot');
    for (var i = 0; i < slots.length; i++) slots[i].classList.remove('is-over');
    if (drag.ghost) drag.ghost.remove();
    drag.chip.classList.remove('is-dragging');
    if (drop) place(+drop.getAttribute('data-row'), drag.cuisine);
    drag = null;
  }

  bankEl.addEventListener('pointerdown', function (e) {
    var chip = e.target.closest ? e.target.closest('.pair-chip') : null;
    if (!chip || chip.disabled || drag || busy) return;
    drag = {
      chip: chip,
      cuisine: chip.getAttribute('data-cuisine'),
      id: e.pointerId,
      x0: e.clientX, y0: e.clientY,
      moved: false, ghost: null
    };
    // Capture on the chip, so a fast drag that outruns the pointer still
    // reports its moves here rather than to whatever it flew over.
    try { chip.setPointerCapture(e.pointerId); } catch (err) { /* fine without */ }
  });

  bankEl.addEventListener('pointermove', function (e) {
    if (!drag || e.pointerId !== drag.id) return;
    if (!drag.moved) {
      if (Math.abs(e.clientX - drag.x0) < DRAG_SLOP &&
          Math.abs(e.clientY - drag.y0) < DRAG_SLOP) return;
      drag.moved = true;
      drag.ghost = ghostFor(drag.chip, drag.cuisine);
      drag.chip.classList.add('is-dragging');
    }
    e.preventDefault();
    moveGhost(e);
  });

  bankEl.addEventListener('pointerup', function (e) {
    if (!drag || e.pointerId !== drag.id) return;
    if (!drag.moved) {                      // a press that never moved is a tap
      var c = drag.cuisine;
      endDrag(e, null);
      selected = selected === c ? null : c;
      paint();
      return;
    }
    endDrag(e, moveGhost(e));
  });

  bankEl.addEventListener('pointercancel', function (e) {
    if (drag && e.pointerId === drag.id) endDrag(e, null);
  });

  // A chip reached by keyboard never sees a pointer event, so Enter and Space
  // arrive here as a plain click and mean the same as a tap.
  bankEl.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('.pair-chip') : null;
    if (!chip || chip.disabled || busy) return;
    if (e.detail) return;                   // a real tap; pointerup handled it
    var c = chip.getAttribute('data-cuisine');
    selected = selected === c ? null : c;
    paint();
  });

  rowsEl.addEventListener('click', function (e) {
    var slot = e.target.closest ? e.target.closest('.pair-slot') : null;
    if (!slot || slot.disabled || busy) return;
    var row = +slot.getAttribute('data-row');
    if (placed[row]) { lift(row); return; }
    if (selected) place(row, selected);
  });

  /* --- the way in --------------------------------------------------------- */

  if (againBtn) againBtn.addEventListener('click', deal);

  /* Dealt on load rather than behind a button. The button asked the reader to
   * opt into a game that was already built and sitting there, which is a
   * question with one sensible answer. The panel carries `hidden` in the
   * markup and is un-hidden here, so a reader with no JavaScript still gets
   * the trivia alone rather than an empty board. Play again deals the next
   * round, and is also the way out of one going badly. */
  panel.hidden = false;
  deal();
})();
