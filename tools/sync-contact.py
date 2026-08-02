#!/usr/bin/env python3
"""Point every "get in touch" on the site at the feedback form.

    python3 tools/sync-contact.py

sync-chrome.py owns the nav and the footer's cuisine columns. It never owned
the footer's first column, so the contact line there was copied by hand and
then drifted: 680 pages ended up publishing a personal gmail address.

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

hello@khaana.com survives in exactly one place, the fallback on the form page
for anyone whose browser will not run the embed. That is a fallback, not a
second route, and keeping it to one page also keeps the address off 677 pages
of harvestable HTML.

Idempotent, so it is safe to re-run after any build step that restamps the
footer. Run after sync-chrome.py and before version-assets.py.
"""
import glob, html, os, re, sys
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ADDRESS = "hello@khaana.com"
FORM = "feedback.html"

# Redirect stubs: no chrome, nothing to contact us about.
SKIP = {"south-indian.html", "himachali.html"}
# The form page keeps its own fallback address, so it is not rewritten.
KEEPS_ADDRESS = {"feedback.html"}


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

CREDIT_RE = re.compile(r'(<div class="credit-line">)(.*?)(</div>)', re.S)
EXISTING_FEEDBACK_RE = re.compile(r'\s*&middot;\s*<a href="[^"]*">Send feedback</a>')

# Any remaining mailto, wherever it sits in the prose, keeping its link text.
PROSE_MAILTO_RE = re.compile(r'<a href="mailto:[^"]*">(.*?)</a>', re.S)


def rewrite(path, rel, up):
    src = open(path, encoding="utf-8").read()
    out = src
    href = form_href(rel, up)

    # The footer's contact line goes entirely; the credit line below carries
    # the one link.
    out = CONTACT_RE.sub("", out, count=1)

    if os.path.basename(path) not in KEEPS_ADDRESS:
        out = out.replace("strategychoice1@gmail.com", ADDRESS)
        out = PROSE_MAILTO_RE.sub(
            lambda m: '<a href="%s">%s</a>' % (href, m.group(1)), out)

    link = '<a href="%s">Send feedback</a>' % href

    def credit(m):
        inner = EXISTING_FEEDBACK_RE.sub("", m.group(2))
        return m.group(1) + inner + " &middot; " + link + m.group(3)

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

    # A mailto anywhere but the form page means a second route crept back in.
    strays = []
    for path, rel, _ in pages:
        if os.path.basename(path) in KEEPS_ADDRESS:
            continue
        if "mailto:" in open(path, encoding="utf-8").read():
            strays.append(rel)

    print("contact synced on %d of %d pages" % (changed, len(pages)))
    print("   every route -> %s" % FORM)
    if strays:
        print("   ! %d pages still offer a mailto: %s"
              % (len(strays), ", ".join(strays[:5])))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
