/* Khaana — the AI-assisted second tier of the Cook page.
 *
 * Tier 1 (cook.js) ranks Khaana's own curated recipes against the pantry.
 * This module asks the model for ideas beyond that set, and renders them in a
 * visually distinct block so a suggestion is never mistaken for a Khaana recipe.
 *
 * The API key is not here and never reaches the browser — this calls our own
 * /api/suggest endpoint, which holds the key server-side.
 */
(function () {
  'use strict';

  var ENDPOINT = '/api/suggest';
  var STORAGE_KEY = 'khaana.pantry.v1';

  var el = function (id) { return document.getElementById(id); };

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function readPantry() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }

  function readFilters() {
    var pick = function (sel) {
      return Array.prototype.slice.call(document.querySelectorAll(sel))
        .map(function (i) { return i.value; });
    };
    var t = el('f-time') ? el('f-time').value : '';
    return {
      diets: pick('input[name="diet"]:checked'),
      equipment: pick('input[name="equip"]:checked'),
      maxMinutes: t ? parseInt(t, 10) : null,
      skill: el('f-skill') ? (el('f-skill').value || null) : null
    };
  }

  // Don't let the model re-suggest dishes Khaana already has a real recipe for.
  function curatedNames() {
    return Array.prototype.slice.call(document.querySelectorAll('.match-card h3'))
      .map(function (h) {
        return h.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-');
      })
      .filter(Boolean);
  }

  function setStatus(msg, kind) {
    var box = el('ai-status');
    box.textContent = msg || '';
    box.className = 'ai-status' + (kind ? ' ' + kind : '');
    box.hidden = !msg;
  }

  function card(s) {
    var uses = (s.usesFromPantry || []).map(esc).join(', ');
    var needs = (s.alsoNeeds || []).map(esc).join(', ');
    return '' +
      '<article class="ai-card">' +
        '<div class="ai-card-head">' +
          '<h4>' + esc(s.name) + '</h4>' +
          '<span class="ai-badge">AI suggestion</span>' +
        '</div>' +
        '<div class="ai-meta">' + esc(s.region) + ' &middot; ' + esc(s.difficulty) +
          ' &middot; about ' + esc(s.approxMinutes) + ' min</div>' +
        '<p class="ai-summary">' + esc(s.summary) + '</p>' +
        (uses ? '<p class="ai-line"><strong>Uses:</strong> ' + uses + '</p>' : '') +
        (needs ? '<p class="ai-line"><strong>You would also need:</strong> ' + needs + '</p>'
               : '<p class="ai-line ai-line-ok">Nothing extra needed.</p>') +
        (s.note ? '<p class="ai-note-line">' + esc(s.note) + '</p>' : '') +
      '</article>';
  }

  function render(list) {
    var out = el('ai-results');
    if (!list.length) {
      out.innerHTML = '';
      setStatus('No further ideas for this pantry. The recipes above are your best options.', '');
      return;
    }
    out.innerHTML =
      '<p class="ai-disclaimer">These are model-generated ideas, not Khaana recipes. ' +
      'They have not been written to the same standard as the recipes above and have no ' +
      'tested quantities. Treat them as starting points.</p>' +
      list.map(card).join('');
  }

  function ask(btn) {
    var pantry = readPantry();
    if (!pantry.length) {
      setStatus('Tick a few ingredients first, then ask for more ideas.', 'warn');
      return;
    }

    var f = readFilters();
    btn.disabled = true;
    setStatus('Thinking about what else you could make…', 'busy');
    el('ai-results').innerHTML = '';

    fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        ingredients: pantry,
        diets: f.diets,
        equipment: f.equipment,
        maxMinutes: f.maxMinutes,
        skill: f.skill,
        exclude: curatedNames()
      })
    }).then(function (r) {
      // On a host without serverless functions (GitHub Pages, a plain static
      // server) this request never reaches our function: the status is 404/405/
      // 501 and the body is an HTML error page. Detect that by content type
      // rather than by status alone, so we report it honestly instead of
      // failing with a JSON parse error on the HTML.
      var ct = r.headers.get('content-type') || '';
      if (ct.indexOf('application/json') === -1) {
        throw new Error('not-deployed');
      }
      return r.json().then(function (body) {
        if (!r.ok) throw new Error(body.error || 'Request failed.');
        return body;
      });
    }).then(function (body) {
      if (body.refused) {
        setStatus('That request was declined. Try a different combination.', 'warn');
        return;
      }
      setStatus('', '');
      render(body.suggestions || []);
    }).catch(function (err) {
      if (err.message === 'not-deployed') {
        setStatus('AI suggestions are not available on this deployment yet.', 'warn');
      } else {
        setStatus(err.message || 'Could not reach the suggestion service.', 'warn');
      }
    }).then(function () {
      btn.disabled = false;
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var btn = el('ai-ask');
    if (!btn) return;
    btn.addEventListener('click', function () { ask(btn); });
  });
})();
