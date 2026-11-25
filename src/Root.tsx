// FIXED. One composition ("Short", 1080x1920) whose length and fps come from the active project's story.ts.
// The active project is chosen with the PROJECT env var (see remotion.config.ts), e.g. PROJECT=bridge.
import React from "react";
import { Composition } from "remotion";
import { Short, SHORT_FRAMES } from "./engine/Short";
import { FPS } from "@project";

export const RemotionRoot: React.FC = () => (
  <Composition id="Short" component={Short} durationInFrames={SHORT_FRAMES} fps={FPS} width={1080} height={1920} />
);
