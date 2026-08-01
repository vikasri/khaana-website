#!/usr/bin/env python3
"""Footnote the checkable claims on each cuisine page.

    python3 tools/build-sources.py

The history sections state things that can be right or wrong: a date, an
etymology, who invented what. Anyone can verify those, and until now nobody
could see where they came from.

Only load-bearing claims are marked. A date, a derivation, a named inventor,
a legal event. Not "the food is rich", not anything a reader can taste for
themselves. Two or three per page, no more, so the prose still reads as prose.

Every source here was opened and read, and the claim on the page was checked
against it before the marker went in. Doing this turned up one error of mine:
the Bara Imambara relief works began in the famine of 1780 and finished in
1784, and the page had put the famine in 1784. Fixed in the prose.

Where the history itself is uncertain the note says so rather than lending it
a citation it does not deserve. The wazwan entry is the clear case: the Timur
story is the usual account and rests on oral tradition, not documents.

Idempotent: existing markers and the sources block are stripped and rebuilt.
"""
import glob, html, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = "https://en.wikipedia.org/wiki/"

# page -> [(anchor, note, url)]
# anchor: text from the page; the marker goes immediately after it. Matched
# with flexible whitespace so the HTML can wrap and indent however it likes.
# note: what the source establishes, in the fewest words that stay honest.
SOURCES = {
    "andhra.html": [
        ("Chilli reached India with Portuguese traders in the sixteenth century",
         "Chillies reached Asia with Portuguese and Spanish traders in the 16th century, Goa among the entry points.", W + "Chili_pepper"),
        ("a separate state since 2014",
         "Telangana was formed on 2 June 2014.", W + "Telangana"),
    ],
    "anglo-indian.html": [
        ("The nominated seats lapsed in January 2020 under the 104th Amendment",
         "The reserved Anglo-Indian seats ended in January 2020 under the 104th Amendment.", W + "Anglo-Indian"),
        ("founded in 1933 in what is now Jharkhand by Ernest Timothy McCluskie",
         "Founded 1933 as a homeland for Anglo-Indians.", W + "McCluskieganj"),
    ],
    "awadhi-lucknowi.html": [
        ("until the British annexed it in 1856",
         "Nawabs ruled Awadh from 1720; the East India Company annexed it in 1856.", W + "Awadh"),
        ("commissioned the Bara Imambara as a relief-work project",
         "Building began in the famine year of 1780 to provide employment, and finished in 1784.", W + "Bara_Imambara"),
    ],
    "bengali.html": [
        ("credited to Kolkata confectioner Nobin Chandra Das around 1868",
         "Usually credited to Nobin Chandra Das in 1868, though earlier claims exist.", W + "Rasgulla"),
        ("As the capital of British India until 1911",
         "The capital moved to New Delhi in 1911.", W + "Kolkata"),
    ],
    "bihari.html": [
        ("received a GI tag in 2022",
         "Mithila Makhana was granted its GI tag in 2022.", W + "Mithila_Makhana"),
    ],
    "goan.html": [
        ("roughly 450 years",
         "Albuquerque took Goa in 1510; Portuguese rule ended in December 1961.", W + "Portuguese_India"),
        ("meat marinated in wine (<em>vinho</em>) and garlic (<em>alhos</em>)",
         "From carne de vinha d'alhos; Goan cooks substituted palm vinegar for the wine and added chilli.", W + "Vindaloo"),
    ],
    "gujarati.html": [
        ("one of the Indus Valley Civilization's key port cities",
         "A southern Indus Valley site on the Gujarat coast. Whether its brick basin was a dock is still argued.", W + "Lothal"),
        ("busiest trade hubs by the 17th century",
         "Described as the most prosperous port of the Mughal empire, declining through the 18th century.", W + "Surat"),
    ],
    "hyderabadi.html": [
        ("founded the city of Hyderabad in 1591",
         "Golconda established 1518; Hyderabad founded under Muhammad Quli Qutb Shah.", W + "Qutb_Shahi_dynasty"),
        ("after an eight-month siege",
         "28 January to 22 September 1687.", W + "Siege_of_Golconda"),
        ("declared himself independent in 1724",
         "Asaf Jah I broke from the Mughals and founded the Asaf Jahi line.", W + "Hyderabad_State"),
    ],
    "indo-chinese.html": [
        ("granted land south of Calcutta around 1778",
         "Yang Tai Chow, also called Tong Achew, arrived in 1778 and was granted land by Warren Hastings.", W + "Chinese_community_in_Kolkata"),
        ("held at an internment camp at Deoli in Rajasthan",
         "An estimated 10,000 were detained at Deoli; the last were released in mid-1967.", W + "Chinese_community_in_Kolkata"),
    ],
    "karnataka.html": [
        ("the Coorg province",
         "Mysore State was enlarged in 1956 with Coorg and the Kannada-speaking districts of Madras, Bombay and Hyderabad.", W + "States_Reorganisation_Act,_1956"),
        ("founded by the philosopher Madhvacharya in the thirteenth century",
         "Founded by Madhvacharya in the 13th century; the Ashta Mathas rotate temple duty.", W + "Udupi_Sri_Krishna_Matha"),
    ],
    "kashmiri.html": [
        ("brought Central Asian and Persian cooks, the wazas, into the valley",
         "This is the usual account rather than a documented one: it rests on oral tradition, and an Iranian origin is also argued.", W + "Wazwan"),
    ],
    "kerala.html": [
        ("when Vasco da Gama landed at Kozhikode (Calicut) in search of pepper",
         "Landed near Kozhikode on 20 May 1498, opening the sea route from Europe.", W + "Vasco_da_Gama"),
    ],
    "maharashtrian.html": [
        ("built under Chhatrapati Shivaji in the 17th century",
         "Shivaji founded the Maratha state and was crowned Chhatrapati in 1674.", W + "Maratha_Empire"),
        ("credited to a street vendor named Ashok Vaidya",
         "Credited with the first vada pav stall outside Dadar station in 1966.", W + "Vada_pav"),
    ],
    "northeast-indian.html": [
        ("from 2007 to 2011",
         "Certified hottest in 2007, superseded by the Trinidad Scorpion Butch T in 2011.", W + "Bhut_jolokia"),
    ],
    "odia.html": [
        ('two years after West Bengal secured one for "Banglar Rosogolla."',
         "West Bengal was granted its GI on 14 November 2017, Odisha on 29 July 2019.", W + "Rasgulla"),
    ],
    "pahari.html": [
        ("carved out of Uttar Pradesh only in 2000",
         "Became the 27th state of India on 9 November 2000.", W + "Uttarakhand"),
    ],
    "parsi.html": [
        ("a Persian narrative poem written down in 1599",
         "Composed 1599 by the priest Bahman Kaikobad; it records the asylum granted by Jadi Rana and its conditions.", W + "Qissa-i_Sanjan"),
    ],
    "punjabi.html": [
        ("came in 1947",
         "Punjab was one of the two provinces partitioned outright.", W + "Partition_of_India"),
        ("credited to Kundan Lal Gujral of Delhi's Moti Mahal restaurant",
         "Founded in Delhi in 1947 by Gujral and partners, who left Peshawar at partition.", W + "Moti_Mahal_(restaurant)"),
    ],
    "rajasthani.html": [
        ("Fresh vegetables were historically scarce and water was precious",
         "Scarcity of water and green vegetables shaped the cooking; food that kept for days was preferred.", W + "Rajasthani_cuisine"),
    ],
    "sindhi.html": [
        ("Partition cut Sindh away whole",
         "Punjab and Bengal were divided; Sindh passed to Pakistan without being partitioned.", W + "Partition_of_India"),
    ],
    "tamil-nadu.html": [
        ("from the tenth century onward",
         "Iddalige appears in the Kannada Vaddaradhane, about 920 CE, and as iddarika in the Manasollasa of 1130.", W + "Idli"),
        ("brought the proceeds home to mansions of Burmese teak",
         "Their banking reached Ceylon, Burma, Malaya and beyond in the 19th century; the Chettinad mansions date from the late 18th to early 20th.", W + "Nattukottai_Chettiar"),
    ],
}

