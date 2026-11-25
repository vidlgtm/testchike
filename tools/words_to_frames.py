#!/usr/bin/env python3
"""FIXED. words.json -> a frame table so the author of story.ts can time every shot to a spoken word.

  python tools/words_to_frames.py <project>      -> prints it and writes projects/<name>/voice/words_frames.md

Rule from the style bible: every visual reaction lands 0-3 frames BEFORE its word.
"""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
proj = os.path.join(REPO, "projects", sys.argv[1])
story = open(os.path.join(proj, "video", "story.ts"), encoding="utf-8").read()
fps = int(re.search(r"export const FPS = (\d+)", story).group(1))
words = json.load(open(os.path.join(proj, "voice", "words.json"), encoding="utf-8"))

rows, sent = ["| # | word | start s | start f | end f | note |", "|---|---|---|---|---|---|"], 1
for i, w in enumerate(words):
    note = ""
    if i == 0 or re.search(r"[.!?]$", words[i - 1]["w"]):
        note = f"**sentence {sent} starts**"
        sent += 1
    if i and w["s"] - words[i - 1]["e"] > 0.35:
        note += f" pause {w['s'] - words[i - 1]['e']:.2f} s"
    rows.append(f"| {i} | {w['w']} | {w['s']:.2f} | {round(w['s'] * fps)} | {round(w['e'] * fps)} | {note.strip()} |")
total = round(words[-1]["e"] * fps)
rows.append(f"\nSpeech ends at frame {total} ({words[-1]['e']:.2f} s). TOTAL in story.ts should be >= {total + 15} (a short tail).")
text = "\n".join(rows)
open(os.path.join(proj, "voice", "words_frames.md"), "w", encoding="utf-8").write(f"# words -> frames ({fps} fps)\n\n" + text + "\n")
print(text)
