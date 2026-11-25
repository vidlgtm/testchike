#!/usr/bin/env python3
"""FIXED. Scaffold a new video project from an existing one (default: the proven `bridge` short).

  python tools/new_project.py <name> --title "My Short Title" [--from bridge]

Creates projects/<name>/ with project.json, empty voice/script.txt and TODO.md (the exact list of VARIABLE files the
author has to rewrite). The look (src/engine/*), the composer, the mix engine and all tools stay untouched.
"""
import argparse, json, os, re, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("--title", required=True)
ap.add_argument("--from", dest="src", default="bridge")
a = ap.parse_args()
if not re.fullmatch(r"[a-z0-9_]+", a.name):
    raise SystemExit("name: lowercase letters, digits and _ only")
src, dst = os.path.join(REPO, "projects", a.src), os.path.join(REPO, "projects", a.name)
if os.path.exists(dst):
    raise SystemExit(f"projects/{a.name} already exists")
shutil.copytree(src, dst, ignore=shutil.ignore_patterns("voice.wav", "words.json", "words_frames.md", "_cache", "cues*.md", "__pycache__"))
cfg = json.load(open(os.path.join(dst, "project.json"), encoding="utf-8"))
cfg.update({"name": a.name, "title": a.title, "based_on": a.src})
json.dump(cfg, open(os.path.join(dst, "project.json"), "w", encoding="utf-8"), indent=2)
open(os.path.join(dst, "voice", "script.txt"), "w", encoding="utf-8").write("# One line per sentence. ~3.7 words/s, 55-70 s. Facts + sources go in SCRIPT.md.\n")
mc = os.path.join(dst, "audio", "mix_config.py")
s = open(mc, encoding="utf-8").read()
open(mc, "w", encoding="utf-8").write(re.sub(r'TITLE = ".*"', f'TITLE = "{a.title}"', s))
open(os.path.join(dst, "SCRIPT.md"), "w", encoding="utf-8").write(f"# {a.title}\n\n## Facts (with sources)\n\n- TODO\n\n## Script\n\nTODO (copy to voice/script.txt, one sentence per line)\n")
open(os.path.join(dst, "TODO.md"), "w", encoding="utf-8").write(f"""# {a.title}: what the author must write

Started from `{a.src}`. The look, composer, mix engine and tools are FIXED (see TEMPLATE_CONTRACT.md).
Do these in order; after each step run `python tools/check_project.py {a.name}`.

- [ ] 1. SCRIPT.md: facts with sources + the script (beat formula in references/STYLE_BIBLE.md); voice/script.txt
- [ ] 2. project.json: voice settings (one steady voice)
- [ ] 3. `python tools/voice.py {a.name}` then `python tools/words_to_frames.py {a.name}` -> words.json + frame table
- [ ] 4. video/story.ts: FPS, TOTAL, SHOTS, XFADE, FLASH_AT, CAMS, KICKS, DOF, FOREGROUND, story physics (tau)
- [ ] 5. video/build.ts + video/world.ts: the place (props, layout) for THIS story; keep Kit/GLB list in world.ts
- [ ] 6. video/cast.ts: who is on screen per shot (roles, crowds, effect cards); faces come from src/engine/toon.ts
- [ ] 7. audio/timeline.py: mirror story.ts (TOTAL, SHOTS, event times); audio/sfx.py cue table; audio/music.py score
- [ ] 8. audio/mix_config.py: MUSIC_TARGET per music section, DIPS, HARD_SWITCHES, REPORT
- [ ] 9. Colab: stills (look check) -> full render
""")
print(f"created projects/{a.name}  ->  open projects/{a.name}/TODO.md")
