/* Saved recipes.

   Kept in localStorage and nowhere else. No account, no server, nothing
   leaves the browser, which is why this needed no backend and carries no
   privacy obligations. The cost of that choice is real and the page says so:
   a recipe saved on a phone is not there on a laptop.

   Two views use this, the recipe page and the Cook page result cards, and the
   Cook page redraws its cards on every keystroke. So state lives here rather
   than in either of them, and both listen for one event instead of reaching
   into each other. */
(function () {
  'use strict';

  var KEY = 'khaana.saved.v1';
  var ids = null;

  function load() {
    if (ids) return ids;
    ids = [];
    try {
      var raw = localStorage.getItem(KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        if (Object.prototype.toString.call(parsed) === '[object Array]') {
          ids = parsed.filter(function (x) { return typeof x === 'string'; });
        }
      }
    } catch (e) { /* private mode, or someone edited it by hand */ }
    return ids;
  }

  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(ids)); }
    catch (e) { /* private mode; the toggle still works for this session */ }
  }

  function announce() {
    document.dispatchEvent(new CustomEvent('khaana:saved-changed',
      { detail: { count: ids.length } }));
  }

  var API = {
    all: function () { return load().slice(); },
    count: function () { return load().length; },
    has: function (id) { return load().indexOf(id) !== -1; },
    toggle: function (id) {
      load();
      var i = ids.indexOf(id);
      if (i === -1) ids.push(id); else ids.splice(i, 1);
      save();
      announce();
      return i === -1;
    }
  };

  /* One heart, filled or not. An inline SVG rather than the characters
     "\u2665" and "\u2661": the hollow one is missing from a number of common
     fonts and falls back to a box, and where it does render the two are
     different weights and sit on different baselines, so the shape appeared
     to jump when tapped. The path is identical in both states, so only the
     fill changes. */
  var HEART = 'M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 ' +
              '7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 ' +
              '3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z';

  API.button = function (id, opts) {
    opts = opts || {};
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'save-btn' + (opts.compact ? ' save-btn-compact' : '');
    b.setAttribute('data-save-id', id);
    API.paint(b, API.has(id));
    return b;
  };

  API.paint = function (b, on) {
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    // The heart carries no text, so the accessible name has to come from
    // here: a screen reader should hear what the control does, not "path".
    b.setAttribute('aria-label', on ? 'Saved. Tap to remove from saved'
                                    : 'Save this recipe');
    b.classList.toggle('is-saved', on);
    b.innerHTML =
      '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
        '<path d="' + HEART + '"/>' +
      '</svg>';
  };

  // One delegated listener for the whole page, so cards redrawn after a filter
  // change keep working without rewiring.
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.save-btn');
    if (!b) return;
    // Cards wrap a stretched link over the whole tile; without this the click
    // opens the recipe instead of saving it.
    ev.preventDefault();
    ev.stopPropagation();
    var id = b.getAttribute('data-save-id');
    if (!id) return;
    API.paint(b, API.toggle(id));
  });

  // Saved in one tab, reflected in another.
  window.addEventListener('storage', function (e) {
    if (e.key !== KEY) return;
    ids = null;
    load();
    document.querySelectorAll('.save-btn').forEach(function (b) {
      API.paint(b, API.has(b.getAttribute('data-save-id')));
    });
    announce();
  });

  // Buttons that came down in the HTML are empty until painted, so the state
  // is decided by this browser rather than baked into a page that is the same
  // for everyone and cached for a year.
  function paintExisting() {
    document.querySelectorAll('.save-btn').forEach(function (b) {
      if (!b.querySelector('svg')) API.paint(b, API.has(b.getAttribute('data-save-id')));
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', paintExisting);
  } else {
    paintExisting();
  }
  API.paintExisting = paintExisting;

  window.KhaanaSaved = API;
}());
