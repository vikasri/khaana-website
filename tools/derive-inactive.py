#!/usr/bin/env python3
"""Recompute every recipe's required inactive time from its own instructions.

    python3 tools/derive-inactive.py [--dry-run] [--report]

The site displayed a "Total" that was prep plus cook and nothing else. On a
recipe that soaks its beans overnight, ferments a batter for eight hours or
marinates mutton for four, that number is not the time the dish takes; it is
the time you spend standing at the stove. An audit of the live site found 137
pages where a stated inactive interval was longer than the whole advertised
total. Masala Dosa said 60 minutes against 6 hours of soaking and up to 14 of
fermentation.

So `inactiveMinutes` is derived here, the same way allergens are, from the
prose that is already on the page. Deriving it beats a hand-typed field for
the same reason: a number typed once drifts the moment someone edits the step
that justified it, and nothing complains.

What "required" means
---------------------

The MINIMUM the recipe insists on, not the longest interval it mentions.

  "Marinate for at least 1 hour, or overnight"   -> 60, not 480
  "Soak 6 hours"                                 -> 360
  "Ferment 8 to 14 hours"                        -> 480
  "Rest overnight if you can"                    -> 0, it says "if you can"

A reader planning backwards needs to know the earliest they can start, and
overstating it makes dishes look harder than they are. Where a range is given
the step itself still prints the upper end, so nothing is hidden.

What is not counted
-------------------

Prose that mentions an interval without requiring one. Nihari's note that it
"was cooked overnight on dying coals" is history. Murukku's warning that
"stored warm they go soft overnight" is storage. Saoji Mutton's "once it sits
overnight the stone flower loses its smoke" argues against waiting. All three
name an interval and none of them is a step, so IGNORE below drops the
sentence patterns that signal narration rather than instruction.

The parser is deliberately narrow and OVERRIDES carries the rest. A wrong
number here is worse than none: it goes on the page as a promise.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "recipes.json")

# An interval the cook is not standing over. "cool" and "drain" are here
# because a cake that must cool three hours before it can be cut is three
# hours you cannot serve it in, whatever else you do meanwhile.
# Imperatives and gerunds only, never the -ed participle. "Simmer the tomato
# with the soaked cashews for 20 minutes" is twenty minutes of simmering; the
# soaking already happened and belongs to an earlier step. Matching "soaked"
# there turned a cooking time into a waiting time.
INACTIVE = re.compile(
    r"\b(soaks?|soaking|ferments?|fermenting|marinates?|marinating|"
    r"rests?|resting|chills?|chilling|refrigerates?|refrigerating|"
    r"prov(?:e|es|ing)|proofs?|proofing|cures?|curing|cools?|cooling|"
    r"freez(?:e|es|ing)|set aside|setting|sets? completely|"
    r"stands?|standing|steeps?|steeping|hangs?|hanging|"
    r"sours?|souring|sprouts?|sprouting|settles?|settling|"
    r"infuses?|infusing|macerates?|macerating|"
    # "dry" only as a deliberate act. A bare \bdry\b matched "cook 15 minutes
    # until the rice is done and almost dry", which is fifteen minutes at the
    # stove and the exact opposite of an interval you can walk away from.
    r"air-dry|dry out|drying|dries|"
    r"leaves?|leave|leaving|sits?|sitting|overnight)\b", re.I)

# Sentences that name an interval without asking for one: history, storage
# advice, warnings against waiting, explicit negations, and the "serve warm,
# or chill two hours" construction where the wait is one of two endings.
IGNORE = re.compile(
    r"\b(was cooked|were cooked|traditionally|comes from|means|meaning|"
    r"not the|rather than|instead of|loses|lose|go soft|goes soft|"
    r"stale|spoil\w*|keeps?\b|stored|storage|history|historic\w*|"
    r"if you can|if you have time|is better|even better|better still|"
    r"not better|no need to|does not need|doesn't need|need not|"
    r"serve warm|serve hot)\b", re.I)

# What the interval is for, in the order we prefer to name it. First hit wins,
# so a sentence that both marinates and refrigerates is named for the
# marinade, which is the thing the cook is waiting on.
LABELS = [
    (re.compile(r"\bferment", re.I), "fermenting"),
    (re.compile(r"\bsprout", re.I), "sprouting"),
    (re.compile(r"\bmarinat|\bmarinad", re.I), "marinating"),
    (re.compile(r"\bsoak", re.I), "soaking"),
    # The verb only. "until bubbly and faintly sour" describes a fermented
    # batter's smell, and naming that interval "souring" would be a guess.
    (re.compile(r"\bsours?\b|\bsouring\b|\bto sour\b", re.I), "souring"),
    (re.compile(r"\bprov(?:e|es|ed|ing)|\bproof", re.I), "proving"),
    (re.compile(r"\bhang", re.I), "draining"),
    (re.compile(r"\bsteep|\binfus|\bmacerat", re.I), "steeping"),
    # Explicit resting outranks the fridge it happens in: "rest 6 hours, or
    # overnight in the refrigerator" is a rest, not a chill.
    (re.compile(r"\brest\b|\brests\b|\bresting\b", re.I), "resting"),
    (re.compile(r"\bto set\b|\bsetting\b|\bset completely\b", re.I), "setting"),
    (re.compile(r"\bchill|\brefrigerat|\bfreez", re.I), "chilling"),
    (re.compile(r"\bcool", re.I), "cooling"),
    (re.compile(r"\bin the sun\b|\bcur(?:e|es|ed|ing)", re.I), "curing"),
    (re.compile(r"\bair-dry\b|\bdry out\b|\bdrying\b|\bdries\b", re.I), "drying"),
    (re.compile(r"\bset|\bstand|\bsettl|\bleave|\bsit", re.I), "resting"),
]

UNIT_MIN = {"h": 60, "hr": 60, "hrs": 60, "hour": 60, "hours": 60,
            "day": 1440, "days": 1440, "week": 10080, "weeks": 10080,
            "minute": 1, "minutes": 1, "min": 1, "mins": 1}

NUM = r"(\d+(?:\.\d+)?)(?:\s*(?:-|–|to)\s*(\d+(?:\.\d+)?))?"
DUR = re.compile(NUM + r"\s*(hours?|hrs?|h|days?|minutes?|mins?|weeks?)\b", re.I)
OVERNIGHT_MIN = 480          # what "overnight" is worth when no number is given
OVERNIGHT = re.compile(r"\bovernight\b", re.I)

# An interval shorter than this is part of cooking, not a reason to start a
# day early. Ten minutes of resting a dough does not need its own stat.
FLOOR = 15


# Where the prose defeats the parser. Each entry says why, because a bare
# number here is unreviewable. Value is (minutes, label) or (0, None) to say
# the recipe has no required inactive time at all.
OVERRIDES = {
    # --- prose that names an interval without requiring one -----------------

    # "Nihar means dawn. It was cooked overnight on dying coals" — history, and
    # IGNORE misses it because the sentence splits before "was".
    "nalli-nihari": (0, None),
    "nihari": (0, None),
    # "Roast and grind the masala the same day. Once it sits overnight the
    # stone flower loses most of its smoke." An argument against waiting.
    "saoji-mutton": (0, None),
    # "the fresh, curd-free version ... not the overnight fermented basi
    # pakhala." Naming the dish this is not.
    "saja-pakhala": (0, None),
    # "Stored warm they go soft overnight" — a storage warning.
    "murukku": (0, None),
    # The recipe on the page is the quick version, which skips the soak. The
    # overnight belongs to the traditional version offered as an alternative,
    # and putting it in the stat would misdescribe the steps underneath it.
    "dahi-pakhala": (0, None),
    # "Leave fresh buttermilk on the counter overnight, OR stir a squeeze of
    # lemon into it." The second half takes a minute.
    "pithla": (0, None),
    # The two-to-three day sun-drying is for making mangodi from scratch. The
    # note directly after it assumes the shop-bought kind, and so does step 1.
    "mangodi-ki-sabzi": (0, None),

    # --- intervals the parser reads, but reads wrongly ----------------------

    # "The dough must rest. Overnight is normal and three days is better."
    # Required is overnight; three days is the counsel of perfection.
    "adhirasam": (480, "resting"),
    # Anarsa's rice soaks three days before anything else happens, and the
    # dough then rests a further day. The soak is the interval to plan around.
    "anarsa": (4320, "soaking"),
    # "Sprouting matki takes two days: soak the beans 8 hours ... leave in a
    # warm place 24 to 36 hours." Sequential, and the recipe's own summary of
    # the pair is two days.
    "matki-usal": (2880, "sprouting"),
    # "Soak the chana dal 2 hours and the rice 30 minutes, separately." Two
    # soaks running at once, so the wait is the longer of them, not the
    # shorter one the clause rule picks.
    "tudkiya-bhath": (120, "soaking"),
    # "Plan around the setting time: 6-8 hours undisturbed." The interval is
    # named in a clause of its own, away from any verb the parser knows.
    "mishti-doi": (360, "setting"),
    # "Leave the bread slices out uncovered for a few hours, or overnight, so
    # they dry a little." A few hours is what it needs; overnight is the
    # convenient way to get them.
    "double-ka-meetha": (180, "drying"),
    # "Leave 2 days before eating" — balchao matures in the jar rather than
    # resting, and the parser has no word for that.
    "prawn-balchao": (2880, "maturing"),
    # The step that carries the interval says "leave in a warm place until
    # doubled, bubbly and faintly sour" without ever saying ferment, which is
    # what those three words describe. The prep note above it does say it.
    "masala-dosa": (480, "fermenting"),
    # "Rub it hard into the slashed chicken, working it into the cuts, and
    # refrigerate overnight." A marinade by every description but the word.
    "parsi-margi-na-farcha": (480, "marinating"),
}


def label_for(text):
    for rx, name in LABELS:
        if rx.search(text):
            return name
    return "resting"


def sentences(text):
    return re.split(r"(?<=[.;:])\s+", text)


def clauses(sentence):
    """Split where one waiting period ends and the next instruction begins.

    "Soak the urad dal 4 hours, then drain it in a sieve for 10 minutes" is
    two clauses. Read whole, the shortest duration in it is the sieve, which
    is not what anyone is waiting for.
    """
    return re.split(r",?\s+then\s+|;\s+", sentence)


def required(sentence, carried_verb=False):
    """Minutes this sentence requires, or 0.

    Within a clause, the SHORTEST duration wins, because that is the one the
    recipe insists on: "at least 30 minutes, or up to 4 hours" requires
    thirty. Across clauses the longest wins, because they are separate waits
    and only the longest has to be planned around.

    The waiting word has to come BEFORE the duration. "Cover and cook 15
    minutes until the rice is almost dry" mentions both, but the fifteen
    minutes belongs to "cook"; only a verb standing in front of a number is
    describing how long to leave the thing alone.

    carried_verb says the preceding sentence gave the instruction and this one
    only gives the clock, as in "Cool completely in the tin." / "At least 3
    hours."
    """
    if IGNORE.search(sentence):
        return 0
    best = 0
    for c in clauses(sentence):
        verb = INACTIVE.search(c)
        if not verb and not carried_verb:
            continue
        at = verb.start() if verb else -1
        found = [float(m.group(1)) * UNIT_MIN[m.group(3).lower()]
                 for m in DUR.finditer(c) if m.start() > at]
        this = min(found) if found else (OVERNIGHT_MIN if OVERNIGHT.search(c) else 0)
        best = max(best, this)
    return int(best)


def derive(r):
    """(minutes, label) for the longest interval the recipe actually requires.

    Longest, because intervals in different steps are usually sequential: a
    batter that soaks six hours and then ferments eight is fourteen hours of
    waiting, but the stat names the one to plan around rather than pretending
    to a total we cannot verify is additive.
    """
    if r["id"] in OVERRIDES:
        return OVERRIDES[r["id"]]
    best, src, context = 0, None, ""
    # (text to read, text to name it by). A tip is read on its own but named
    # from its step, so "At least 3 hours" under "Cool completely in the tin"
    # is cooling rather than the fallback.
    chunks = [(n, n) for n in r.get("prepNotes", [])]
    for s in r["steps"]:
        # Step and tip are read together as well as apart, because the clock
        # is often in the tip and the verb it belongs to is in the step:
        # "Cool completely in the tin." / "At least 3 hours."
        chunks.append((s["text"], s["text"]))
        if s.get("tip"):
            joined = s["text"] + " " + s["tip"]
            chunks.append((s["tip"], joined))
            chunks.append((joined, joined))
    for text, ctx in chunks:
        carried = False
        for s in sentences(text):
            v = required(s, carried)
            if v > best:
                best, src, context = v, s, ctx
            # An instruction that names no clock hands one to a later
            # sentence, and keeps holding it past any sentence that names
            # neither, until some duration finally answers it.
            if INACTIVE.search(s) and not DUR.search(s):
                carried = True
            elif v:
                carried = False
    if best < FLOOR:
        return 0, None
    # The sentence names the interval where it can; the surrounding step is
    # the fallback, not the first choice, or a step-long paragraph would
    # rename an interval its own sentence already described.
    label = label_for(src)
    if label == "resting" and label_for(context) != "resting":
        label = label_for(context)
    return best, label


def human(mins):
    if mins % 1440 == 0 and mins >= 1440:
        d = mins // 1440
        return "%d day%s" % (d, "" if d == 1 else "s")
    if mins >= 60:
        h, m = divmod(mins, 60)
        return "%d hr" % h if not m else "%d hr %d min" % (h, m)
    return "%d min" % mins


def main():
    dry = "--dry-run" in sys.argv
    db = json.load(open(SRC, encoding="utf-8"))
    changed, cleared, flagged = 0, 0, []

    for r in db["recipes"]:
        mins, label = derive(r)
        before = r.get("inactiveMinutes", 0)
        if mins:
            if before != mins or r.get("inactiveLabel") != label:
                changed += 1
            r["inactiveMinutes"] = mins
            r["inactiveLabel"] = label
            active = (r.get("prepMinutes") or 0) + (r.get("cookMinutes") or 0)
            if mins > active:
                flagged.append((r["id"], active, mins, label))
        else:
            if r.pop("inactiveMinutes", None) is not None:
                cleared += 1
            r.pop("inactiveLabel", None)

    if "--report" in sys.argv:
        for rid, active, mins, label in sorted(flagged, key=lambda x: -x[2]):
            print("  %-32s active %4d min   + %-10s %s"
                  % (rid, active, human(mins), label))
        print()

    have = sum(1 for r in db["recipes"] if r.get("inactiveMinutes"))
    print("inactive time on %d of %d recipes; %d exceed the active total"
          % (have, len(db["recipes"]), len(flagged)))
    if dry:
        print("dry run, nothing written")
        return 0
    json.dump(db, open(SRC, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("wrote %s" % os.path.relpath(SRC, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
