/* Khaana - recipe detail page.
   Reads ?id= from the URL and renders one recipe from the curated database,
   marking up which ingredients the cook already ticked on the Cook page. */
(function () {
  'use strict';

  var STORAGE_KEY = 'khaana.pantry.v1';
  var pantry = null, recipe = null, have = new Set();

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function nameFor(id) {
    var found = null;
    pantry.categories.forEach(function (c) {
      c.items.forEach(function (i) { if (i.id === id) found = i.name; });
    });
    return found || id.replace(/-/g, ' ').replace(/\b\w/g, function (m) { return m.toUpperCase(); });
  }

  function param(k) {
    var m = new RegExp('[?&]' + k + '=([^&]+)').exec(window.location.search);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function classify(id) {
    if (pantry.staples.indexOf(id) !== -1) return { state: 'staple' };
    if (have.has(id)) return { state: 'have' };
    var opts = pantry.substitutions[id] || [];
    for (var i = 0; i < opts.length; i++) {
      if (have.has(opts[i].id)) return { state: 'substitute', via: opts[i] };
    }
    return { state: 'missing', options: opts };
  }

  function render() {
    var r = recipe;
    document.title = r.name + ' recipe | Khaana';

    var total = r.prepMinutes + r.cookMinutes;
    var host = document.getElementById('recipe');

    var ingHtml = r.ingredients.map(function (ing) {
      var c = classify(ing.id);
      var badge = '';
      if (c.state === 'have') badge = '<span class="ing-badge have">have</span>';
      else if (c.state === 'substitute') {
        badge = '<span class="ing-badge sub">use ' + esc(nameFor(c.via.id)) + '</span>';
      } else if (c.state === 'missing' && have.size > 0) {
        badge = '<span class="ing-badge miss">need</span>';
      }
      var subNote = '';
      if (c.state === 'substitute') {
        subNote = '<span class="ing-note">' + esc(c.via.note) + '</span>';
      } else if (c.state === 'missing' && c.options.length) {
        subNote = '<span class="ing-note">or ' + c.options.map(function (o) {
          return esc(nameFor(o.id)) + ' (' + esc(o.note) + ')';
        }).join('; ') + '</span>';
      }
      return '<li class="' + (ing.essential === false ? 'optional' : '') + '">' +
        '<span class="ing-qty">' + esc(ing.qty) + '</span> ' +
        '<span class="ing-name">' + esc(nameFor(ing.id)) + '</span> ' + badge +
        (ing.note ? '<span class="ing-note">' + esc(ing.note) + '</span>' : '') +
        subNote +
        (ing.essential === false ? '<span class="ing-opt">optional</span>' : '') +
      '</li>';
    }).join('');

    var stepsHtml = r.steps.map(function (s, i) {
      var g = s.glossary ? glossaryBox(s.glossary) : '';
      return '<li>' + esc(s.text) +
        (s.tip ? '<span class="step-tip">' + esc(s.tip) + '</span>' : '') + g + '</li>';
    }).join('');

    var glossHtml = (r.glossary || []).map(glossaryBox).join('');

    host.innerHTML =
      '<nav class="crumbs"><a href="cook.html">&larr; Back to suggestions</a></nav>' +
      '<div class="recipe-head">' +
        '<div class="recipe-headline">' +
          // Not every cuisine has a region page of its own; those show as plain text.
          '<div class="eyebrow">' + (r.regionPage
            ? '<a href="' + esc(r.regionPage) + '">' + esc(r.region) + '</a>'
            : esc(r.region)) + '</div>' +
          '<h1>' + esc(r.name) + '</h1>' +
          '<p class="lede">' + esc(r.subtitle) + '</p>' +
          '<div class="diet-tags">' + r.tags.map(function (t) {
              return '<span class="diet-tag">' + esc(t.replace(/-/g, ' ')) + '</span>';
            }).join('') + '</div>' +
        '</div>' +
        (r.image
          ? '<figure class="recipe-photo">' +
              '<img src="' + esc(r.image.src) + '" alt="' + esc(r.image.alt) + '" />' +
              '<figcaption>Photo: ' + esc(r.image.credit) + ' &middot; ' +
                esc(r.image.license) + '</figcaption>' +
            '</figure>'
          : '<figure class="recipe-photo recipe-photo-none" aria-hidden="true">' +
              '<span>' + esc(r.name.charAt(0)) + '</span>' +
            '</figure>') +
      '</div>' +

      '<div class="recipe-stats">' +
        stat('Prep', r.prepMinutes + ' min') +
        stat('Cook', r.cookMinutes + ' min') +
        stat('Total', total + ' min') +
        stat('Serves', String(r.servings)) +
        stat('Difficulty', r.difficulty) +
      '</div>' +

      (r.allergens && r.allergens.length
        ? '<p class="allergen"><strong>Contains:</strong> ' + r.allergens.map(esc).join(', ') + '</p>'
        : '<p class="allergen none"><strong>Allergens:</strong> none of the common ones</p>') +

      '<div class="recipe-cols">' +
        '<div class="recipe-ing">' +
          '<h2>Ingredients</h2>' +
          '<p class="serves-note">Quantities for ' + r.servings + '.</p>' +
          '<ul class="ing-list">' + ingHtml + '</ul>' +
          '<h3>Cookware</h3>' +
          '<p class="equip-line">' + r.equipment.map(function (e) {
              return esc(e.replace(/-/g, ' '));
            }).join(', ') + '</p>' +
        '</div>' +
        '<div class="recipe-method">' +
          (r.prepNotes && r.prepNotes.length
            ? '<h2>Before you start</h2><ul class="prep-notes">' +
              r.prepNotes.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') + '</ul>'
            : '') +
          '<h2>Method</h2>' +
          '<ol class="steps">' + stepsHtml + '</ol>' +
          '<h2>Storage</h2><p>' + esc(r.storage) + '</p>' +
          (glossHtml ? '<h2>Ingredients &amp; techniques explained</h2>' + glossHtml : '') +
        '</div>' +
      '</div>' +

      '<p class="provenance">Recipe v' + esc(r.provenance.recipeVersion) +
        ', last updated ' + esc(r.provenance.updated) +
        '. Curated for Khaana and kept under version control.</p>';
  }

  function stat(label, value) {
    return '<div class="stat"><span class="stat-label">' + esc(label) +
      '</span><span class="stat-value">' + esc(value) + '</span></div>';
  }

  function glossaryBox(key) {
    var g = pantry.glossary[key];
    if (!g) return '';
    return '<aside class="gloss"><strong>' + esc(g.term) + '</strong>' + esc(g.text) + '</aside>';
  }

  function notFound(id) {
    document.getElementById('recipe').innerHTML =
      '<nav class="crumbs"><a href="cook.html">&larr; Back to suggestions</a></nav>' +
      '<h1>Recipe not found</h1><p>No recipe with the id &ldquo;' + esc(id || '') +
      '&rdquo; exists in the database yet.</p>';
  }

  try {
    var raw = localStorage.getItem(STORAGE_KEY);
    if (raw) JSON.parse(raw).forEach(function (i) { have.add(i); });
  } catch (e) { /* ignore */ }

  var wanted = param('id');
  // One detail file per recipe, so opening a page never downloads the others.
  // An unknown id 404s, which is the not-found path rather than an error.
  Promise.all([
    fetch('data/pantry.json').then(function (r) { return r.json(); }),
    fetch('data/recipes/' + encodeURIComponent(wanted || '') + '.json')
      .then(function (r) { return r.ok ? r.json() : null; })
  ]).then(function (res) {
    pantry = res[0];
    recipe = res[1];
    if (!recipe) return notFound(wanted);
    render();
  }).catch(function (e) {
    document.getElementById('recipe').innerHTML =
      '<p>Could not load the recipe database. Serve this site over http rather than opening the file directly.</p>';
    if (window.console) console.error(e);
  });
})();
