#!/usr/bin/env python3
"""FIXED. The render orchestrator (runs on the Colab T4; never run it on a small local machine).

  python tools/render.py <project> --stills 100,400,900          look check: JPEG stills at --scale 0.5
  python tools/render.py <project> --quality 1080p               full video (preview | 1080p | 2k)
  options: --chunk 300 --concurrency 2 --gl vulkan --skip-audio --crf 16 --out out/<project>

What it does
  1. bundles the Remotion project ONCE (PROJECT env var selects projects/<name>/video through remotion.config.ts)
  2. renders the frames in chunks of --chunk frames. Each chunk is its own Chrome session: ANGLE/GPU Chrome leaks
     memory over thousands of frames, and a Colab disconnect only loses the current chunk (finished chunks are
     skipped on the next run, so keep out/ on Google Drive).
  3. concatenates the chunks, muxes the synthesized mix (audio_engine/mix.py) with -map 0:v:0 -map 1:a:0
  4. runs tools/short_qa.py (black / white / frozen / pop frames, loudness, contact sheets)
"""
import argparse, json, math, os, re, shutil, subprocess, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUALITY = {"preview": 0.5, "1080p": 1.0, "2k": 1.3333}


def run(cmd, env=None, check=True):
    print("$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=REPO, env=env)
    if check and r.returncode:
        sys.exit(f"command failed ({r.returncode}): {' '.join(cmd)}")
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--quality", choices=list(QUALITY), default="1080p")
    ap.add_argument("--stills", help="comma separated frame numbers")
    ap.add_argument("--chunk", type=int, default=300)
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--gl", help="override the GL backend (default: out/.gl_backend from tools/gpu_probe.py)")
    ap.add_argument("--skip-audio", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    name = a.project
    out = os.path.abspath(a.out or os.path.join(REPO, "out", name))
    os.makedirs(out, exist_ok=True)
    story = open(os.path.join(REPO, "projects", name, "video", "story.ts"), encoding="utf-8").read()
    total = int(re.search(r"export const TOTAL = (\d+)", story).group(1))
    fps = int(re.search(r"export const FPS = (\d+)", story).group(1))

    gl = a.gl
    if not gl:
        p = os.path.join(REPO, "out", ".gl_backend")
        verdict = json.load(open(p)) if os.path.exists(p) else {"gl": "angle-egl", "hardware": False}
        gl = verdict["gl"]
        if not verdict.get("hardware"):
            print("WARNING: no hardware WebGL was verified (run tools/gpu_probe.py). Using", gl)
    env = dict(os.environ, PROJECT=name, REMOTION_GL=gl, REMOTION_CHROME_MODE="chrome-for-testing")
    env.setdefault("REMOTION_TMP", "/tmp/remotion-tmp")
    os.makedirs(env["REMOTION_TMP"], exist_ok=True)
    env["TMPDIR"] = env["REMOTION_TMP"]
    scale = QUALITY["preview"] if a.stills else QUALITY[a.quality]

    # ---- 1. bundle once
    bundle = os.path.join(out, "bundle")
    shutil.rmtree(bundle, ignore_errors=True)
    run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir", bundle], env)

    common = ["--gl=" + gl, "--chrome-mode=chrome-for-testing", "--log=warn"]

    # ---- look check stills
    if a.stills:
        sd = os.path.join(out, "stills")
        os.makedirs(sd, exist_ok=True)
        for f in [int(x) for x in a.stills.split(",") if x.strip()]:
            t0 = time.time()
            run(["npx", "remotion", "still", bundle, "Short", os.path.join(sd, f"f{f:05d}.jpg"), f"--frame={f}",
                 f"--scale={scale}", "--image-format=jpeg", "--jpeg-quality=90", "--timeout=180000", *common], env)
            print(f"still {f}: {time.time() - t0:.1f}s")
        print("stills in", sd)
        return

    # ---- audio
    mix = os.path.join(out, "audio", "mix.wav")
    if not a.skip_audio and not os.path.exists(mix):
        run([sys.executable, os.path.join(REPO, "audio_engine", "mix.py"), os.path.join(REPO, "projects", name),
             "--out", os.path.join(out, "audio")], env)
    have_audio = os.path.exists(mix)

    # ---- 2. frames in chunks
    cd = os.path.join(out, f"chunks_{a.quality}")
    os.makedirs(cd, exist_ok=True)
    n = math.ceil(total / a.chunk)
    t_all = time.time()
    done_frames = 0
    for i in range(n):
        f0, f1 = i * a.chunk, min(total, (i + 1) * a.chunk) - 1
        part = os.path.join(cd, f"c{i:04d}.mp4")
        if os.path.exists(part) and os.path.getsize(part) > 1000:
            print(f"chunk {i + 1}/{n} frames {f0}-{f1}: already rendered, skipping")
            done_frames += f1 - f0 + 1
            continue
        t0 = time.time()
        tmp = part + ".part.mp4"
        run(["npx", "remotion", "render", bundle, "Short", tmp, f"--frames={f0}-{f1}", f"--scale={scale}",
             f"--concurrency={a.concurrency}", "--codec=h264", f"--crf={a.crf}", "--pixel-format=yuv420p", "--muted",
             "--timeout=180000", *common], env)
        os.replace(tmp, part)
        dt = time.time() - t0
        done_frames += f1 - f0 + 1
        fps_now = (f1 - f0 + 1) / dt
        left = (total - done_frames) / max(fps_now, 1e-6)
        print(f"chunk {i + 1}/{n} done in {dt:.0f}s ({fps_now:.2f} fps) - ETA {left / 60:.1f} min", flush=True)
    print(f"all frames rendered in {(time.time() - t_all) / 60:.1f} min")

    # ---- 3. concat + mux
    lst = os.path.join(cd, "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.join(cd, f'c{i:04d}.mp4')}'\n" for i in range(n)))
    silent = os.path.join(out, f"{name}_{a.quality}_silent.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    final = os.path.join(out, f"{name}_{a.quality}.mp4")
    if have_audio:
        run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", mix, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", final])
    else:
        shutil.copy(silent, final)
        print("NOTE: no mix.wav - the video has no sound")
    print("FINAL:", final)

    # ---- 4. QA
    run([sys.executable, os.path.join(REPO, "tools", "shots_json.py"), name], env, check=False)
    sj = os.path.join(REPO, "out", name, "shots.json")
    run([sys.executable, os.path.join(REPO, "tools", "short_qa.py"), final, os.path.join(out, "qa"), *([sj] if os.path.exists(sj) else [])], env, check=False)
    rep = os.path.join(out, "qa", "report.md")
    if os.path.exists(rep):
        print(open(rep, encoding="utf-8").read())


if __name__ == "__main__":
    main()
