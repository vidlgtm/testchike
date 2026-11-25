#!/usr/bin/env python3
"""FIXED. Finds the first Chrome GL backend that really uses the GPU (Colab T4) and saves it to out/.gl_backend.

Remotion + three.js must render with hardware WebGL: with SwiftShader (CPU) a 1080x1920 frame of this look
(MSAA 4 + ink + 2 lens passes + bloom) takes minutes on Colab's 2 vCPUs.

usage: python tools/gpu_probe.py            -> prints the verdict, writes out/.gl_backend
"""
import json, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = ["vulkan", "angle-egl", "angle"]


def probe(gl):
    cmd = ["npx", "remotion", "gpu", f"--gl={gl}", "--chrome-mode=chrome-for-testing"]
    try:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    out = (r.stdout or "") + (r.stderr or "")
    low = out.lower()
    # `remotion gpu` prints chrome://gpu feature lines such as "WebGL: Hardware accelerated"
    m = re.search(r"webgl[^\n]*", low)
    line = m.group(0) if m else ""
    hardware = ("hardware accelerated" in line) and ("software" not in line)
    if "swiftshader" in low and "nvidia" not in low:
        hardware = False
    return hardware, out


def main():
    os.makedirs(os.path.join(REPO, "out"), exist_ok=True)
    verdict = {"gl": "swangle", "hardware": False}
    for gl in CANDIDATES:
        print(f"--- probing --gl={gl}", flush=True)
        ok, out = probe(gl)
        print("\n".join(out.strip().splitlines()[-18:]))
        if ok:
            verdict = {"gl": gl, "hardware": True}
            break
    if not verdict["hardware"]:
        print("\n!!! NO HARDWARE WEBGL. Falling back to swangle (CPU) - rendering will be extremely slow.")
        print("!!! Check: Runtime = T4 GPU, `nvidia-smi` works, and colab/setup_colab.sh installed libnvidia-gl-<driver>.")
    else:
        print(f"\nOK: hardware WebGL via --gl={verdict['gl']}")
    with open(os.path.join(REPO, "out", ".gl_backend"), "w") as f:
        json.dump(verdict, f)
    print(json.dumps(verdict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
