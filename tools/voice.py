#!/usr/bin/env python3
"""FIXED. Narration -> projects/<name>/voice/voice.wav (48 kHz mono 24-bit) + words.json (word timings).

  python tools/voice.py <project> [--engine edge|file] [--voice en-US-GuyNeural] [--rate +0%]
                                  [--whisper small.en] [--force]

Engines
  edge  free Microsoft neural voices through the `edge-tts` package (needs internet, no key, no GPU).
        ONE voice for the whole short ("voice: one steady tone"). Default.
  file  you drop your own recording at projects/<name>/voice/voice.wav (any format ffmpeg can read);
        this tool only normalises it to 48 kHz mono and makes the word timings.

Word timings come from faster-whisper (GPU when available, CPU fallback) and are ALIGNED to the exact script text,
so words.json always carries the script's own spelling:  [{"w": "Seventy-four", "s": 0.12, "e": 0.61}, ...]
Everything in the picture and the sound is timed to this file (see TEMPLATE_CONTRACT.md).
"""
import argparse, asyncio, difflib, json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sh(*cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def read_script(path):
    lines = []
    for l in open(path, encoding="utf-8").read().splitlines():
        l = l.strip()
        if l and not l.startswith("#"):
            lines.append(l)
    return lines


async def tts_edge(text, voice, rate, out_mp3):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(out_mp3)


def to_wav48(src, dst):
    sh("ffmpeg", "-y", "-i", src, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s24le", dst)


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("\u2019", "'"))


def transcribe(wav, model_size):
    from faster_whisper import WhisperModel
    last = None
    for device, ctype in (("cuda", "float16"), ("cpu", "int8")):
        try:
            m = WhisperModel(model_size, device=device, compute_type=ctype)
            segs, _ = m.transcribe(wav, language="en", word_timestamps=True, beam_size=5, vad_filter=False)
            words = [(w.word.strip(), float(w.start), float(w.end)) for s in segs for w in (s.words or [])]
            print(f"whisper[{model_size}] on {device}: {len(words)} words")
            return words
        except Exception as e:  # cuda libs missing -> retry on cpu
            last = e
            print(f"whisper on {device} failed: {e!r}")
    raise RuntimeError(f"transcription failed: {last!r}")


def align(script_tokens, heard):
    """script tokens (our spelling) <- times of the heard words (whisper). Unmatched tokens are interpolated."""
    a = [norm(t) for t in script_tokens]
    b = [norm(w[0]) for w in heard]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    times = [None] * len(script_tokens)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and (i2 - i1) == (j2 - j1)):
            for k in range(i2 - i1):
                times[i1 + k] = (heard[j1 + k][1], heard[j1 + k][2])
        elif tag == "replace" and j2 > j1:  # different counts: spread the heard span over the script tokens
            s0, e0 = heard[j1][1], heard[j2 - 1][2]
            n = i2 - i1
            for k in range(n):
                times[i1 + k] = (s0 + (e0 - s0) * k / n, s0 + (e0 - s0) * (k + 1) / n)
    n = len(times)
    i = 0
    while i < n:  # interpolate the holes
        if times[i] is None:
            j = i
            while j < n and times[j] is None:
                j += 1
            left = times[i - 1][1] if i > 0 else 0.0
            right = times[j][0] if j < n else (heard[-1][2] if heard else left + 0.3 * (j - i))
            step = max(right - left, 0.05 * (j - i)) / (j - i)
            for k in range(i, j):
                times[k] = (left + step * (k - i), left + step * (k - i + 1))
            i = j
        else:
            i += 1
    out, prev_e = [], 0.0
    for tok, (s, e) in zip(script_tokens, times):
        s = max(s, prev_e - 0.02)
        e = max(e, s + 0.04)
        out.append({"w": tok, "s": round(s, 3), "e": round(e, 3)})
        prev_e = e
    return out, sm.ratio()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--engine", choices=["edge", "file"])
    ap.add_argument("--voice")
    ap.add_argument("--rate")
    ap.add_argument("--whisper")
    ap.add_argument("--force", action="store_true", help="regenerate voice.wav even if it exists")
    a = ap.parse_args()

    proj = os.path.join(REPO, "projects", a.project)
    cfg = json.load(open(os.path.join(proj, "project.json"), encoding="utf-8")).get("voice", {})
    engine = a.engine or cfg.get("engine", "edge")
    voice = a.voice or cfg.get("voice", "en-US-GuyNeural")
    rate = a.rate or cfg.get("rate", "+0%")
    wmodel = a.whisper or cfg.get("whisper_model", "small.en")
    vdir = os.path.join(proj, "voice")
    os.makedirs(vdir, exist_ok=True)
    wav = os.path.join(vdir, "voice.wav")
    script = read_script(os.path.join(vdir, "script.txt"))
    text = " ".join(script)
    tokens = text.split()
    print(f"script: {len(script)} lines, {len(tokens)} words (~{len(tokens) / 3.7:.0f} s at 3.7 words/s)")

    if engine == "edge":
        if a.force or not os.path.exists(wav):
            mp3 = os.path.join(vdir, "_tts.mp3")
            asyncio.run(tts_edge(text, voice, rate, mp3))
            to_wav48(mp3, wav)
            os.remove(mp3)
            print("voice.wav written with", voice, rate)
        else:
            print("voice.wav exists (use --force to regenerate)")
    else:
        if not os.path.exists(wav):
            sys.exit(f"engine=file: put your recording at {wav}")
        tmp = os.path.join(vdir, "_in.wav")
        os.replace(wav, tmp)
        to_wav48(tmp, wav)
        os.remove(tmp)

    heard = transcribe(wav, wmodel)
    words, ratio = align(tokens, heard)
    json.dump(words, open(os.path.join(vdir, "words.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    dur = words[-1]["e"] if words else 0
    print(f"words.json: {len(words)} words, speech ends at {dur:.2f} s, script/speech match {ratio * 100:.0f}%")
    if ratio < 0.85:
        print("WARNING: the spoken audio differs from script.txt - check the recording / fix words.json by hand.")


if __name__ == "__main__":
    main()
