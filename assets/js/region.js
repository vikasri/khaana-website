/* Fun facts: put the cuisines back on the map.
 *
 * The same map the home page shows, with everything that names a zone taken
 * off it: the legend, the numbered pins, and the tooltips the zones carry. What
 * is left is seventeen unlabelled shapes over India, and a bank of five cuisine
 * names to drop onto them.
 *
 * One map, two uses
 * -----------------
 * The file is loaded and stripped here rather than kept as a second, quieter
 * copy on disk. A map that exists twice is a map that gets corrected once — and
 * the zones on it are the thing this game is scored against, so the two copies
 * disagreeing would not be a cosmetic bug but a wrong answer. The home page
 * embeds it in an <object>, which is its own document and cannot be reached
 * into usefully; here the markup is fetched and inlined, because the game has
 * to hang events on the individual zones.
 *
 * How a round works
 * -----------------
 * Five names at a time. Place all five and mark them: the ones that landed
 * right stay where they are and are done with, the ones that did not come back
 * to the bank, and the bank is topped up from what is left until it is five
 * again. So the five are never five fresh names — they are whatever is still
 * unplaced, and the run ends when the last zone is named.
 *
 * Two for a right one and one off for a wrong one, as in the other two games,
 * and the total is allowed to go negative.
 *
 * Optional, like everything else on this page: no fetch, no map, no game, and
 * the two games above it play exactly as they do.
 */
