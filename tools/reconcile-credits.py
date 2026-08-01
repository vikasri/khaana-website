#!/usr/bin/env python3
"""Establish and record attribution for every image on the site.

    python3 tools/reconcile-credits.py            # report only
    python3 tools/reconcile-credits.py --write    # identify, then write

Attribution was being kept in two places that had drifted apart: CREDITS.md
(hand-maintained) and assets/images/credits.json (written by an early fetch
script). Seventeen images appeared in neither, so the site was publishing
CC BY-SA photos with no credit line — which the licence does not allow.

Seven of those were recovered from tools/_fetched_images.json, a manifest that
was committed and later deleted; git still has it. The rest have to be
identified from the pixels.

Identification works by perceptual hash. The local file is a resized,
re-encoded copy of a Commons original, so the bytes differ and the dimensions
differ, but a dHash survives both: reduce to 9x8 greyscale, compare each pixel
with its right-hand neighbour, and read the 64 comparisons as a fingerprint.
Two encodings of the same photograph land within a few bits of each other,
while different photographs of the same dish do not come close.

A candidate is accepted only under DIST_ACCEPT. Anything looser would risk
attributing a photograph to the wrong author, which is worse than recording
nothing, so unmatched files are reported rather than guessed at.

After --write, credits.json is the single source of truth and CREDITS.md is
generated from it by tools/build-credits.py.
"""
import io, json, os, re, subprocess, sys, time
import urllib.parse, urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "assets", "images")
CREDITS_JSON = os.path.join(IMG_DIR, "credits.json")
API = "https://commons.wikimedia.org/w/api.php"
UA = "KhaanaSiteBot/1.0 (https://khaana.com; strategychoice1@gmail.com)"

# Same licence policy as tools/fetch-images.py.
OK_LICENCE = re.compile(r"^(cc0|public domain|cc by(-sa)?[\s-]|cc by(-sa)?$)", re.I)
BAD_LICENCE = re.compile(r"(\bnc\b|non[- ]commercial|\bnd\b|no[- ]deriv|fair use)", re.I)

# 64-bit dHash. Same photo re-encoded lands at 0-6; a different photo of the
# same dish is typically 20+. 10 leaves headroom for the resize without
# reaching into territory where two dishes could collide.
DIST_ACCEPT = 10


