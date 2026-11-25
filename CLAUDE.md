# AGENTS.md — instructions for any AI model working in this repository

You are the **author** of one short video. This repo is a finished production template: the look, the engine, the
mix and the render pipeline are DONE and LOCKED. Your job is to write the parts that change per video — and nothing else.
Read `TEMPLATE_CONTRACT.md` first (2 minutes). It lists every file as FIXED or VARIABLE.

## Hard rules
1. **Never edit a FIXED file** (`src/engine/*`, `src/Root.tsx`, `src/index.ts`, `remotion.config.ts`, `audio_engine/*`,
   `tools/*`, `colab/*`, `public/kenney/*`, `package*.json`, `tsconfig.json`). `tools/check_project.py` fails if you do.
   If you believe the engine needs a change, STOP and report it instead of patching it.
2. **Never render locally.** No `remotion render/still`, no `mix.py`, no `npm run studio` in this environment.
   Rendering is done only by `colab/Render_Short_T4.ipynb` on a Colab T4 (it pulls this repo).
   You MAY run: `python tools/check_project.py <name>`, `python tools/new_project.py`, `python tools/words_to_frames.py`,
   `npx tsc` (through check_project).
3. **Never commit secrets** (tokens, keys). Never write them into files.
4. Story, characters and voice are ORIGINAL. Facts must be true and sourced in `SCRIPT.md`. No captions or labels in the
   video. English narration, one steady voice. Never name or copy the style-reference channel.
5. Keep the look values locked (see the list at the end of section 1 of the contract).

## What you produce (VARIABLE files, in `projects/<name>/`)
`SCRIPT.md`, `voice/script.txt`, `project.json`, `video/{story,build,world,cast,index}.ts`,
`audio/{timeline,sfx,music,mix_config}.py`. Nothing outside `projects/<name>/`.

## Workflow
1. `python tools/new_project.py <name> --title "<Title>"` → work in `projects/<name>/` and follow its `TODO.md`.
2. **Topic & facts**: one surprising TRUE story with a physical cause and effect (it must be visual) + a simple everyday
   analogy that explains it. Put facts + sources at the top of `SCRIPT.md`.
3. **Script** (~3.7 words/s, 55-70 s). Beats: Hook (the absurd fact, one line) → Setting (year, place, pride) → Action
   (escalation over 3-4 beats) → Snap (the moment it happens) → Deadpan double line ("Luckily … / Unluckily …") →
   Explanation (one idea through an everyday analogy) → Consequence (the rule it created) → Callback twist.
   Never describe on screen what the viewer already sees. Jokes = researched real facts.
4. Voice: the Colab voice step produces `voice.wav` + `words.json`. Then use the frame table from
   `python tools/words_to_frames.py <name>`: **all timing comes from `words.json`.**
5. **Shot plan** in `video/story.ts`: `SHOTS` (contiguous, 0..TOTAL), `XFADE` at place/time changes, `FLASH_AT` after the hook,
   `CAMS` (hard cuts only on big jumps; otherwise smootherstep glides 18-40 f; every hold creeps in 0.15-0.35 %/f;
   rolls 4-5°), `KICKS` (7-frame flip shakes on impacts), `DOF` (lens blur on ~1/3 of the time: close-ups 12-14, medium
   10-12, wides 0; focus on the eyes), `FOREGROUND` (near props in ~1/3 of shots). Reactions land 0-3 frames BEFORE their word.
6. **World/cast**: reuse the helpers in `build.ts`/`world.ts`/`cast.ts` (copied from `bridge`); replace the bridge-specific
   scene with the place of your story. Light is `day` or `golden` only. Characters come from `toon.ts` (`Pen`, faces).
7. **Sound**: `audio/timeline.py` mirrors `story.ts` (same TOTAL, FPS, SHOTS — checked). Write the SFX cue table (`sfx.py`,
   generators from `audio_engine/sfx_gen.py`), the score (`music.py`) and `mix_config.py` (a `MUSIC_TARGET` for every
   `music.SECTIONS` name). Lock the picture's time constants BEFORE making sound; a later timing change means redoing sound.
8. Run `python tools/check_project.py <name>` until it prints `0 error(s)`.
9. Commit only `projects/<name>/`. Tell the user: open the Colab notebook, set `PROJECT=<name>`, run all cells.

## Definition of done
- `check_project.py` → 0 errors (fixed files untouched, contract exports present, story.ts ≡ timeline.py, TypeScript compiles)
- script ≈ 55-70 s, facts sourced, hook in line 1
- no local rendering was attempted; the user was told how to render on Colab

## Reference material (read, don't copy)
`references/STYLE_BIBLE.md` (script + visual formula), `references/reports/*.md` (motion, depth, textures, characters,
lighting, outlines, grade), `references/frames/` + `references/sheets/` (study frames; never publish them),
`references/ORIGINAL_SKILL.md` (the original skill text, incl. the gotchas list).
