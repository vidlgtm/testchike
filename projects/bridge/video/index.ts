// THE CONTRACT between the fixed engine (src/engine/Short.tsx, src/Root.tsx) and a video project.
// Every project MUST export exactly these names from here. Everything else in the folder is private to the video.
export { World, loadKit } from "./world";
export type { Kit } from "./build";
export { FPS, TOTAL, FLASH_AT, SHOTS, layersAt, dofAt } from "./story";