def get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def dhash(data_or_path):
    im = (Image.open(data_or_path) if isinstance(data_or_path, str)
          else Image.open(io.BytesIO(data_or_path)))
    im = im.convert("L").resize((9, 8), Image.LANCZOS)
    px = list(im.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            left = px[row * 9 + col]
            right = px[row * 9 + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return bits


def dist(a, b):
    return bin(a ^ b).count("1")


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def search(term, limit=12):
    q = urllib.parse.urlencode({
        "action": "query", "generator": "search",
        "gsrsearch": "filetype:bitmap " + term, "gsrnamespace": "6",
        "gsrlimit": str(limit), "prop": "imageinfo",
        "iiprop": "url|extmetadata|size", "iiurlwidth": "640", "format": "json",
    })
    data = json.loads(get(API + "?" + q))
    pages = (data.get("query") or {}).get("pages") or {}
    return sorted(pages.values(), key=lambda p: p.get("index", 999))


def meta_of(page):
    ii = (page.get("imageinfo") or [{}])[0]
    m = ii.get("extmetadata", {})
    lic = ((m.get("LicenseShortName", {}) or {}).get("value", "") or "").strip()
    return {
        "title": page.get("title", ""),
        "thumb": ii.get("thumburl") or ii.get("url"),
        "license": lic,
        "artist": strip_html((m.get("Artist", {}) or {}).get("value", "")) or "Unknown",
        "source_url": ii.get("descriptionurl", ""),
    }


def recover_from_git():
    """The deleted fetch manifest, keyed by the alt text it recorded."""
    out = {}
    shas = subprocess.run(["git", "log", "--all", "--format=%H", "--",
                           "tools/_fetched_images.json"],
                          cwd=ROOT, capture_output=True, text=True).stdout.split()
    for sha in shas:
        blob = subprocess.run(["git", "show", "%s:tools/_fetched_images.json" % sha],
                              cwd=ROOT, capture_output=True, text=True).stdout
        try:
            for v in json.loads(blob).values():
                if v.get("alt"):
                    out.setdefault(v["alt"].strip().lower(), v)
        except Exception:
            continue
    return out


def short(alt):
    """The dish name at the front of an alt string.

    Alt text is written for a reader ("Pesarattu, the green gram crepe of
    coastal Andhra"), and Commons search takes that whole sentence literally
    and returns nothing. Everything before the first comma is the dish."""
    return re.split(r"[,:;(]", alt)[0].strip()


def subjects():
    """What each image shows, read from the alt text on the page using it."""
    out = {}
    for name in os.listdir(ROOT):
        if not name.endswith(".html"):
            continue
        s = open(os.path.join(ROOT, name), encoding="utf-8").read()
        for m in re.finditer(r'<img src="assets/images/([^"]+)"[^>]*?alt="([^"]*)"', s):
            out.setdefault(m.group(1), m.group(2))
    return out


def main(write=False):
    credits = {e["file"]: e for e in json.load(open(CREDITS_JSON, encoding="utf-8"))}
    md = open(os.path.join(ROOT, "CREDITS.md"), encoding="utf-8").read()
    subj = subjects()
    recovered = recover_from_git()

    files = sorted(f for f in os.listdir(IMG_DIR) if f.lower().endswith(".jpg"))
    gap = [f for f in files
           if f not in credits and ("assets/images/" + f) not in md]

    print("images: %d | already attributed: %d | to establish: %d\n"
          % (len(files), len(files) - len(gap), len(gap)))

    resolved, unresolved = {}, []

    for f in gap:
        alt = (subj.get(f) or "").strip()
        # 1. the recovered manifest, matched on the alt text it stored
        # Match on the dish name, since the manifest stored "Kedgeree" while
        # the page says "Kedgeree, rice with flaked fish and egg".
        key = short(alt).lower()
        hit = recovered.get(alt.lower()) or recovered.get(key)
        if not hit:
            for k, v in recovered.items():
                if k and (k.startswith(key) or key.startswith(k)):
                    hit = v
                    break
        if hit:
            resolved[f] = {
                "file": f, "subject": alt, "license": hit.get("license", ""),
                "artist": hit.get("credit", ""), "source_url": hit.get("sourceUrl", ""),
                "how": "recovered from deleted git manifest",
            }
            print("  git   %-24s %-34s %s" % (f, alt[:34], hit.get("license")))
            continue

        # 2. identify by perceptual hash against Commons search results
        if not alt:
            unresolved.append((f, "no alt text to search on"))
            continue
        try:
            local = dhash(os.path.join(IMG_DIR, f))
        except Exception as e:
            unresolved.append((f, "unreadable: %s" % e))
            continue

        best, best_d = None, 99
        try:
            for page in search(short(alt) or alt):
                m = meta_of(page)
                if not m["thumb"]:
                    continue
                try:
                    d = dist(local, dhash(get(m["thumb"])))
                except Exception:
                    continue
                if d < best_d:
                    best, best_d = m, d
                if best_d == 0:
                    break
                time.sleep(0.2)
        except Exception as e:
            unresolved.append((f, "search failed: %s" % e))
            continue

        if best and best_d <= DIST_ACCEPT:
            bad = BAD_LICENCE.search(best["license"]) or not OK_LICENCE.search(best["license"])
            resolved[f] = {
                "file": f, "subject": alt, "license": best["license"],
                "artist": best["artist"][:80], "source_url": best["source_url"],
                "how": "identified by perceptual hash (distance %d)" % best_d,
                "licence_review_needed": bool(bad),
            }
            flag = "  <-- LICENCE NOT IN THE ALLOWED SET" if bad else ""
            print("  hash  %-24s %-34s %-16s d=%-2d %s%s"
                  % (f, alt[:34], best["license"], best_d, best["artist"][:24], flag))
        else:
            unresolved.append((f, "no Commons match (closest distance %s)" % best_d))
        time.sleep(0.4)

    print("\nestablished: %d | still unattributed: %d" % (len(resolved), len(unresolved)))
    for f, why in unresolved:
        print("   ? %-24s %s" % (f, why))

    json.dump(resolved, open(os.path.join(ROOT, "tools", "_resolved_credits.json"), "w"),
              indent=2, ensure_ascii=False)
    print("\nwrote tools/_resolved_credits.json")

    if write and resolved:
        rows = list(json.load(open(CREDITS_JSON, encoding="utf-8")))
        have = {r["file"] for r in rows}
        for f, r in resolved.items():
            if f in have:
                continue
            rows.append({
                "file": f, "region": f.split("-")[0], "slot": "gallery" if "-g" in f else "hero",
                "wiki_title": r["subject"], "source_url": r["source_url"],
                "license": r["license"], "artist": r["artist"],
                "note": r["how"],
            })
        json.dump(rows, open(CREDITS_JSON, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        print("credits.json now holds %d entries" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main("--write" in sys.argv))
