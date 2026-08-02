/* Mobile layout audit, run in the browser console against a served page.

   Written after a fourth mobile bug in a row got found by eye rather than by
   checking. Each of them was one of a small number of shapes:

     - content overflowing its own box, because something has a max-height and
       overflow left at visible (that is what put 436px of pantry checkboxes
       through the bottom of the white panel)
     - something wider than the viewport, giving the page a sideways scroll
     - two things drawn on top of each other
     - a tap target too small to hit, under about 40px
     - text under about 12px

   window.khaanaAudit() returns them all. It reports what it found and where,
   and stays quiet about everything else. */
window.khaanaAudit = function () {
  var vw = window.innerWidth, doc = document.documentElement;
  var out = {viewport: vw + 'x' + window.innerHeight, problems: []};
  var add = function (kind, el, detail) {
    out.problems.push({
      kind: kind,
      el: el.tagName.toLowerCase() +
          (el.id ? '#' + el.id : '') +
          (el.className && el.className.toString
            ? '.' + el.className.toString().trim().split(/\s+/).slice(0, 2).join('.')
            : ''),
      detail: detail
    });
  };

  if (doc.scrollWidth > doc.clientWidth + 1) {
    out.problems.push({kind: 'page scrolls sideways',
                       detail: doc.scrollWidth + ' > ' + doc.clientWidth});
  }

  // Things drawn on top of each other. Only checked for absolutely
  // positioned overlays against the text they can cover, because a general
  // pairwise test flags every parent against its own children. This is the
  // check that would have caught the hero word mark sitting over 29% of the
  // home page paragraph on a phone.
  var floats = document.querySelectorAll(
    '.hero-wordmark, .match-pct, [style*="position:absolute"], [style*="position: absolute"]');
  var texts = document.querySelectorAll('h1, h2, h3, p, li');
  var area = function (a, b) {
    return Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) *
           Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
  };
  for (var f = 0; f < floats.length; f++) {
    var fr = floats[f].getBoundingClientRect();
    if (!fr.width || getComputedStyle(floats[f]).display === 'none') continue;
    for (var t = 0; t < texts.length; t++) {
      if (floats[f].contains(texts[t]) || texts[t].contains(floats[f])) continue;
      // The rendered text, not the element box. A block-level <h1> spans the
      // whole container even when the word in it is 227px wide, so measuring
      // the box reported the home page word mark as covering 23% of the
      // headline when it was not touching a letter.
      if (!texts[t].textContent.trim()) continue;
      var range = document.createRange();
      range.selectNodeContents(texts[t]);
      var tr = range.getBoundingClientRect();
      if (!tr.width || !tr.height) continue;
      var covered = area(fr, tr) / (tr.width * tr.height);
      if (covered > 0.06) {
        add('covers text', floats[f],
            Math.round(covered * 100) + '% of <' + texts[t].tagName.toLowerCase() + '> "' +
            texts[t].textContent.trim().slice(0, 30) + '"');
      }
    }
  }

  var all = document.querySelectorAll('body *');
  for (var i = 0; i < all.length; i++) {
    var el = all[i], r = el.getBoundingClientRect();
    if (!r.width && !r.height) continue;
    var cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;

    // content taller than its own box with nothing to scroll it
    if (cs.maxHeight !== 'none' && cs.overflowY === 'visible' &&
        el.scrollHeight > el.clientHeight + 2 && el.clientHeight > 0) {
      add('content spills out of its box', el,
          el.scrollHeight + 'px of content in ' + el.clientHeight + 'px, overflow visible');
    }

    // wider than the screen.
    //
    // Unless an ancestor scrolls horizontally on purpose. A credits table
    // that is 519px wide inside its own overflow-x:auto box is the correct
    // way to show a wide table on a phone, not a bug.
    if (r.width > vw + 1 && cs.position !== 'fixed') {
      var scroller = null, p = el.parentElement;
      while (p && p !== document.body) {
        var po = getComputedStyle(p).overflowX;
        if (po === 'auto' || po === 'scroll') { scroller = p; break; }
        p = p.parentElement;
      }
      if (!scroller) {
        add('wider than the viewport', el, Math.round(r.width) + 'px > ' + vw);
      }
    }

    // unreachably small tap target.
    //
    // Two things are deliberately not flagged. A link with a stretched
    // ::after covers its whole card, so its own box says nothing about how
    // big the target is. And a link inside a sentence cannot be 40px tall
    // without wrecking the sentence: the standard is for controls and for
    // stacked navigation, not for prose.
    // Touch sizing only applies where there is a touch. Run at 1440px this
    // check reported 217 "problems" on the Cook page, all of them checkboxes
    // that are the right size for a mouse.
    var touch = vw <= 900 || matchMedia('(pointer: coarse)').matches;
    var isControl = touch && (el.tagName === 'BUTTON' ||
        (el.tagName === 'INPUT' && /checkbox|radio|submit/.test(el.type)));
    var isStackedNav = touch && el.tagName === 'A' &&
        el.parentElement && /^(LI)$/.test(el.parentElement.tagName);
    if ((isControl || isStackedNav) && r.width > 0 && (r.height < 24 || r.width < 24)) {
      var stretched = getComputedStyle(el, '::after').position === 'absolute';
      var label = el.closest('label');
      if (!stretched && (!label || label.getBoundingClientRect().height < 24)) {
        add('tap target under 24px', el, Math.round(r.width) + 'x' + Math.round(r.height));
      }
    }

    // text too small to read on a phone
    var fs = parseFloat(cs.fontSize);
    if (touch && fs && fs < 11 && el.textContent && el.textContent.trim().length > 12 &&
        el.children.length === 0) {
      add('text under 11px', el, cs.fontSize);
    }
  }
  out.touchRulesApplied = vw <= 900 || matchMedia('(pointer: coarse)').matches;
  out.ok = out.problems.length === 0;
  return out;
};