MARKER = re.compile(r'<sup class="src-ref">.*?</sup>', re.S)
BLOCK = re.compile(r'\s*<div class="page-sources">.*?</div>\s*(?=</div>\s*<aside)', re.S)


def slug(page):
    return page[:-5]


def main():
    # Every page is rendered before any page is written. A bad anchor found on
    # the eleventh page would otherwise leave the first ten already footnoted
    # and the rest not, which is a worse state than either.
    pending = {}
    total = 0
    for page in sorted(SOURCES):
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            print("  ! %s not found" % page)
            return 1
        src = open(path, encoding="utf-8").read()

        # Strip previous run before matching, so anchors never hit old markup.
        src = MARKER.sub("", src)
        src = BLOCK.sub("\n        ", src)

        items = SOURCES[page]
        for i, (anchor, note, url) in enumerate(items, 1):
            pat = re.compile(r'\s+'.join(re.escape(w) for w in anchor.split()))
            hits = pat.findall(src)
            if len(hits) != 1:
                print("  ! %s claim %d: anchor matched %d times, expected 1" % (page, i, len(hits)))
                print("    %r" % anchor)
                return 1
            sup = ('<sup class="src-ref"><a href="#src-%s-%d" id="ref-%s-%d">%d</a></sup>'
                   % (slug(page), i, slug(page), i, i))
            src = pat.sub(lambda m: m.group(0) + sup, src, count=1)

        rows = "\n".join(
            '          <li id="src-%s-%d">%s <a href="%s" target="_blank" '
            'rel="noopener noreferrer">%s</a> <a class="src-back" href="#ref-%s-%d" '
            'aria-label="Back to text">&#8593;</a></li>'
            % (slug(page), i, html.escape(note), url,
               html.escape(url.rsplit("/", 1)[1].replace("_", " ")), slug(page), i)
            for i, (anchor, note, url) in enumerate(items, 1))

        block = ('\n        <div class="page-sources">\n'
                 '          <h2>Sources</h2>\n'
                 '          <ol>\n%s\n          </ol>\n'
                 '        </div>\n      ' % rows)

        # Last thing inside the prose column, before the quick-facts aside.
        m = re.search(r'(?=</div>\s*<aside)', src)
        if not m:
            print("  ! %s: no prose/aside boundary" % page)
            return 1
        src = src[:m.start()] + block + src[m.start():]

        pending[path] = src
        total += len(items)
        print("  %-24s %d sources" % (page, len(items)))

    for path, src in pending.items():
        open(path, "w", encoding="utf-8").write(src)

    print("\n%d claims footnoted across %d pages" % (total, len(SOURCES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
