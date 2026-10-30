"""Search for run-length code widths that give the smallest stream.

The search is a genetic algorithm:

- A candidate is a list of segment widths, for example [5, 2, 1, 3].
- Each candidate is scored by the exact number of bits the encoder would write.
- The best candidates are kept, pairs are combined (crossover), and small random
  changes are added (mutation). Repeat for several generations.

Scoring does not re-encode the video for every candidate. The run lengths are read
once, and a histogram of stored values is built for each total width. A candidate
is then scored from the histogram, which is fast.

Run it from anywhere:

    python encoder/search_vlq.py --skip 1
    python encoder/search_vlq.py --skip 3 --generations 40 --seed 2

The best result is written to encoder/vlq_search_skip<N>.json. To use it, pass the
widths to encoder/main.py with --vlq.
"""

import argparse
import json
import os
import random

import numpy as np

import main as enc

HERE = os.path.dirname(os.path.abspath(__file__))

MIN_TOTAL = 16  # total bits in the code
MAX_TOTAL = 22  # histograms have 2**MAX_TOTAL bins, so keep this moderate
MAX_SEGMENTS = 10
MAX_WIDTH = 12

# Starting points for the search: the current code, and a few others from the old encoder notes.
SEEDS = [
    [5, 2, 1, 3, 2, 1, 1, 4, 2],
    [6, 2, 2, 4],
    [6, 2, 5],
    [4, 4, 6],
    [7, 4, 4],
    [8, 7],
    [6, 5, 4],
]


class Scorer:
    """Scores width lists by the number of bits the encoder would write."""

    def __init__(self, lengths):
        # Maximal run lengths of the whole stream, before any cutting.
        self.lengths = lengths
        self.runs = len(lengths)
        self.histograms = {}
        self.scores = {}

    def histogram(self, total):
        """Return (values, counts): how often each stored value occurs if the code holds `total` bits."""
        if total not in self.histograms:
            top = 1 << total  # longest run one code can hold
            lengths = self.lengths

            long_runs = lengths > top
            pieces = np.ceil(lengths[long_runs] / top).astype(np.int64)
            last_piece = lengths[long_runs] - (pieces - 1) * top

            hist = np.bincount(lengths[~long_runs] - 1, minlength=top).astype(np.int64)
            # Each long run is cut into full pieces (stored value top - 1) and one last piece.
            hist[top - 1] += int((pieces - 1).sum())
            hist += np.bincount(last_piece - 1, minlength=top)

            values = np.flatnonzero(hist)
            self.histograms[total] = (values, hist[values])
        return self.histograms[total]

    def bits(self, widths):
        """Total bits for the whole stream with this code."""
        total = sum(widths)
        values, counts = self.histogram(total)

        # Bits per stored value: a prefix bit and the width for each segment used.
        cum_width = np.cumsum(widths)
        cum_cost = np.cumsum([1 + w for w in widths])
        needed = np.maximum(1, np.frexp(values.astype(np.float64))[1])  # bit length of each value
        segments = np.searchsorted(cum_width, needed, side="left")
        per_value = cum_cost[segments]

        # A maximum-length run is followed by an explicit colour bit.
        explicit = (values == (1 << total) - 1).astype(np.int64)

        # +1 for the colour of the first run.
        return int(np.sum(counts * (per_value + explicit))) + 1

    def score(self, widths):
        key = tuple(widths)
        if key not in self.scores:
            self.scores[key] = self.bits(widths)
        return self.scores[key]


def repair(widths, rng):
    """Make a width list valid: sensible segment count, widths, and total."""
    w = [min(max(int(x), 1), MAX_WIDTH) for x in widths][:MAX_SEGMENTS]
    if not w:
        w = [4]

    while sum(w) > MAX_TOTAL:
        i = max(range(len(w)), key=lambda k: w[k])
        w[i] -= 1

    while sum(w) < MIN_TOTAL:
        if len(w) < MAX_SEGMENTS and rng.random() < 0.3:
            w.append(1)
        else:
            i = rng.randrange(len(w))
            if w[i] < MAX_WIDTH:
                w[i] += 1
            elif len(w) < MAX_SEGMENTS:
                w.append(1)

    return w


