"""Encode the Bad Apple video into src/vid.h for the ESP32 firmware.

Run it from any folder, after installing opencv-python and numpy:

    python encoder/main.py                       # every 3rd frame, default widths
    python encoder/main.py --skip 1              # every frame
    python encoder/main.py --vlq 6,2,2,4         # other run-length code widths

The code widths and the maximum run length are written into src/vid.h, so the
firmware always uses the same values as the encoder. The bit format is described
at the top of src/main.cpp.
"""

import argparse
import os

import cv2 as cv
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_PATH = os.path.join(HERE, "Touhou - Bad AppleCR.mp4")
OUTPUT_PATH = os.path.join(HERE, "..", "src", "vid.h")

# Keep every SKIP_EVERY-th source frame. Overridden by --skip.
DEFAULT_SKIP = 3

# Segment widths of the run-length code. Overridden by --vlq.
DEFAULT_VLQ_BITS = [5, 2, 1, 3, 2, 1, 1, 4, 2]

# Picture size on the device. Must match VIDEO_W and VIDEO_H in src/main.cpp.
# The picture is the source columns CROP_X to CROP_X + VIDEO_W - 1.
CROP_X = 30
VIDEO_W = 178
VIDEO_H = 134

THRESHOLD = 128

WORD_BITS = 64


def max_stored(widths):
    """Largest stored value: the sum of the widths, as an all-ones number."""
    return (1 << sum(widths)) - 1


def read_frames(path, skip):
    """Yield every skip-th frame as a 0/1 array of shape (VIDEO_H, VIDEO_W).

    1 = white, 0 = black.
    """
    cap = cv.VideoCapture(path)
    if not cap.isOpened():
        raise SystemExit("Cannot open video: " + path)

    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if index % skip == 0:
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            _, bw = cv.threshold(gray, THRESHOLD, 255, cv.THRESH_BINARY)
            picture = bw[:VIDEO_H, CROP_X:CROP_X + VIDEO_W]

            if picture.shape != (VIDEO_H, VIDEO_W):
                raise SystemExit("Unexpected frame size, got {}".format(gray.shape))

            yield (picture > 0).astype(np.uint8)

        index += 1

    cap.release()


def find_runs(bits):
    """Split a flat 0/1 array into maximal runs. Returns the colour and length of each run."""
    changes = np.flatnonzero(bits[1:] != bits[:-1]) + 1
    starts = np.concatenate(([0], changes))
    ends = np.concatenate((changes, [bits.size]))
    return bits[starts], ends - starts


def split_long_runs(colours, lengths, widths):
    """Yield (colour, length) pairs. Runs longer than the code can hold are cut into pieces."""
    max_run = max_stored(widths) + 1
    for colour, length in zip(colours.tolist(), lengths.tolist()):
        while length > max_run:
            yield colour, max_run
            length -= max_run
        yield colour, length


def vlq_bits(stored, widths):
    """Bits for one stored run length, as a string of '0' and '1'.

    Each segment has a prefix bit: '0' for the first segment, '1' for the others.
    Segments are written least significant first, and each one is padded to its width.
    """
    if not 0 <= stored <= max_stored(widths):
        raise ValueError("run too long for the code: {}".format(stored + 1))

    needed = max(1, stored.bit_length())
    out = []
    used = 0
    for i, width in enumerate(widths):
        segment = (stored >> used) & ((1 << width) - 1)
        prefix = "0" if i == 0 else "1"
        out.append(prefix + format(segment, "0{}b".format(width)))
        used += width
        if used >= needed:
            break
    return "".join(out)


def encode_stream(runs, widths):
    """Turn (colour, length) pairs into the bit stream the firmware reads."""
    out = []
    colour_is_explicit = True  # the first colour is always stored
    previous_colour = None
    top = max_stored(widths)

    for colour, length in runs:
        if colour_is_explicit:
            out.append(str(colour))
        elif colour == previous_colour:
            # Only a cut piece of a long run can repeat a colour, and those always store it.
            raise AssertionError("colour should have alternated")

        stored = length - 1
        out.append(vlq_bits(stored, widths))

        # The firmware reads an explicit colour bit after a maximum-length run.
        colour_is_explicit = stored == top
        previous_colour = colour

    return "".join(out)


def pack_words(bit_string):
    """Split the stream into 64-bit words. The last word is padded with zeros on the right."""
    padded = bit_string + "0" * ((-len(bit_string)) % WORD_BITS)
    return [int(padded[i:i + WORD_BITS], 2) for i in range(0, len(padded), WORD_BITS)]


def write_header(path, frame_count, words, widths):
    lines = [
        "#include <pgmspace.h>",
        "",
        "const uint16_t frames_n = {};".format(frame_count),
        "const uint32_t byte_n = {};".format(len(words)),
        "",
        "// Run-length code: segment widths, and the largest stored value (their sum, all ones).",
        "const uint8_t VLQ_BITS[] = {" + ", ".join(str(w) for w in widths) + "};",
        "const uint32_t MAX_RUN_RAW = {};".format(max_stored(widths)),
        "",
        "const uint64_t v[] PROGMEM = {",
    ]

    words_per_line = 4
    for i in range(0, len(words), words_per_line):
        values = ["0x{:016X}ULL".format(w) for w in words[i:i + words_per_line]]
        lines.append(", ".join(values) + ",")

    lines.append("};")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def parse_widths(text):
    widths = [int(part) for part in text.split(",")]
    if any(w < 1 for w in widths) or sum(widths) > 31:
        raise argparse.ArgumentTypeError("widths must be >= 1 and sum to at most 31")
    return widths


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--skip", type=int, default=DEFAULT_SKIP,
                        help="keep every N-th source frame (default %(default)s)")
    parser.add_argument("--vlq", type=parse_widths, default=DEFAULT_VLQ_BITS,
                        help="comma-separated code widths (default %(default)s)")
    args = parser.parse_args()

    frames = list(read_frames(VIDEO_PATH, args.skip))
    if not frames:
        raise SystemExit("No frames read from " + VIDEO_PATH)

    bits = np.concatenate([frame.ravel() for frame in frames])
    colours, lengths = find_runs(bits)
    runs = list(split_long_runs(colours, lengths, args.vlq))

    assert sum(length for _, length in runs) == bits.size

    stream = encode_stream(runs, args.vlq)
    words = pack_words(stream)
    write_header(OUTPUT_PATH, len(frames), words, args.vlq)

    print("skip:", args.skip)
    print("vlq widths:", args.vlq)
    print("frames:", len(frames))
    print("runs:", len(runs))
    print("stream bits:", len(stream), "(%.2f bits per run)" % (len(stream) / len(runs)))
    print("64-bit words (byte_n):", len(words))
    print("written:", os.path.normpath(OUTPUT_PATH))


if __name__ == "__main__":
    main()
