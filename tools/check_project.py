#!/usr/bin/env python3
"""FIXED. Guards the template contract. Run it before every render (the Colab notebook does).

  python tools/check_project.py <project>       validate a video project (exit code 1 on any ERROR)
  python tools/check_project.py --seal          re-record the hashes of the FIXED files (maintainers only)

Checks
  1. FIXED files are byte-identical to FIXED.sha256 (an author must never edit the engine to make a video)
  2. the project has every VARIABLE file, project.json is complete, index.ts exports the contract
  3. story.ts and timeline.py describe the SAME picture (TOTAL, FPS, shot ranges) - the sound is timed to it
  4. voice/script.txt exists; voice.wav / words.json exist (WARN before the voice step) and fit inside the picture
  5. the TypeScript of the project compiles against the engine (tsc, project alias)
"""
import glob, hashlib, json, os, re, subprocess, sys, wave

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO, "FIXED.sha256")
FIXED_GLOBS = ["src/engine/*", "src/Root.tsx", "src/index.ts", "remotion.config.ts", "tsconfig.json", "package.json",
               "package-lock.json", "audio_engine/*.py", "tools/*.py", "colab/*", "public/kenney/*"]
CONTRACT = ["World", "loadKit", "Kit", "FPS", "TOTAL", "FLASH_AT", "SHOTS", "layersAt", "dofAt"]
VARIABLE = ["project.json", "voice/script.txt", "video/index.ts", "video/story.ts", "video/world.ts", "video/build.ts",
            "video/cast.ts", "audio/timeline.py", "audio/music.py", "audio/sfx.py", "audio/mix_config.py"]
errors, warns = [], []


def fixed_files():
    out = []
    for g in FIXED_GLOBS:
        out += [p for p in glob.glob(os.path.join(REPO, g)) if os.path.isfile(p)]
    return sorted(set(out))


def digest(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def seal():
    with open(MANIFEST, "w") as f:
        for p in fixed_files():
            f.write(f"{digest(p)}  {os.path.relpath(p, REPO)}\n")
    print("sealed", len(fixed_files()), "fixed files ->", MANIFEST)


def check_fixed():
    if not os.path.exists(MANIFEST):
        warns.append("FIXED.sha256 missing (run --seal)")
        return
    want = dict(l.strip().split("  ", 1)[::-1] for l in open(MANIFEST) if l.strip())
    for rel, h in want.items():
        p = os.path.join(REPO, rel)
        if not os.path.exists(p):
            errors.append(f"FIXED file deleted: {rel}")
        elif digest(p) != h:
            errors.append(f"FIXED file edited: {rel}  -> move your change into projects/<name>/ (see TEMPLATE_CONTRACT.md)")


def num(pattern, text):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


def shots_ts(src, total):
    return [(int(i), int(a), total if b == "TOTAL" else int(b)) for i, a, b in re.findall(r"\{ id: (\d+), a: (\d+), b: (\w+),", src)]


def shots_py(src, total):
    out = []
    for i, a, b in re.findall(r"(\d+): \((\d+), (\w+), \"", src):
        out.append((int(i), int(a), total if b == "TOTAL" else int(b)))
    return out


def check_project(name):
    root = os.path.join(REPO, "projects", name)
    if not os.path.isdir(root):
        errors.append(f"no such project: projects/{name}")
        return
    for rel in VARIABLE:
        if not os.path.exists(os.path.join(root, rel)):
            errors.append(f"missing VARIABLE file: projects/{name}/{rel}")
    if errors:
        return
    cfg = json.load(open(os.path.join(root, "project.json"), encoding="utf-8"))
    for k in ("name", "title", "voice"):
        if k not in cfg:
            errors.append(f"project.json: missing '{k}'")
    if cfg.get("name") != name:
        errors.append(f"project.json name '{cfg.get('name')}' != folder '{name}'")
    idx = open(os.path.join(root, "video", "index.ts"), encoding="utf-8").read()
    for n in CONTRACT:
        if not re.search(rf"\b{n}\b", idx):
            errors.append(f"video/index.ts must export '{n}' (the engine/project contract)")
    story = open(os.path.join(root, "video", "story.ts"), encoding="utf-8").read()
    tl = open(os.path.join(root, "audio", "timeline.py"), encoding="utf-8").read()
    t_ts, t_py = num(r"export const TOTAL = (\d+)", story), num(r"\nTOTAL = (\d+)", tl)
    f_ts, f_py = num(r"export const FPS = (\d+)", story), num(r"\nFPS = (\d+)", tl)
    if t_ts is None or t_py is None or t_ts != t_py:
        errors.append(f"TOTAL differs: story.ts={t_ts} timeline.py={t_py} (they must mirror each other)")
    if f_ts != f_py:
        errors.append(f"FPS differs: story.ts={f_ts} timeline.py={f_py}")
    if t_ts:
        a, b = shots_ts(story, t_ts), shots_py(tl, t_ts)
        if not a:
            errors.append("story.ts: no SHOTS found")
        elif a != b:
            errors.append("SHOTS differ between story.ts and timeline.py:\n   story.ts    " + str(a) + "\n   timeline.py " + str(b))
        for (i, s0, s1), nxt in zip(a, a[1:] + [None]):
            if s1 <= s0:
                errors.append(f"shot {i}: b <= a")
            if nxt and nxt[1] != s1:
                errors.append(f"shot {i} ends at {s1} but shot {nxt[0]} starts at {nxt[1]} (gap/overlap)")
        if a and (a[0][1] != 0 or a[-1][2] != t_ts):
            errors.append("shots must cover frame 0 .. TOTAL exactly")
    # voice
    vdir = os.path.join(root, "voice")
    wav, words = os.path.join(vdir, "voice.wav"), os.path.join(vdir, "words.json")
    if not os.path.exists(wav) or not os.path.exists(words):
        warns.append("voice.wav / words.json not made yet (python tools/voice.py " + name + ")")
    else:
        w = wave.open(wav, "rb")
        dur = w.getnframes() / w.getframerate()
        if w.getframerate() != 48000:
            errors.append(f"voice.wav is {w.getframerate()} Hz, must be 48000 (run tools/voice.py)")
        if t_ts and f_ts and dur > t_ts / f_ts:
            errors.append(f"voice.wav is {dur:.2f} s but the picture is only {t_ts / f_ts:.2f} s")
        ws = json.load(open(words, encoding="utf-8"))
        if not all({"w", "s", "e"} <= set(x) for x in ws):
            errors.append("words.json entries must be {w, s, e}")
    # typescript
    cfgp = os.path.join(REPO, "tsconfig.check.json")
    json.dump({"extends": "./tsconfig.json", "compilerOptions": {"paths": {
        "@project": [f"projects/{name}/video/index.ts"], "@engine/*": ["src/engine/*"]}},
        "include": ["src", f"projects/{name}/video", "remotion.config.ts"]}, open(cfgp, "w"))
    r = subprocess.run(["npx", "tsc", "--noEmit", "-p", cfgp], cwd=REPO, capture_output=True, text=True)
    os.remove(cfgp)
    if r.returncode:
        errors.append("TypeScript errors:\n" + (r.stdout + r.stderr).strip()[:3000])


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--seal":
        return seal()
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    check_fixed()
    check_project(sys.argv[1])
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n{len(errors)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
