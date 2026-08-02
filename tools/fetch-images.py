#!/usr/bin/env python3
"""Fetch freely-licensed dish photos from Wikimedia Commons.

    python3 tools/fetch-images.py "Dal tadka:dal-tadka" "Palak paneer:palak-paneer"

Each argument is "Search term:recipe-id". For every one it searches Commons,
keeps the first result under a licence that actually permits reuse, downloads a
~1200px version to assets/images/recipes/, and prints an attribution row.

Only these licences are accepted:
    CC0, public domain, CC BY (any version), CC BY-SA (any version)

NC (non-commercial) and ND (no-derivatives) are rejected outright — they are
listed on Commons but are not free for a site that may one day carry ads, and
ND forbids the cropping and resizing a responsive layout does.

The tool cannot see whether a photo actually shows the dish. Filenames and
search relevance are good but not proof, so spot-check what it downloads.
"""
import json, os, re, sys, time
import urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "images", "recipes")
API = "https://commons.wikimedia.org/w/api.php"
UA = "KhaanaSiteBot/1.0 (https://khaana.com; hello@khaana.com)"

OK_LICENCE = re.compile(r"^(cc0|public domain|cc by(-sa)?[\s-]|cc by(-sa)?$)", re.I)
BAD_LICENCE = re.compile(r"(\bnc\b|non[- ]commercial|\bnd\b|no[- ]deriv|fair use)", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def search(term, limit=6):
    q = urllib.parse.urlencode({
        "action": "query", "generator": "search",
        "gsrsearch": "filetype:bitmap " + term, "gsrnamespace": "6",
        "gsrlimit": str(limit), "prop": "imageinfo",
        "iiprop": "url|extmetadata|size", "iiurlwidth": "1200", "format": "json",
    })
    data = json.loads(get(API + "?" + q))
    pages = (data.get("query") or {}).get("pages") or {}
    # generator=search returns pages unordered; restore relevance order
    return sorted(pages.values(), key=lambda p: p.get("index", 999))


STOP = {"and", "with", "the", "of", "in", "a", "ka", "ki", "curry", "masala", "indian"}


def name_matches(term, title):
    """Reject a hit whose filename shares no meaningful word with the search term.

    Commons search is relevance-ranked, not content-verified: searching "Dal
    tadka" returned File:Ilish_Bhaat.jpg (fried hilsa) because a bowl of dal
    appears somewhere in the frame. Requiring a filename token in common kills
    that class of mismatch cheaply.
    """
    words = {w for w in re.split(r"[^a-z]+", term.lower()) if len(w) > 2 and w not in STOP}
    fname = re.split(r"[^a-z]+", title.lower())
    # Substring, not equality: Commons runs words together in filenames
    # ("Palakpaneer_Rayagada.jpg"), and an exact-token test would reject a
    # perfectly good photo. "dal" still finds nothing in "Ilish_Bhaat".
    return any(any(w in tok for tok in fname) for w in words) if words else True


def usable(page):
    ii = (page.get("imageinfo") or [{}])[0]
    meta = ii.get("extmetadata", {})
    lic = (meta.get("LicenseShortName", {}) or {}).get("value", "") or ""
    if BAD_LICENCE.search(lic) or not OK_LICENCE.search(lic.strip()):
        return None
    if not name_matches(page.get("_term", ""), page["title"]):
        return None
    return {
        "title": page["title"],
        "url": ii.get("thumburl") or ii.get("url"),
        "descurl": ii.get("descriptionurl", ""),
        "licence": lic.strip(),
        "artist": strip_html((meta.get("Artist", {}) or {}).get("value", "")) or "Unknown",
    }


def main(pairs):
    os.makedirs(OUT_DIR, exist_ok=True)
    rows, found = [], {}
    for pair in pairs:
        term, rid = pair.rsplit(":", 1)
        hit = None
        try:
            for page in search(term):
                page["_term"] = term
                hit = usable(page)
                if hit:
                    break
        except Exception as e:
            print("  ! search failed for %s: %s" % (term, e))
        if not hit:
            print("  - %-28s no freely-licensed match" % term)
            continue
        dest = os.path.join(OUT_DIR, rid + ".jpg")
        try:
            data = get(hit["url"])
        except Exception as e:
            print("  ! download failed for %s: %s" % (term, e))
            continue
        open(dest, "wb").write(data)
        found[rid] = {
            "src": "assets/images/recipes/%s.jpg" % rid,
            "alt": term,
            "credit": hit["artist"][:60],
            "license": hit["licence"],
            "sourceUrl": hit["descurl"],
        }
        rows.append("| `assets/images/recipes/%s.jpg` | %s | %s | %s | [link](%s) |"
                    % (rid, term, hit["licence"], hit["artist"][:40], hit["descurl"]))
        print("  + %-28s %-14s %-28s %.0f KB"
              % (term, hit["licence"], hit["artist"][:28], len(data) / 1024))
        time.sleep(0.5)  # be polite to Commons

    json.dump(found, open(os.path.join(ROOT, "tools", "_fetched_images.json"), "w"),
              ensure_ascii=False, indent=2)
    if rows:
        print("\n--- append to CREDITS.md ---")
        print("\n".join(rows))
    print("\nfetched %d / %d" % (len(found), len(pairs)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
