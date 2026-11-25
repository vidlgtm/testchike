#!/usr/bin/env python3
"""FIXED. projects/<name>/video/story.ts -> out/<name>/shots.json (shot ranges, crossfades, flash, planned cuts/kicks)
for tools/short_qa.py.   usage: python tools/shots_json.py <project>"""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
name = sys.argv[1]
src = open(os.path.join(REPO, "projects", name, "video", "story.ts"), encoding="utf-8").read()
total = int(re.search(r"TOTAL = (\d+)", src).group(1))
shots = [{"id": int(i), "a": int(a), "b": int(b) if b != "TOTAL" else total}
         for i, a, b in re.findall(r"\{ id: (\d+), a: (\d+), b: (\w+),", src)]
m = re.search(r"XFADE[^=]*= \{([^}]*)\}", src)
xf = {int(k): int(v) for k, v in re.findall(r"(\d+): (\d+)", m.group(1))} if m else {}
fm = re.search(r"FLASH_AT = (\d+)", src)
flash = int(fm.group(1)) if fm else None
xfade = [[s["a"] - xf[s["id"]] // 2, s["a"] + xf[s["id"]] // 2] for s in shots if s["id"] in xf]
cuts = [[int(f), int(f)] for f in re.findall(r"\{ f: (\d+), cut: true", src)]
consts = {k: float(v) for k, v in re.findall(r"\b([A-Z][A-Z0-9_]*) = ([\d.]+)", src)}
kicks = []
km = re.search(r"const KICKS[^=]*= \[(.*?)\];", src, re.S)
if km:
    for t0, _ in re.findall(r"\[([\w.]+), ([\d.]+)\]", km.group(1)):
        f0 = round((consts[t0] if t0 in consts else float(t0)) * 30)
        kicks.append([f0, f0 + 8])
out = {"shots": shots, "xfade": xfade, "planned": cuts + kicks}
if flash is not None:
    out["flash"] = [flash, flash + 4]
od = os.path.join(REPO, "out", name)
os.makedirs(od, exist_ok=True)
json.dump(out, open(os.path.join(od, "shots.json"), "w"), indent=1)
print(len(shots), "shots; xfade", xfade, "flash", flash, "cuts", [c[0] for c in cuts], "kicks", [k[0] for k in kicks])
