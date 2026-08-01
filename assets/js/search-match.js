/* Khaana — shared query matching for the site search and the recipe search.
 *
 * Both boxes used to be a single indexOf against one concatenated string. That
 * failed three ways a reader would not forgive:
 *
 *   "chokha litti"  found nothing, because the words were the wrong way round
 *   "biriyani"      found nothing, because the site spells it biryani
 *   "mutton curry"  found nothing, because the two words are never adjacent
 *
 * Here the query is split into words and every word has to match somewhere in
 * the entry, independently of the others. Word order stops mattering, and each
 * word can land as an exact word, a prefix, a substring, a known alternative
 * spelling, or with one character wrong.
 *
 * No build step and no dependency: exposed as window.KhaanaMatch and pulled in
 * with a plain script tag ahead of whichever search uses it.
 */
(function () {
  'use strict';

  /* ---------- alternative spellings ----------
     English transliteration of Indian food is not standardised, so a reader's
     spelling and the site's are often both correct. Each row is a set of
     equals — any member matches any other — which means a new spelling is one
     word in one place rather than a pair of entries in a synonym map.

     Rows deliberately include some near-misses rather than exact synonyms
     (palak/saag, chickpea/chana). On a site this size a reader typing "saag"
     wanting spinach is better served a spinach dish than nothing. */
  var VARIANT_ROWS = [
    // dishes
    ['biryani', 'biriyani', 'biriani', 'birani', 'beriyani'],
    ['dal', 'daal', 'dhal', 'dahl', 'dhall', 'lentil', 'lentils'],
    ['paneer', 'panir'],
    ['chana', 'channa', 'chhana', 'chickpea', 'chickpeas', 'kabuli'],
    ['chole', 'chhole', 'choley', 'cholay', 'chholey'],
    ['gosht', 'ghosht', 'gosth'],
    ['keema', 'kheema', 'qeema', 'quema', 'mince'],
    ['roti', 'rotti', 'chapati', 'chapatti', 'phulka'],
    ['naan', 'nan'],
    ['puri', 'poori'],
    ['paratha', 'parantha', 'porotta', 'parotta'],
    ['bhaji', 'bhajji', 'bhajia', 'bhajiya'],
    ['pakora', 'pakoda', 'pakodi', 'fritter', 'fritters'],
    ['vada', 'wada', 'bada', 'vadai'],
    ['dosa', 'dosai', 'dose'],
    ['idli', 'idly', 'iddli'],
    ['sambar', 'sambhar', 'saambar'],
    ['rasam', 'rassam'],
    ['uttapam', 'uthappam', 'uttappam'],
    ['upma', 'uppma'],
    ['poha', 'pohe'],
    ['dhokla', 'dokla'],
    ['kadhi', 'karhi', 'kadi'],
    ['rajma', 'razma'],
    ['sabzi', 'sabji', 'subzi', 'subji'],
    ['khichdi', 'khichri', 'khichadi', 'khichuri', 'kichdi'],
    ['korma', 'kurma', 'qorma'],
    ['kofta', 'koftha'],
    ['halwa', 'halva', 'halwaa'],
    ['kheer', 'khir', 'payasam', 'payasa'],
    ['ladoo', 'laddu', 'laddoo', 'laadu'],
    ['barfi', 'burfi', 'barfee'],
    ['jalebi', 'jilebi', 'jilapi'],
    ['rasgulla', 'rosogolla', 'rasagola', 'rosgulla', 'rasagulla'],
    ['samosa', 'samoosa', 'singara'],
    ['khichuri', 'khichdi'],
    ['chutney', 'chatni', 'chutny'],
    ['achar', 'achaar', 'pickle'],
    ['pav', 'pao', 'paav'],
    ['momo', 'momos', 'dumpling', 'dumplings'],
    ['vindaloo', 'vindalho', 'vindalu'],
    ['xacuti', 'shakuti', 'xacutti'],
    ['tandoori', 'tanduri'],
    ['masala', 'masaala', 'masalla'],
    ['thali', 'thaali'],
    ['lassi', 'lassee'],
    ['tikka', 'teekka'],

    // ingredients
    ['dahi', 'curd', 'yogurt', 'yoghurt'],
    ['aloo', 'alu', 'aalu', 'potato', 'potatoes'],
    ['gobi', 'gobhi', 'cauliflower'],
    ['palak', 'saag', 'sag', 'spinach', 'greens'],
    ['methi', 'fenugreek', 'kasuri'],
    ['baingan', 'baigan', 'brinjal', 'eggplant', 'aubergine'],
    ['bhindi', 'okra', 'ladyfinger'],
    ['lauki', 'doodhi', 'ghiya'],
    ['dhania', 'coriander', 'cilantro'],
    ['jeera', 'zeera', 'cumin'],
    ['haldi', 'turmeric'],
    ['imli', 'tamarind'],
    ['nariyal', 'coconut'],
    ['mutton', 'lamb', 'goat'],
    ['prawn', 'prawns', 'shrimp', 'shrimps'],
    ['chicken', 'murgh', 'murg'],
    ['fish', 'machli', 'macher', 'meen'],
    ['egg', 'eggs', 'anda'],
    ['capsicum', 'bellpepper', 'shimla'],
    ['ghee', 'clarified'],
    ['chai', 'tea'],

    // regions and communities
    ['bengali', 'bangla', 'bangali', 'bengal'],
    ['odia', 'oriya', 'odiya', 'odisha', 'orissa'],
    ['maharashtrian', 'marathi', 'maharashtra'],
    ['karnataka', 'kannada', 'mysore', 'udupi', 'coorg'],
    ['andhra', 'telugu', 'telangana'],
    ['tamil', 'tamilnadu', 'chettinad'],
    ['kerala', 'malabar', 'malayali', 'nadan'],
    ['awadhi', 'lucknowi', 'lucknow', 'awadh'],
    ['punjabi', 'punjab'],
    ['kashmiri', 'kashmir', 'wazwan'],
    ['rajasthani', 'rajasthan', 'marwari'],
    ['gujarati', 'gujarat'],
    ['goan', 'goa', 'konkani'],
    ['hyderabadi', 'hyderabad', 'deccani'],
    ['bihari', 'bihar'],
    ['pahari', 'himachali', 'himachal', 'kumaoni', 'garhwali', 'uttarakhandi'],
    ['northeast', 'assamese', 'assam', 'naga', 'manipuri', 'khasi'],
    ['parsi', 'parsee', 'irani'],
    ['sindhi', 'sindh'],
    ['indochinese', 'manchurian', 'schezwan', 'sichuan', 'szechwan', 'szechuan'],

    // diet words a reader may type in their own words
    ['vegetarian', 'veg'],
    ['vegan', 'plantbased'],
    ['glutenfree', 'gluten'],
    ['dairyfree', 'dairy'],
    ['healthier', 'healthy', 'light']
  ];

  // token -> group id. A word may sit in more than one row (khichdi, methi),
  // in which case it carries every group it belongs to.
  var GROUPS = {};
  VARIANT_ROWS.forEach(function (row, gi) {
    row.forEach(function (w) {
      (GROUPS[w] || (GROUPS[w] = [])).push(gi);
    });
  });

  // Words that carry no signal in a recipe query and would otherwise force an
  // AND term that nothing satisfies.
  var STOP = {
    a: 1, an: 1, the: 1, of: 1, and: 1, or: 1, with: 1, without: 1, in: 1,
    on: 1, for: 1, to: 1, is: 1, how: 1, make: 1, made: 1, recipe: 1,
    recipes: 1, dish: 1, dishes: 1, food: 1, cuisine: 1, style: 1
  };

  function norm(s) {
    return String(s == null ? '' : s)
      .toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')   // café -> cafe
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
  }

  function wordsOf(s) {
    var n = norm(s);
    return n ? n.split(' ') : [];
  }

  // Crude but adequate: only the trailing plural, and only on words long enough
  // that dropping a letter cannot turn one real word into another.
  function stem(w) {
    if (w.length > 4 && w.charAt(w.length - 1) === 's' && w.charAt(w.length - 2) !== 's') {
      return w.slice(0, -1);
    }
    return w;
  }

  /* One substitution, insertion or deletion — enough for a slipped key, not so
     loose that short words all collapse into each other. Bounded and
     early-exiting rather than a full matrix, since this runs per word per
     entry on every keystroke. */
  function within1(a, b) {
    if (a === b) return true;
    var la = a.length, lb = b.length;
    if (Math.abs(la - lb) > 1) return false;
    var i = 0, j = 0, diff = 0;
    while (i < la && j < lb) {
      if (a.charAt(i) === b.charAt(j)) { i++; j++; continue; }
      if (++diff > 1) return false;
      if (la === lb) { i++; j++; }
      else if (la > lb) { i++; }
      else { j++; }
    }
    if (i < la || j < lb) diff++;
    return diff <= 1;
  }

  // Two letters swapped — "birynai" for "biryani". Levenshtein calls that two
  // edits, but it is the single commonest typing slip, so it is worth its own
  // cheap test.
  function swapped(a, b) {
    if (a.length !== b.length) return false;
    var d = [];
    for (var i = 0; i < a.length; i++) {
      if (a.charAt(i) !== b.charAt(i)) { d.push(i); if (d.length > 2) return false; }
    }
    return d.length === 2 && d[1] === d[0] + 1 &&
           a.charAt(d[0]) === b.charAt(d[1]) && a.charAt(d[1]) === b.charAt(d[0]);
  }

  function fuzzyEq(a, b) {
    // Below five characters a single edit is too much licence: "dal"/"dab",
    // "roti"/"rota". Those words are short enough to type correctly.
    if (a.length < 5 || b.length < 5) return a === b;
    return within1(a, b) || swapped(a, b);
  }

  function sameGroup(a, b) {
    var ga = GROUPS[a], gb = GROUPS[b];
    if (!ga || !gb) return false;
    for (var i = 0; i < ga.length; i++) {
      if (gb.indexOf(ga[i]) !== -1) return true;
    }
    return false;
  }

  /* ---------- public ---------- */

  /* Query -> the words that have to match. Single characters are dropped
     unless the whole query is one, so "a" in "aloo a" cannot sink the search. */
  function tokens(q) {
    var raw = wordsOf(q).filter(function (w) { return !STOP[w]; });
    var kept = raw.filter(function (w) { return w.length > 1; });
    if (!kept.length) kept = raw;
    return kept.map(function (w) {
      return { raw: w, stem: stem(w) };
    });
  }

  /* Precompute the normalised forms once per entry. Called for the whole index
     right after it loads, so no keystroke pays for it. */
  function prepare(fields) {
    var titleWords = wordsOf(fields.title);
    var strongWords = wordsOf(fields.strong || '');
    return {
      title: norm(fields.title),
      titleWords: titleWords,
      titleStems: titleWords.map(stem),
      strong: norm(fields.strong || ''),
      strongWords: strongWords,
      strongStems: strongWords.map(stem),
      body: norm(fields.body || ''),
      // Padded so a word-boundary test is a plain indexOf rather than a regex
      // built per token per entry.
      bodyPad: ' ' + norm(fields.body || '') + ' '
    };
  }

  // Best score this one word can earn against one entry. 0 means absent, and
  // because every word must earn something, 0 rejects the entry outright.
  function tokenScore(doc, t) {
    var w = t.raw, st = t.stem, i, dw, ds;

    for (i = 0; i < doc.titleWords.length; i++) {
      dw = doc.titleWords[i]; ds = doc.titleStems[i];
      // Comfortably above a prefix hit plus a phrase bonus: "dosa" must rank
      // Neer Dosa over Dosakaya Pappu, which merely starts with the letters.
      if (dw === w || ds === st) return 130;
    }
    for (i = 0; i < doc.titleWords.length; i++) {
      if (doc.titleWords[i].indexOf(w) === 0) return 80;      // partial word
    }
    if (doc.title.indexOf(w) !== -1) return 62;               // inside a word
    for (i = 0; i < doc.titleWords.length; i++) {
      if (sameGroup(doc.titleWords[i], w)) return 58;         // other spelling
    }
    for (i = 0; i < doc.titleWords.length; i++) {
      if (fuzzyEq(doc.titleWords[i], w)) return 44;           // one slip
    }

    for (i = 0; i < doc.strongWords.length; i++) {
      dw = doc.strongWords[i];
      if (dw === w || doc.strongStems[i] === st) return 34;
      if (dw.indexOf(w) === 0) return 28;
    }
    if (doc.strong.indexOf(w) !== -1) return 22;
    for (i = 0; i < doc.strongWords.length; i++) {
      if (sameGroup(doc.strongWords[i], w)) return 20;
      if (fuzzyEq(doc.strongWords[i], w)) return 16;
    }

    /* Body text is matched on word boundaries, not as a loose substring.
       "tea" used to hit every recipe saying "teaspoon", which buried Masala
       Chai under a page of unrelated dishes. Short words must match whole;
       from four characters up a word may still be completed, so "vinda"
       still finds vindaloo in a method step. */
    if (doc.body) {
      var at = doc.bodyPad.indexOf(' ' + w + ' ');
      if (at === -1 && w.length >= 4) at = doc.bodyPad.indexOf(' ' + w);
      if (at !== -1) return at < 400 ? 12 : 8;
    }
    return 0;
  }

  /* Every word must match. Returns 0 when any of them does not, so an extra
     word narrows the result set rather than widening it. */
  function score(doc, toks, phrase) {
    if (!toks.length) return 0;
    var total = 0;
    for (var i = 0; i < toks.length; i++) {
      var s = tokenScore(doc, toks[i]);
      if (s === 0) return 0;
      total += s;
    }
    // Words in the reader's order, adjacent, still beat the same words apart.
    if (phrase) {
      if (doc.title === phrase) total += 200;
      else if (doc.title.indexOf(phrase) === 0) total += 120;
      else if (doc.title.indexOf(phrase) !== -1) total += 90;
    }
    return total;
  }

  window.KhaanaMatch = {
    norm: norm,
    tokens: tokens,
    prepare: prepare,
    score: score
  };
})();
