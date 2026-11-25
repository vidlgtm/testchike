# TEMPLATE CONTRACT — what is FIXED and what CHANGES per video

This repo is a **template** for ~55-70 s vertical cartoon story shorts ("flat 2D characters in a colourful 3D toon
world", three.js inside Remotion, synthesized sound). The proven example is `projects/bridge`.

> **Rule 1.** To make a new video you write ONLY the files in column **VARIABLE**. You never edit a **FIXED** file.
> `python tools/check_project.py <project>` fails if a fixed file changed (hashes in `FIXED.sha256`).
> **Rule 2.** Nothing is rendered on a local machine. Rendering = `colab/Render_Short_T4.ipynb` on a free T4.

## 1. FIXED (never edit while making a video)

| Path | What it owns |
|---|---|
| `src/engine/ink.ts` | world ink-line pass (#030303, 5.1 px near → 3.3 px far @1080×1920, `NOINK` layer) |
| `src/engine/lensblur.ts` | thin-lens depth of field (pre + main pass), film grain (off) |
| `src/engine/grade.ts` | colour grade presets + strength per light |
| `src/engine/lights.ts` | `LIGHTS` + `LOOK` presets: **`day`** and **`golden`** (sun, shade, sky, fog) |
| `src/engine/shade.ts`, `cardshade.ts` | two-tone shading, character cards lit by the scene light |
| `src/engine/paint.ts` | HD Canvas2D texture painter (planks, stone, cobble, grass, water, clouds …) |
| `src/engine/toon.ts` | the `Pen` drawing API, bean-head characters, 14 faces, stick limbs, plum ink, prop cards |
| `src/engine/Short.tsx` | the composer: ink → lens pre → lens main → bloom → NEUTRAL tone map → grade, MSAA 4, crossfades, flash |
| `src/Root.tsx`, `src/index.ts`, `remotion.config.ts` | composition `Short` 1080×1920, project selection (`PROJECT=<name>`) |
| `public/kenney/*.glb` | CC0 Kenney props (trees, bushes, flowers, stalls, lantern, cart, windmill, canoe …) |
| `audio_engine/dsp.py`, `instruments.py`, `sfx_gen.py` | DSP, instruments, the synthesized-sound generators |
| `audio_engine/mix.py` | voice + score + SFX mix: duck, per-section levels, −15 LUFS, 4× oversampled limiter ≤ −1.2 dBTP |
| `tools/*.py`, `colab/*` | voice, GPU probe, validation, scaffolding, chunked render, QA |

Look values that are therefore **locked** (from `references/`): ink colour/width, DOF scale, bloom (thr 1.0, int .5),
tone map NEUTRAL, light presets, character proportions (bean h/w .94, 3.5 head-heights), plum ink `#241726`,
walk bob/lean, no captions, no film grain, voice = one steady tone, mix standard (music +3 dB, SFX −6 dB, voice unchanged).

## 2. VARIABLE (what the author writes for each video) — `projects/<name>/`

| File | You decide | Notes |
|---|---|---|
| `SCRIPT.md` | facts + sources, the script | one surprising TRUE story with a physical cause→effect; beat formula in `references/STYLE_BIBLE.md` |
| `voice/script.txt` | the narration, one sentence per line | ~3.7 words/s, 55-70 s, English |
| `project.json` | title, voice engine/voice/rate | `edge` (free TTS) or `file` (your own recording) |
| `voice/voice.wav`, `voice/words.json` | *generated* by `tools/voice.py` | every shot/sound is timed to `words.json` (`{w,s,e}`) |
| `video/story.ts` | **the picture timeline** | `FPS`, `TOTAL`, `SHOTS` (id, a, b, light `day`/`golden`, crowd, `tau`), `XFADE`, `FLASH_AT`, `CAMS` (pos/look/fov/roll keys), `KICKS`, `DOF`/`dofAt`, `FOREGROUND`, the story physics (`amp`, `stomp`, …) |
| `video/build.ts` | the place | town/houses/props layout, recolouring of kit props, sight-line culling |
| `video/world.ts` | the 3D scene of THIS story | geometry that moves (here: bridge deck, chains, swing), `KENNEY` list of GLBs, `World.update(id, f, cam, scene)` |
| `video/cast.ts` | who is on screen | actors, crowds, walk cycles, effect cards (`stage(id, t, …)`) |
| `video/index.ts` | the **contract exports** | must export `World, loadKit, Kit, FPS, TOTAL, FLASH_AT, SHOTS, layersAt, dofAt` |
| `audio/timeline.py` | the picture timeline, mirrored for sound | `TOTAL`, `FPS`, `SHOTS` MUST equal `story.ts` (checked) + event times (snap, hits, footfalls …) |
| `audio/sfx.py` | the SFX cue table | which generator (from `sfx_gen.py`) at which time/distance |
| `audio/music.py` | the original score | sections, themes, chords; `SECTIONS` |
| `audio/mix_config.py` | music level per section, speech dips, hard switches, report | `MUSIC_TARGET[section]` for every `music.SECTIONS` name |

## 3. The contract between the engine and a project

`src/engine/Short.tsx` imports **only** this from `@project` (→ `projects/<name>/video/index.ts`):

```ts
World            // class: new World(kit); world.root (THREE.Object3D); world.update(shotId, frame, camera, scene) → look-at target
loadKit()        // Promise<Kit>: loads public/kenney/<name>.glb
Kit              // type
FPS, TOTAL       // numbers
FLASH_AT         // frame of the 4-frame white flash after the hook
SHOTS            // { id, a, b, light: "day" | "golden", crowd, tau, towns? }[]  (id = index+1, contiguous, covers 0..TOTAL)
layersAt(f)      // [{id, alpha}] shots to draw (base + fading-in next shot during a crossfade)
dofAt(f)         // { cInf, focus?(f) } lens blur per frame
```
Cards (characters, signs, effect cards) must be on the `NOINK` layer (see `cast.ts`) and lit through `cardshade.ts`.
Every pixel-sized parameter scales with output height / 1920 (engine does this) — never hard-code pixels in a project.

## 4. Per-video recipe (in this order; `projects/<name>/TODO.md` is generated with it)

1. `python tools/new_project.py <name> --title "…"` (copies `bridge` as the working starting point)
2. Facts → `SCRIPT.md`; narration → `voice/script.txt`; `project.json`
3. Colab: voice step → `words.json` → `python tools/words_to_frames.py <name>` gives the word→frame table
4. Rewrite `story.ts` (shots + cameras to words; reactions land 0-3 frames BEFORE the word), then `build/world/cast`
5. Mirror `story.ts` in `audio/timeline.py`; write `sfx.py`, `music.py`, `mix_config.py`
6. `python tools/check_project.py <name>` → Colab stills (`--stills`) → fix → full render → QA report

## 5. Readability traps (from the proven short — check every new prop/shot)
- A swing drawn as one rope behind the kid reads as a hanging: two ropes, a wide plank, kid between.
- Props/flotsam closer than ~2 m to the lens become huge cut-off blobs; a cut foreground bush reads as a green ball.
- No flag that reads as another country's flag; use a period-correct one. Signs get an unlit material.
- Golden rim light = inner rim only, head/torso only. Lens ~2.5 m up so rails cross legs, not torsos.
- Every hold needs a creeping push-in (a static hold ≥ 12 f is flagged "frozen" by QA).
- No captions/labels in the video. English only. Jokes are researched real facts.
