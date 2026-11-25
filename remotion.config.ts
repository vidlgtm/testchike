// FIXED. Selects the active video project (PROJECT env var) and the GL backend (REMOTION_GL env var).
import { Config } from "@remotion/cli/config";
import path from "node:path";

const project = process.env.PROJECT ?? "bridge";
Config.overrideWebpackConfig((c) => ({
  ...c,
  resolve: {
    ...c.resolve,
    alias: {
      ...(c.resolve?.alias as Record<string, string> | undefined),
      "@project": path.resolve(`projects/${project}/video/index.ts`),
      "@engine": path.resolve("src/engine"),
    },
  },
}));
Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(95);
Config.setCodec("h264");
Config.setOverwriteOutput(true);
// GPU on Colab T4: REMOTION_GL=angle-egl (set by the notebook). Without a GPU: swangle (very slow).
const gl = process.env.REMOTION_GL;
if (gl) Config.setChromiumOpenGlRenderer(gl as "angle-egl");
// Chrome flavour with GPU drivers on Linux (needed on Colab): REMOTION_CHROME_MODE=chrome-for-testing
const mode = process.env.REMOTION_CHROME_MODE;
if (mode) Config.setChromeMode(mode as "chrome-for-testing");
