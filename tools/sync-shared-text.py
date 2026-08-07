#!/usr/bin/env python3
"""Stamp the shared copy from site_text.py into every hand-written page.

    python3 tools/sync-shared-text.py

sync-chrome.py owns the nav and the footer's cuisine columns. This owns the
words inside them, and everywhere else a sentence from site_text.py appears in
a page that is not generated: the footer tagline, the feedback link, and any
region marked <!-- text:name --> ... <!-- /text:name --> in the HTML.

Nothing owned the footer's first column before, which is exactly how it
drifted. 680 pages ended up publishing a personal gmail address, and the
heading above it read "Khaana" on recipe pages and "Khaana (Hindi for Food)"
on the root pages.

There is one way to reach us and it is the form. Offering an address as well
made the reader choose between two routes to the same inbox, and the two are
not equivalent: a mailto hands them a blank draft in whatever mail client the
machine happens to open, which on a shared or work computer is often the
wrong account or none at all. So the address comes off the pages entirely and
the form takes every route:

  credit line     "Send feedback", carrying the page it was reached from
  About, Credits  the prose invitations to report a mistake

The page matters. "The picture is wrong" is not actionable across 651
recipes; the same note carrying its own URL is. Each link passes ?from=, and
the form reads it back.

No address anywhere. There is no mailbox on the domain, and a mailto naming
one that does not exist is worse than no link at all: it looks like a working
route and silently goes nowhere. The form needs no mailbox, since it posts to
Google, so the site does not need one either. If a real mailbox ever exists,
the place for it is here and nowhere else.

Idempotent, so it is safe to re-run after any build step that restamps the
footer. Run after sync-chrome.py and before version-assets.py.
"""
import glob, html, os, re, sys

import site_text as T
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FORM = "feedback.html"

# Redirect stubs: no chrome, nothing to contact us about.
SKIP = {"south-indian.html", "himachali.html", "recipe.html"}


def form_href(rel, up):
    """The form, told which page it was reached from.

    ?from= is a path, and the form rebuilds it against its own origin rather
    than trusting it, so this is a hint and not an instruction.
    """
    return html.escape("%s%s?from=%s" % (up, FORM, quote("/" + rel)), quote=True)


# The contact paragraph in the footer's first column, however it currently
# reads. Matched on the wrapper rather than the wording so a reworded line is
# still found and removed.
CONTACT_RE = re.compile(
    r'\s*<p style="max-width:280px; font-size:0\.9rem; margin-top:12px;">.*?</p>', re.S)

TAGLINE_RE = re.compile(
    r'(<p style="max-width:280px; font-size:0\.97rem;">)(.*?)(</p>)', re.S)

# A marked region in hand-written HTML, so the wording can change in
# site_text.py without this tool having to recognise the old wording.
MARKED_RE = re.compile(
    r'(<!-- text:([a-z-]+) -->)(.*?)(<!-- /text:\2 -->)', re.S)
MARKED = {"disclaimer-use": lambda: "<p>%s</p>" % T.DISCLAIMER_USE}

CREDIT_RE = re.compile(r'(<div class="credit-line">)(.*?)(</div>)', re.S)
EXISTING_FEEDBACK_RE = re.compile(
    r'\s*&middot;\s*<a href="[^"]*">' + re.escape(T.FEEDBACK_LINK) + r'</a>')

# Any remaining mailto, wherever it sits in the prose, keeping its link text.
PROSE_MAILTO_RE = re.compile(r'<a href="mailto:[^"]*">(.*?)</a>', re.S)


def rewrite(path, rel, up):
    src = open(path, encoding="utf-8").read()
    out = src
    href = form_href(rel, up)

    # The footer's contact line goes entirely; the credit line below carries
    # the one link.
    out = CONTACT_RE.sub("", out, count=1)

    out = PROSE_MAILTO_RE.sub(
        lambda m: '<a href="%s">%s</a>' % (href, m.group(1)), out)

    out = TAGLINE_RE.sub(lambda m: m.group(1) + T.BRAND_TAGLINE + m.group(3), out, count=1)
    out = MARKED_RE.sub(
        lambda m: m.group(1) + MARKED[m.group(2)]() + m.group(4)
        if m.group(2) in MARKED else m.group(0), out)

    link = '<a href="%s">%s</a>' % (href, T.FEEDBACK_LINK)

    # The whole credit line, written from one definition rather than patched.
    # It carries the copyright notice and the Terms link now, and those have to
    # read the same on all 660-odd pages or the notice is worth nothing.
    def credit(m):
        return m.group(1) + " &middot; ".join([
            T.COPYRIGHT,
            '<a href="%sterms.html">Terms</a>' % up,
            '<a href="%sabout.html">About &amp; disclaimers</a>' % up,
            '<a href="%scredits.html">Image credits</a>' % up,
            link,
        ]) + m.group(3)

    out = CREDIT_RE.sub(credit, out, count=1)

    if out == src:
        return False
    open(path, "w", encoding="utf-8").write(out)
    return True


def main():
    pages = []
    for path in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        if os.path.basename(path) not in SKIP:
            pages.append((path, os.path.basename(path), ""))
    for path in sorted(glob.glob(os.path.join(ROOT, "recipes", "*.html"))):
        pages.append((path, "recipes/" + os.path.basename(path), "../"))

    changed = sum(1 for path, rel, up in pages if rewrite(path, rel, up))

    # A mailto anywhere means a route to a mailbox that does not exist.
    strays = [rel for path, rel, _ in pages
              if "mailto:" in open(path, encoding="utf-8").read()]

    print("contact synced on %d of %d pages" % (changed, len(pages)))
    print("   every route -> %s" % FORM)
    if strays:
        print("   ! %d pages offer a mailto to a mailbox that does not exist: %s"
              % (len(strays), ", ".join(strays[:5])))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
