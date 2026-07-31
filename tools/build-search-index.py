#!/usr/bin/env python3
"""Build data/search-index.json from the site's own pages.

khaana.com is static, so site search needs a prebuilt index. Run this whenever
page copy or the recipe database changes:

    python3 tools/build-search-index.py

Header, nav and footer are stripped before indexing. That matters more than it
looks: every page lists all thirteen cuisines in its nav, so indexing raw HTML
would make every page match every cuisine name and the results would be noise.
"""

import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "search-index.json")

# Pages that are navigation rather than content.
#   recipe.html  — a shell filled in from recipes.json; the recipes are indexed
#                  from that database instead.
#   index.html   — carries a blurb for all thirteen cuisines, so it matches
#                  almost every query. Offering the home page as a search result
#                  to someone standing on it is pure noise.
SKIP = {"recipe.html", "index.html"}

# Strip whole blocks whose text is chrome, not content.
BLOCK_RE = re.compile(
    r"<(header|footer|nav|script|style|noscript)\b.*?</\1\s*>", re.S | re.I
)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")

MAX_TEXT = 6000  # per page, keeps the index small enough to ship to the browser


def visible_text(markup: str) -> str:
    markup = BLOCK_RE.sub(" ", markup)
    markup = re.sub(r"<!--.*?-->", " ", markup, flags=re.S)
    text = TAG_RE.sub(" ", markup)
    return WS_RE.sub(" ", html.unescape(text)).strip()


def first(pattern, markup, default=""):
    m = re.search(pattern, markup, re.S | re.I)
    return WS_RE.sub(" ", html.unescape(TAG_RE.sub("", m.group(1)))).strip() if m else default


def build():
    entries = []

    for name in sorted(os.listdir(ROOT)):
        if not name.endswith(".html") or name in SKIP:
            continue
        markup = open(os.path.join(ROOT, name), encoding="utf-8").read()

        title = first(r"<title>(.*?)</title>", markup, name)
        title = title.split("|")[0].strip() or name
        heading = first(r"<h1[^>]*>(.*?)</h1>", markup) or title
        desc = first(r'<meta name="description" content="([^"]*)"', markup)
        body = visible_text(markup)[:MAX_TEXT]

        if name == "index.html":
            kind, label = "page", "Home"
        elif name == "cook.html":
            kind, label = "page", "Cook with what you have"
        else:
            kind, label = "cuisine", heading

        entries.append({
            "title": label,
            "url": name,
            "kind": kind,
            "snippet": desc or body[:160],
            "text": (label + " " + title + " " + desc + " " + body).lower(),
        })

    # Recipes come from the curated database, not from scraped markup.
    recipes_path = os.path.join(ROOT, "data", "recipes.json")
    recipes = json.load(open(recipes_path, encoding="utf-8"))["recipes"]
    pantry = json.load(open(os.path.join(ROOT, "data", "pantry.json"), encoding="utf-8"))
    names = {}
    for cat in pantry["categories"]:
        for item in cat["items"]:
            names[item["id"]] = item["name"]

    for r in recipes:
        ingredients = " ".join(names.get(i["id"], i["id"].replace("-", " "))
                               for i in r["ingredients"])
        steps = " ".join(s["text"] for s in r["steps"])
        entries.append({
            "title": r["name"],
            "url": "recipe.html?id=" + r["id"],
            "kind": "recipe",
            "region": r["region"],
            "snippet": r["subtitle"],
            "text": " ".join([
                r["name"], r["region"], r["subtitle"],
                " ".join(r["tags"]), ingredients, steps,
            ]).lower(),
        })

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"entries": entries}, fh, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(OUT)
    kinds = {}
    for e in entries:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print("wrote %s (%.1f KB)" % (os.path.relpath(OUT, ROOT), size / 1024))
    print("entries:", ", ".join("%s=%d" % kv for kv in sorted(kinds.items())))
    return 0


if __name__ == "__main__":
    sys.exit(build())
