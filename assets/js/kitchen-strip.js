/* Khaana — "what can I cook tonight" strip on the homepage.

   The Cook page already remembers a pantry in localStorage, but nothing ever
   told the reader that. This reads the same key, scores the same way, and shows
   the three best matches so a returning visitor lands on something cookable.

   Deliberately silent on a first visit: with an empty pantry every score is 0,
   and a strip promising "0 dishes" is worse than no strip. */
(function () {
  'use strict';

  var STORAGE_KEY = 'khaana.pantry.v1';
  var SHOW = 3;
  var MIN_PCT = 20;          // same floor the Cook page uses
  // Same shelf weights, and they have to stay the same: the strip and the Cook
  // page show a percentage for the same recipe, and two different numbers for
  // one dish is a bug the reader can see. Reasoning lives in cook.js.
  var CAT_WEIGHT = {
    protein: 2.5, pulses: 2.0, veg: 1.6, grains: 1.5, spices: 0.4
  };
  var ING_WEIGHT = { paneer: 2.5, tofu: 2.5 };   // filed as dairy, cooked as the main event
  // A centre-of-the-plate ingredient the database rarely asks for is a strong
  // signal of what the cook wants; a common one is not. Reasoning in cook.js.
  var RARE_SHARE = 0.04, RARE_BONUS = 1.4;
  var CENTRE_SHELVES = { protein: 1, pulses: 1, veg: 1, grains: 1 };

  var strip = document.getElementById('kitchen-strip');
  if (!strip) return;

  var have = new Set();
  try {
    var raw = localStorage.getItem(STORAGE_KEY);
    if (raw) JSON.parse(raw).forEach(function (i) { have.add(i); });
  } catch (e) { return; }
  if (have.size === 0) return;

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  Promise.all([
    fetch('data/pantry.json?v=48f0f84c').then(function (r) { return r.json(); }),
    fetch('data/recipes-index.json?v=ee4d857b').then(function (r) { return r.json(); })
  ]).then(function (res) {
    var pantry = res[0], recipes = res[1].recipes;
    var staples = pantry.staples, subs = pantry.substitutions;

    var shelf = {};
    pantry.categories.forEach(function (c) {
      c.items.forEach(function (i) { shelf[i.id] = c.id; });
    });

    var freq = {};
    recipes.forEach(function (r) {
      r.ingredients.forEach(function (i) {
        if (i.essential === false) return;
        freq[i.id] = (freq[i.id] || 0) + 1;
      });
    });

    function weightFor(id) {
      var cw = ING_WEIGHT[id];
      if (typeof cw !== 'number') cw = CAT_WEIGHT[shelf[id]];
      if (typeof cw !== 'number') cw = 1;
      var centre = CENTRE_SHELVES[shelf[id]] || typeof ING_WEIGHT[id] === 'number';
      if (centre && (freq[id] || 0) < recipes.length * RARE_SHARE) cw *= RARE_BONUS;
      return cw;
    }

    function score(r) {
      var earned = 0, possible = 0;
      r.ingredients.forEach(function (ing) {
        if (staples.indexOf(ing.id) !== -1) return;      // assumed present
        var w = (ing.essential === false ? 0.35 : 1) * weightFor(ing.id);
        possible += w;
        if (have.has(ing.id)) { earned += w; return; }
        var opts = subs[ing.id] || [];
        for (var i = 0; i < opts.length; i++) {
          if (have.has(opts[i].id)) { earned += w * (1 - (opts[i].penalty || 0.2)); return; }
        }
      });
      return possible > 0 ? Math.round((earned / possible) * 100) : 0;
    }

    var scored = recipes.map(function (r) { return { r: r, pct: score(r) }; })
                        .filter(function (s) { return s.pct >= MIN_PCT; })
                        .sort(function (a, b) { return b.pct - a.pct; });

    if (scored.length === 0) return;

    var n = scored.length;
    document.getElementById('kitchen-count').textContent =
      'You can make ' + (n > 100 ? '100+' : n) + (n === 1 ? ' dish' : ' dishes') + ' right now';
    // "starter": the saved pantry is a partial picture, so the count should not
    // sound like a complete inventory of what the reader owns.
    document.getElementById('kitchen-note').textContent =
      'Based on the ' + have.size +
      (have.size === 1 ? ' starter ingredient' : ' starter ingredients') +
      ' saved in your kitchen.';

    document.getElementById('kitchen-cards').innerHTML =
      scored.slice(0, SHOW).map(function (s) {
        var r = s.r;
        var thumb = r.image
          ? '<img src="' + esc(r.image.src) + '" alt="' + esc(r.image.alt) + '" loading="lazy" />'
          : '<span class="kitchen-card-noimg" aria-hidden="true">' + esc(r.name.charAt(0)) + '</span>';
        return '<a class="kitchen-card" href="recipes/' + esc(r.id) + '.html">' +
                 '<span class="kitchen-card-thumb">' + thumb + '</span>' +
                 '<span class="kitchen-card-body">' +
                   '<span class="kitchen-card-pct">' + s.pct + '%</span>' +
                   '<span class="kitchen-card-name">' + esc(r.name) + '</span>' +
                   '<span class="kitchen-card-meta">' + esc(r.region) + ' &middot; ' +
                     (r.prepMinutes + r.cookMinutes) + ' min' +
                     // Active minutes. A card this small has no room for the
                     // figure, but "+ soaking" is the part that decides
                     // whether it can be tonight's dinner.
                     (r.inactiveMinutes ? ' + ' + esc(r.inactiveLabel) : '') +
                   '</span>' +
                 '</span>' +
               '</a>';
      }).join('');

    strip.hidden = false;
  }).catch(function () { /* homepage still works without the strip */ });
})();