def mutate(widths, rng):
    w = list(widths)
    i = rng.randrange(len(w))
    roll = rng.random()

    if roll < 0.35:
        w[i] += rng.choice((-2, -1, 1, 2))
    elif roll < 0.55 and w[i] >= 2:
        a = rng.randint(1, w[i] - 1)  # split one segment in two
        w[i:i + 1] = [a, w[i] - a]
    elif roll < 0.75 and i < len(w) - 1:
        w[i:i + 2] = [w[i] + w[i + 1]]  # merge two neighbours
    elif roll < 0.85 and len(w) >= 2:
        j = rng.randrange(len(w))  # swap two segments
        w[i], w[j] = w[j], w[i]
    else:
        w[i] = rng.randint(1, MAX_WIDTH)

    return repair(w, rng)


def crossover(a, b, rng):
    """Prefix of one parent, suffix of the other."""
    cut_a = rng.randint(0, len(a))
    cut_b = rng.randint(0, len(b))
    return repair(list(a[:cut_a]) + list(b[cut_b:]), rng)


def compositions(total, parts):
    """All ways to write total as an ordered sum of `parts` widths, each 1 to MAX_WIDTH."""
    if parts == 1:
        if 1 <= total <= MAX_WIDTH:
            yield (total,)
        return
    for first in range(1, min(MAX_WIDTH, total - parts + 1) + 1):
        for rest in compositions(total - first, parts - 1):
            yield (first,) + rest


def exhaustive(scorer, max_segments, log):
    """Score every code with up to max_segments segments. Slow for large values."""
    best = None
    for total in range(MIN_TOTAL, MAX_TOTAL + 1):
        for parts in range(1, max_segments + 1):
            for widths in compositions(total, parts):
                if best is None or scorer.score(widths) < scorer.score(best):
                    best = widths
    log("exhaustive best (up to {} segments): {}  {} bits".format(
        max_segments, list(best), scorer.score(best)))
    return list(best)


def tournament(population, scorer, rng, size=3):
    return min(rng.sample(population, size), key=scorer.score)


def search(scorer, rng, population_size, generations, log):
    population = [repair(seed, rng) for seed in SEEDS]
    while len(population) < population_size:
        length = rng.randint(2, 8)
        population.append(repair([rng.randint(1, 8) for _ in range(length)], rng))

    elite_count = max(2, population_size // 10)

    for generation in range(generations):
        population.sort(key=scorer.score)
        if generation % 10 == 0 or generation == generations - 1:
            best = population[0]
            log("gen {:3d}  best {}  {} bits  ({:.3f} bits/run)".format(
                generation, best, scorer.score(best), scorer.score(best) / scorer.runs))

        next_population = population[:elite_count]
        while len(next_population) < population_size:
            parent_a = tournament(population, scorer, rng)
            parent_b = tournament(population, scorer, rng)
            child = crossover(parent_a, parent_b, rng) if rng.random() < 0.7 else list(parent_a)
            if rng.random() < 0.8:
                child = mutate(child, rng)
            next_population.append(child)
        population = next_population

    population.sort(key=scorer.score)
    return population[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--skip", type=int, default=1, help="keep every N-th source frame")
    parser.add_argument("--population", type=int, default=80)
    parser.add_argument("--generations", type=int, default=120)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--exhaustive", type=int, default=0,
                        help="also try every code with up to this many segments (0 = off)")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    print("reading video, skip", args.skip)
    frames = list(enc.read_frames(enc.VIDEO_PATH, args.skip))
    bits = np.concatenate([frame.ravel() for frame in frames])
    colours, lengths = enc.find_runs(bits)
    scorer = Scorer(lengths)
    print("frames:", len(frames), " maximal runs:", len(lengths))

    default = enc.DEFAULT_VLQ_BITS
    print("default code {}: {} bits".format(default, scorer.score(default)))

    best = search(scorer, rng, args.population, args.generations, print)
    if args.exhaustive:
        candidate = exhaustive(scorer, args.exhaustive, print)
        if scorer.score(candidate) < scorer.score(best):
            best = candidate
    best_bits = scorer.score(best)
    print("best code {}: {} bits, {:.1f} KiB".format(best, best_bits, best_bits / 8 / 1024))

    # Check the prediction by encoding the video with the best code.
    runs = list(enc.split_long_runs(colours, lengths, best))
    real_bits = len(enc.encode_stream(runs, best))
    print("encoded stream: {} bits (prediction {}, difference is at most one colour bit)".format(
        real_bits, best_bits))
    assert abs(real_bits - best_bits) <= 1

    result = {
        "skip": args.skip,
        "widths": best,
        "bits": real_bits,
        "default_widths": default,
        "default_bits": scorer.score(default),
        "seed": args.seed,
    }
    path = os.path.join(HERE, "vlq_search_skip{}.json".format(args.skip))
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
    print("saved:", os.path.normpath(path))


if __name__ == "__main__":
    main()
