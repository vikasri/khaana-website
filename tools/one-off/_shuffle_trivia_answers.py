#!/usr/bin/env python3
"""Spread the trivia answers across A, B, C and D. Ran once, on 120 questions.

The bank had grown with the right answer at B 78 times in 100. Pressing B
without reading scored 78%, which is not a quiz, it is a habit. This moved
each question's correct option to an assigned position and left the wrong
options in their existing order around it.

Two things it is careful about:

  * The counts come out exactly even — thirty of each position — because the
    positions are dealt from a list of thirty of each rather than drawn at
    random per question. Random per question would have left a lean of five
    or six either way, which is the problem in miniature.
  * The order those positions are dealt in is shuffled, not round-robin, and
    then constrained. The page shows five questions running from one point in
    the list, so a round-robin would have printed A, B, C, D, A every single
    day — and a plain shuffle, tried first, put five B answers in a row, which
    is a day where reading the questions is optional. No position may appear
    more than twice in any five running, counting round the end of the list,
    since the day's five wrap. Seeded, so re-running it reproduces the same
    arrangement rather than churning the file.

No option text was touched, and nothing here knows which answer is right
beyond the index already recorded in the file.
"""
import collections, json, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "data", "trivia.json")
SEED = 20260805
WINDOW = 5          # questions shown together on a day
MAX_IN_WINDOW = 2   # of them that may share an answer position


def targets_for(n, rng):
    """n answer positions, evenly split, with no position crowding a day.

    Built one at a time from whatever is still owed, rejecting any pick that
    would put a third copy of a position inside the last five. The tail has to
    close the loop with the head, so a run that paints itself into a corner is
    thrown away and started again. It takes a handful of goes.
    """
    for _ in range(2000):
        left = collections.Counter({p: n // 4 for p in range(4)})
        for p in range(n % 4):
            left[p] += 1
        out = []
        for _ in range(n):
            ok = [p for p in range(4) if left[p] and
                  out[-(WINDOW - 1):].count(p) < MAX_IN_WINDOW]
            if not ok:
                break
            p = rng.choice(sorted(ok, key=lambda p: -left[p])[:2])
            out.append(p)
            left[p] -= 1
        if len(out) < n:
            continue
        loop = out + out[:WINDOW - 1]
        if all(max(collections.Counter(loop[i:i + WINDOW]).values()) <= MAX_IN_WINDOW
               for i in range(n)):
            return out
    raise SystemExit("could not lay out the answer positions; loosen the rule")


def main():
    db = json.load(open(SRC, encoding="utf-8"),
                   object_pairs_hook=collections.OrderedDict)
    qs = db["questions"]
    n = len(qs)
    if n % 4:
        print("  ! %d questions does not divide by four; the spread will lean"
              " by one or two" % n)

    rng = random.Random(SEED)
    targets = targets_for(n, rng)

    moved = 0
    for q, target in zip(qs, targets):
        opts = list(q["options"])
        right = opts.pop(q["answer"])
        opts.insert(target, right)
        if opts != q["options"] or q["answer"] != target:
            moved += 1
        q["options"] = opts
        q["answer"] = target
        assert q["options"][q["answer"]] == right

    json.dump(db, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(SRC, "a", encoding="utf-8").write("\n")

    spread = collections.Counter(q["answer"] for q in qs)
    print("moved the answer on %d of %d questions" % (moved, n))
    print("spread now: %s" % dict(sorted(spread.items())))
    # The five shown together each day are consecutive in this list and wrap
    # round the end of it, so that is the window to check.
    loop = [q["answer"] for q in qs] * 2
    worst = max(max(collections.Counter(loop[i:i + WINDOW]).values())
                for i in range(n))
    print("most repeats of one position within any five in a row: %d" % worst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