(function () {
  'use strict';

  var MAP = 'assets/images/india-cuisine-zones.svg';
  var HAND = 5;                    // names in the bank at once
  var RIGHT = 2, WRONG = -1;
  var DRAG_SLOP = 6;               // px before a press becomes a drag
  /* Cropped to the country. The file's own box is 381 -820 2319 2160, which
   * leaves room down the right for the legend and above for the map's title —
   * both of which this game takes off, and neither of which is worth the space
   * once they are gone. Measured rather than guessed: the states run x 430 to
   * 1924 and y -234 to 1246, and the zones drawn over them reach x 406 to 1955
   * and y -511 to 1205, so this is their union with a margin. */
  var BOX = '370 -560 1630 1870';

  var panel = document.getElementById('region-game');
  var mapEl = document.getElementById('region-map');
  var bankEl = document.getElementById('region-bank');
  var scoreEl = document.getElementById('region-score');
  var leftEl = document.getElementById('region-left');
  var verdictEl = document.getElementById('region-verdict');
  var markBtn = document.getElementById('region-mark');
  if (!panel || !mapEl || !bankEl || !window.fetch) return;

  var reduced = window.matchMedia &&
                window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var svg = null;
  var zones = {};        // cuisine -> {path, cx, cy, done}
  var pool = [];         // cuisines not yet placed correctly, unshuffled order
  var hand = [];         // the five in the bank
  var placed = {};       // cuisine -> the zone name it has been dropped on
  var score = 0;
  var busy = false;
  var selected = null;

  function shuffle(list) {
    var a = list.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  /* --- the map ------------------------------------------------------------ */

  /* Everything that would answer the question, removed.
   *
   * Three things name a zone on the published map and all three have to go: the
   * legend down the right-hand side, the numbered pins that key into it, and
   * the <title> on each zone, which is what a browser shows as a tooltip and
   * what a screen reader reads. The links go too — every zone is wrapped in an
   * anchor to that cuisine's page, so a mis-aimed drop would otherwise leave
   * the page mid-game, and the href names the cuisine besides.
   */
  function strip(doc) {
    var el = doc.getElementById('map-legend');
    if (el) el.parentNode.removeChild(el);
    el = doc.getElementById('zone-numbers');
    if (el) el.parentNode.removeChild(el);

    var links = doc.querySelectorAll('a.zone-link');
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      while (a.firstChild) a.parentNode.insertBefore(a.firstChild, a);
      a.parentNode.removeChild(a);
    }
    var titles = doc.querySelectorAll('title');
    for (i = 0; i < titles.length; i++) {
      titles[i].parentNode.removeChild(titles[i]);
    }
    /* The map's own furniture: its title and the wordmark under it. They are
     * there for a map that travels on its own, and this one is inside a panel
     * that has just said what it is. They are also set across the full width
     * the legend used to occupy, so left in they would be the only reason not
     * to crop to the country. */
    var texts = doc.querySelectorAll('svg > text, svg > g > text');
    for (i = 0; i < texts.length; i++) {
      if (texts[i].closest('#cuisine-zones')) continue;
      texts[i].parentNode.removeChild(texts[i]);
    }
  }

  function buildMap(text) {
    var doc = new DOMParser().parseFromString(text, 'image/svg+xml');
    var root = doc.querySelector('svg');
    if (!root || doc.querySelector('parsererror')) return false;
    strip(doc);
    root.setAttribute('viewBox', BOX);
    root.removeAttribute('width');
    root.removeAttribute('height');
    root.setAttribute('class', 'region-svg');
    root.setAttribute('preserveAspectRatio', 'xMidYMid meet');

    mapEl.textContent = '';
    svg = document.importNode(root, true);
    mapEl.appendChild(svg);

    var paths = svg.querySelectorAll('[data-zone]');
    if (!paths.length) return false;
    for (var i = 0; i < paths.length; i++) {
      paths[i].setAttribute('class', 'region-zone');
      zones[paths[i].getAttribute('data-zone')] = { path: paths[i], cx: 0, cy: 0 };
    }
    return true;
  }

  /* Each zone's own centre, read off the shape rather than guessed at: it is
   * where a placed name is written, and the zones are octagons of a dozen
   * different sizes.
   *
   * Measured after the panel is shown, and not a moment before. getBBox on
   * anything inside a display:none subtree answers zero — truthfully, since a
   * box that is not laid out has no size — and the panel ships hidden and is
   * revealed once the map has loaded. Measured on the wrong side of that, every
   * name in the game was drawn at the origin, off the top-left of the map. */
  function measure() {
    var ok = false;
    for (var name in zones) {
      if (!zones.hasOwnProperty(name)) continue;
      var b = zones[name].path.getBBox();
      if (!b.width) continue;
      zones[name].cx = b.x + b.width / 2;
      zones[name].cy = b.y + b.height / 2;
      ok = true;
    }
    return ok;
  }

  /* The name written across the zone it has been dropped on. Drawn into the
   * map rather than laid over it, so it scales and moves with the shape it
   * belongs to and needs no second coordinate system. */
  function label(zone, text, state) {
    var z = zones[zone];
    if (!z) return;
    // A zone whose centre never took — the panel was hidden when it was asked,
    // or the map was still settling. Cheap to ask again, and the alternative is
    // a name stacked at the origin.
    if (!z.cx && !z.cy) measure();
    var t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    t.setAttribute('class', 'region-label' + (state ? ' is-' + state : ''));
    t.setAttribute('x', z.cx);
    t.setAttribute('y', z.cy);
    t.setAttribute('text-anchor', 'middle');
    t.setAttribute('dominant-baseline', 'central');
    t.setAttribute('data-for', zone);
    t.textContent = text;
    svg.appendChild(t);
  }

  function clearLabel(zone) {
    var old = svg.querySelectorAll('[data-for="' + zone + '"]');
    for (var i = 0; i < old.length; i++) old[i].parentNode.removeChild(old[i]);
  }

  /* --- the bank ----------------------------------------------------------- */

  function refill() {
    while (hand.length < HAND && pool.length) hand.push(pool.shift());
  }

  function paint() {
    bankEl.textContent = '';
    hand.forEach(function (name) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'region-chip';
      b.setAttribute('data-cuisine', name);
      b.textContent = name;
      var on = placed[name];
      if (on) b.classList.add('is-placed');
      if (selected === name) b.classList.add('is-picked');
      b.setAttribute('aria-pressed', selected === name ? 'true' : 'false');
      b.disabled = busy;
      bankEl.appendChild(b);
    });

    for (var name in zones) {
      if (!zones.hasOwnProperty(name)) continue;
      var z = zones[name];
      z.path.classList.toggle('is-done', !!z.done);
      z.path.classList.toggle('is-taken', takenBy(name) !== null);
    }

    var all = Object.keys(zones).length;
    var done = Object.keys(zones).filter(function (k) { return zones[k].done; }).length;
    if (leftEl) {
      leftEl.textContent = done === all ? 'All ' + all + ' placed'
                                        : done + ' of ' + all + ' placed';
    }
    if (scoreEl) {
      scoreEl.textContent = 'Score: ' + score;
      scoreEl.setAttribute('data-neg', score < 0 ? '1' : '0');
    }
    if (markBtn) {
      var ready = hand.length > 0 && hand.every(function (n) { return placed[n]; });
      markBtn.hidden = !ready || busy;
    }
  }

  function takenBy(zone) {
    for (var name in placed) {
      if (placed.hasOwnProperty(name) && placed[name] === zone) return name;
    }
    return null;
  }

  /* --- placing ------------------------------------------------------------ */

  function place(zone, cuisine) {
    if (busy || !zones[zone] || zones[zone].done) return;
    if (hand.indexOf(cuisine) < 0) return;
    // One name to a zone. Dropping onto a zone that already holds one sends
    // that one back to the bank rather than refusing the move: the reader has
    // said where they want this one and the other was only a guess too.
    var sitting = takenBy(zone);
    if (sitting && sitting !== cuisine) {
      delete placed[sitting];
      clearLabel(zone);
    }
    if (placed[cuisine]) clearLabel(placed[cuisine]);
    placed[cuisine] = zone;
    clearLabel(zone);
    label(zone, cuisine, 'set');
    selected = null;
    paint();
  }

  function lift(cuisine) {
    if (busy || !placed[cuisine]) return;
    clearLabel(placed[cuisine]);
    delete placed[cuisine];
    paint();
  }

  /* --- marking ------------------------------------------------------------ */

  function mark() {
    if (busy) return;
    busy = true;
    var right = 0, wrong = 0;
    hand.slice().forEach(function (name) {
      var on = placed[name];
      if (!on) return;
      clearLabel(on);
      if (on === name) {
        right++;
        score += RIGHT;
        zones[name].done = true;
        label(name, name, 'right');
        hand.splice(hand.indexOf(name), 1);
        delete placed[name];
      } else {
        wrong++;
        score += WRONG;
        // Shown in the wrong place for a moment, so the miss is legible as a
        // miss rather than as the name simply vanishing.
        label(on, name, 'wrong');
      }
    });

    say(right, wrong);
    paint();

    later(function () {
      Object.keys(placed).forEach(function (name) {
        clearLabel(placed[name]);
        delete placed[name];
      });
      refill();
      busy = false;
      paint();
      if (!hand.length) done();
    }, reduced ? 0 : 1200);
  }

  function done() {
    if (verdictEl) {
      verdictEl.textContent = 'That is the whole map. Final score ' + score + '.';
      verdictEl.hidden = false;
      verdictEl.setAttribute('data-tone', 'win');
    }
    if (markBtn) markBtn.hidden = true;
  }

  function say(right, wrong) {
    if (!verdictEl) return;
    var line;
    if (!wrong) line = right === 1 ? 'Right where it belongs.'
                                   : 'All ' + right + ' in the right place.';
    else if (!right) line = wrong === 1 ? 'Not that one. Try it again.'
                                        : 'None of those. They come back for another go.';
    else line = right + ' right, ' + wrong + ' back for another go.';
    verdictEl.textContent = line;
    verdictEl.hidden = false;
    verdictEl.setAttribute('data-tone', wrong ? 'miss' : 'win');
  }

  var timers = [];
  function later(fn, ms) { timers.push(setTimeout(fn, ms)); }

  /* --- pointer, tap and keyboard ------------------------------------------ */

  var drag = null;

  function zoneAt(x, y) {
    var el = document.elementFromPoint(x, y);
    if (!el || !el.getAttribute) return null;
    var name = el.getAttribute('data-zone');
    if (!name || !zones[name] || zones[name].done) return null;
    return name;
  }

  function ghostFor(chip, name) {
    var g = document.createElement('div');
    g.className = 'region-ghost';
    g.textContent = name;
    document.body.appendChild(g);
    return g;
  }

  function moveGhost(e) {
    drag.ghost.style.left = e.clientX + 'px';
    drag.ghost.style.top = e.clientY + 'px';
    var over = zoneAt(e.clientX, e.clientY);
    for (var name in zones) {
      if (zones.hasOwnProperty(name)) {
        zones[name].path.classList.toggle('is-over', name === over);
      }
    }
    return over;
  }

  function endDrag(drop) {
    for (var name in zones) {
      if (zones.hasOwnProperty(name)) zones[name].path.classList.remove('is-over');
    }
    if (drag.ghost) drag.ghost.remove();
    drag.chip.classList.remove('is-dragging');
    if (drop) place(drop, drag.cuisine);
    drag = null;
  }

  bankEl.addEventListener('pointerdown', function (e) {
    var chip = e.target.closest ? e.target.closest('.region-chip') : null;
    if (!chip || chip.disabled || drag || busy) return;
    drag = {
      chip: chip, cuisine: chip.getAttribute('data-cuisine'), id: e.pointerId,
      x0: e.clientX, y0: e.clientY, moved: false, ghost: null
    };
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
    if (!drag.moved) {                     // a press that never moved is a tap
      var c = drag.cuisine;
      endDrag(null);
      if (placed[c]) { lift(c); return; }
      selected = selected === c ? null : c;
      paint();
      return;
    }
    endDrag(moveGhost(e));
  });

  bankEl.addEventListener('pointercancel', function (e) {
    if (drag && e.pointerId === drag.id) endDrag(null);
  });

  // A chip reached by keyboard never sees a pointer, so Enter and Space arrive
  // as a plain click and mean the same as a tap.
  bankEl.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('.region-chip') : null;
    if (!chip || chip.disabled || busy || e.detail) return;
    var c = chip.getAttribute('data-cuisine');
    if (placed[c]) { lift(c); return; }
    selected = selected === c ? null : c;
    paint();
  });

  mapEl.addEventListener('click', function (e) {
    if (busy || !selected) return;
    var name = e.target.getAttribute && e.target.getAttribute('data-zone');
    if (!name || !zones[name] || zones[name].done) return;
    place(name, selected);
  });

  if (markBtn) {
    var pressed = false;
    markBtn.addEventListener('pointerdown', function () { pressed = true; });
    markBtn.addEventListener('click', function (e) {
      // As in the matching game: the button appears the moment the fifth name
      // goes down, so it will not take a press it did not see begin on itself.
      if (!pressed && e.detail !== 0) return;
      pressed = false;
      mark();
    });
  }

  /* --- the way in --------------------------------------------------------- */

  fetch(MAP).then(function (r) {
    return r.ok ? r.text() : Promise.reject();
  }).then(function (text) {
    if (!buildMap(text)) return;
    pool = shuffle(Object.keys(zones));
    refill();
    panel.hidden = false;
    measure();
    paint();
  }).catch(function () {
    /* No map, no game. The page is the two above it, which is what a reader
       without JavaScript gets anyway. */
  });
})();
