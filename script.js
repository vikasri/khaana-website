document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
    });
  }
});


/* The sticky header wraps to two or three lines depending on width, so anything
   that needs to sit directly below it cannot hard-code an offset. Publish the
   measured height and let CSS use it. */
(function () {
  var header = document.querySelector('.site-header');
  if (!header) return;
  function publish() {
    document.documentElement.style.setProperty(
      '--header-h', Math.round(header.getBoundingClientRect().height) + 'px');
  }
  publish();
  window.addEventListener('resize', publish);
  window.addEventListener('load', publish);
})();


/* Reveal the rest of a cuisine's recipes. The tiles are already in the page,
   so this only drops the hidden attribute; nothing is fetched. */
(function () {
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest && ev.target.closest('.show-more-recipes');
    if (!b) return;
    var wrap = b.parentNode.querySelector('.recipe-tiles');
    if (!wrap) return;
    wrap.querySelectorAll('.recipe-tile.is-extra').forEach(function (t) { t.hidden = false; });
    b.setAttribute('aria-expanded', 'true');
    b.remove();
  });
})();


/* Fold an optional postcode into the Maps search. The link already works
   without it, using whatever location the device reports, so this only
   rewrites the href at the moment of clicking. Nothing is stored or sent
   anywhere else. */
(function () {
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('.eat-out-btn');
    if (!a) return;
    var box = document.getElementById('eat-out-where');
    var where = box ? box.value.trim() : '';
    // The search phrase is built by tools/build-cuisine-recipes.py and carried
    // in data-query, so the typed-postcode path and the plain href ask Maps
    // for exactly the same thing. Composing it here from the region name is
    // what produced "Pahari restaurant" and a list of nearby pizza.
    var q = a.getAttribute('data-query') || '';
    if (!q) return;
    // "near <place>" rather than a bare append. Maps reads it as a centre to
    // search around and will reach well past the town for a match, where a
    // trailing place name reads as part of the business name and narrows it.
    if (where) q += ' near ' + where;
    // Google's api=1 search form. It opens in the browser wherever the app
    // is absent, iPhone included, which is why the Apple Maps link that used
    // to sit alongside was removed rather than kept as a fallback.
    a.href = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(q);
  });
})();


/* The Cuisines menu. Click to open, click away or press Escape to close. */
(function () {
  document.addEventListener('click', function (ev) {
    var t = ev.target.closest && ev.target.closest('.nav-cuisines-toggle');
    var open = document.querySelector('.nav-cuisines.open');
    if (t) {
      var li = t.parentNode;
      var wasOpen = li.classList.contains('open');
      if (open) { open.classList.remove('open');
                  open.querySelector('.nav-cuisines-toggle').setAttribute('aria-expanded', 'false'); }
      if (!wasOpen) { li.classList.add('open'); t.setAttribute('aria-expanded', 'true'); }
      ev.preventDefault();
      return;
    }
    if (open && !ev.target.closest('.nav-dropdown')) {
      open.classList.remove('open');
      open.querySelector('.nav-cuisines-toggle').setAttribute('aria-expanded', 'false');
    }
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape') return;
    var open = document.querySelector('.nav-cuisines.open');
    if (!open) return;
    open.classList.remove('open');
    var b = open.querySelector('.nav-cuisines-toggle');
    b.setAttribute('aria-expanded', 'false');
    b.focus();
  });
})();
