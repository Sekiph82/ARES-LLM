from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path

from local_llm.media_artifact import MediaPlan, plan_media, slugify


def _safe_json(data: object) -> str:
    return json.dumps(data, indent=2)


def _package_json(title: str) -> str:
    package_name = slugify(title, fallback="ares-remotion-video")
    return _safe_json(
        {
            "name": package_name,
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "preview": "remotion studio src/index.ts",
                "render": "remotion render src/index.ts AresVideo out/ares-video.mp4",
            },
            "dependencies": {
                "@remotion/cli": "latest",
                "@remotion/player": "latest",
                "remotion": "latest",
                "react": "latest",
                "react-dom": "latest",
            },
            "devDependencies": {
                "@types/react": "latest",
                "@types/react-dom": "latest",
                "typescript": "latest",
            },
        }
    )


def _tsconfig_json() -> str:
    return _safe_json(
        {
            "compilerOptions": {
                "jsx": "react-jsx",
                "lib": ["dom", "es2022"],
                "module": "esnext",
                "moduleResolution": "bundler",
                "noEmit": True,
                "strict": True,
                "target": "es2022",
            },
            "include": ["src"],
        }
    )


def _index_ts() -> str:
    return """import {registerRoot} from 'remotion';
import {Root} from './Root';

registerRoot(Root);
"""


def _root_tsx(plan: MediaPlan, fps: int, width: int, height: int) -> str:
    duration = max(1, int(round(sum(shot.duration_sec for shot in plan.shots) * fps)))
    return f"""import React from 'react';
import {{Composition}} from 'remotion';
import {{AresVideo}} from './Video';
import sceneData from '../public/scene-data.json';

export const Root: React.FC = () => {{
  return (
    <Composition
      id="AresVideo"
      component={{AresVideo}}
      durationInFrames={duration}
      fps={fps}
      width={width}
      height={height}
      defaultProps={{{{sceneData}}}}
    />
  );
}};
"""


def _video_tsx() -> str:
    return """import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import './style.css';

type Shot = {
  index: number;
  title: string;
  prompt: string;
  duration_sec: number;
  camera: string;
  motion: string;
  palette: string[];
};

type SceneData = {
  title: string;
  brief: string;
  style: string;
  shots: Shot[];
};

export const AresVideo: React.FC<{sceneData: SceneData}> = ({sceneData}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const shotFrameCount = Math.max(1, Math.floor(durationInFrames / sceneData.shots.length));
  const shotIndex = Math.min(sceneData.shots.length - 1, Math.floor(frame / shotFrameCount));
  const shot = sceneData.shots[shotIndex];
  const localFrame = frame - shotIndex * shotFrameCount;
  const progress = localFrame / shotFrameCount;
  const pulse = spring({frame: localFrame, fps, config: {damping: 18, stiffness: 80}});
  const drift = interpolate(progress, [0, 1], [-26, 26]);
  const palette = shot.palette;

  return (
    <AbsoluteFill
      className="scene"
      style={{
        background: `linear-gradient(135deg, ${palette[0]}, ${palette[4]})`,
      }}
    >
      <div className="stars" />
      <div className="moon" />
      <div className="mountain mountainLeft" />
      <div className="mountain mountainRight" />

      <div className="ninja" style={{transform: `translateX(${drift}px) scale(${0.9 + pulse * 0.1})`}}>
        <div className="ninjaHead" />
        <div className="ninjaBody" />
        <div className="scarf" />
        <div className="sword" />
      </div>

      <div className="dragon" style={{transform: `translateX(${-drift}px) rotate(${Math.sin(progress * Math.PI) * 2}deg)`}}>
        <div className="dragonWing top" />
        <div className="dragonWing bottom" />
        <div className="dragonBody" />
        <div className="dragonHead" />
        <div className="fire" />
      </div>

      <div className="clash" style={{transform: `scale(${0.7 + pulse * 0.35})`}} />

      <header className="title">
        <span>{sceneData.style}</span>
        <h1>{sceneData.title}</h1>
      </header>

      <footer className="caption">
        <strong>Shot {shot.index}: {shot.title}</strong>
        <p>{shot.prompt}</p>
      </footer>
    </AbsoluteFill>
  );
};
"""


def _style_css() -> str:
    return """:root {
  font-family: Inter, Segoe UI, Arial, sans-serif;
}

.scene {
  color: white;
  overflow: hidden;
}

.stars {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 12% 22%, #38bdf8 0 2px, transparent 3px),
    radial-gradient(circle at 44% 18%, #e0f2fe 0 1px, transparent 2px),
    radial-gradient(circle at 72% 32%, #38bdf8 0 2px, transparent 3px),
    radial-gradient(circle at 82% 72%, #e0f2fe 0 1px, transparent 2px),
    radial-gradient(circle at 30% 80%, #38bdf8 0 2px, transparent 3px);
}

.moon {
  position: absolute;
  right: 132px;
  top: 82px;
  width: 92px;
  height: 92px;
  border-radius: 50%;
  background: #e5e7eb;
  box-shadow: 0 0 44px rgba(229, 231, 235, 0.28);
}

.moon::after {
  content: "";
  position: absolute;
  right: -8px;
  top: 0;
  width: 92px;
  height: 92px;
  border-radius: 50%;
  background: #111827;
}

.mountain {
  position: absolute;
  bottom: 0;
  width: 520px;
  height: 310px;
  background: #0b1220;
  clip-path: polygon(0 100%, 44% 0, 100% 100%);
}

.mountainLeft {
  left: -60px;
}

.mountainRight {
  right: -70px;
  transform: scaleX(1.2);
}

.ninja {
  position: absolute;
  left: 190px;
  bottom: 150px;
  width: 180px;
  height: 220px;
}

.ninjaHead {
  position: absolute;
  left: 66px;
  top: 10px;
  width: 58px;
  height: 58px;
  border: 3px solid #f8fafc;
  border-radius: 50%;
  background: #050505;
}

.ninjaHead::after {
  content: "";
  position: absolute;
  left: 12px;
  top: 27px;
  width: 34px;
  height: 5px;
  background: #f8fafc;
}

.ninjaBody {
  position: absolute;
  left: 48px;
  top: 72px;
  width: 82px;
  height: 118px;
  background: #111827;
  border: 3px solid #f8fafc;
  clip-path: polygon(18% 0, 82% 0, 100% 100%, 0 100%);
}

.scarf {
  position: absolute;
  left: 16px;
  top: 66px;
  width: 96px;
  height: 24px;
  background: #ef4444;
  clip-path: polygon(100% 0, 0 30%, 88% 100%);
}

.sword {
  position: absolute;
  left: 98px;
  top: 74px;
  width: 198px;
  height: 5px;
  background: #f8fafc;
  transform: rotate(-35deg);
  transform-origin: left center;
  box-shadow: 0 0 18px rgba(248, 250, 252, 0.55);
}

.dragon {
  position: absolute;
  right: 138px;
  top: 190px;
  width: 390px;
  height: 210px;
}

.dragonBody {
  position: absolute;
  left: 70px;
  top: 92px;
  width: 230px;
  height: 44px;
  border-radius: 999px;
  background: #166534;
  box-shadow: inset 0 -8px 0 #f59e0b;
}

.dragonHead {
  position: absolute;
  right: 26px;
  top: 66px;
  width: 112px;
  height: 76px;
  background: #166534;
  clip-path: polygon(0 22%, 78% 0, 100% 50%, 76% 100%, 0 78%);
  border: 2px solid #bbf7d0;
}

.dragonHead::after {
  content: "";
  position: absolute;
  right: 28px;
  top: 25px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #f8fafc;
}

.dragonWing {
  position: absolute;
  background: #14532d;
  border: 2px solid #bbf7d0;
}

.dragonWing.top {
  left: 150px;
  top: 10px;
  width: 138px;
  height: 92px;
  clip-path: polygon(0 100%, 42% 0, 100% 80%);
}

.dragonWing.bottom {
  left: 126px;
  top: 120px;
  width: 160px;
  height: 90px;
  clip-path: polygon(0 0, 100% 18%, 36% 100%);
}

.fire {
  position: absolute;
  right: -58px;
  top: 80px;
  width: 98px;
  height: 46px;
  background: #f97316;
  clip-path: polygon(0 50%, 62% 0, 100% 50%, 58% 100%);
  filter: drop-shadow(0 0 18px rgba(249, 115, 22, 0.8));
}

.clash {
  position: absolute;
  left: 446px;
  top: 268px;
  width: 88px;
  height: 88px;
  border: 8px double #facc15;
  border-radius: 50%;
  box-shadow: 0 0 28px rgba(250, 204, 21, 0.7);
}

.title {
  position: absolute;
  left: 54px;
  top: 44px;
}

.title span {
  color: #f97316;
  font-size: 22px;
  font-weight: 700;
  text-transform: uppercase;
}

.title h1 {
  max-width: 760px;
  margin: 8px 0 0;
  font-size: 56px;
  line-height: 1;
}

.caption {
  position: absolute;
  left: 54px;
  right: 54px;
  bottom: 42px;
  padding-top: 18px;
  border-top: 3px solid #38bdf8;
}

.caption strong {
  display: block;
  font-size: 28px;
}

.caption p {
  max-width: 900px;
  margin: 8px 0 0;
  color: #d4d4d8;
  font-size: 20px;
  line-height: 1.35;
}
"""


def _readme(plan: MediaPlan, fps: int, width: int, height: int) -> str:
    return f"""# {plan.title}

Generated by Ares as a Remotion-ready React video project.

## What This Is

This project turns the Ares storyboard into a programmatic video composition.
React code is the source of truth, so the scene can be edited like a normal
frontend project.

## Run

```powershell
npm install
npm run preview
```

Render MP4:

```powershell
npm run render
```

Composition:

- ID: `AresVideo`
- Size: `{width}x{height}`
- FPS: `{fps}`

## License Note

Remotion has its own license terms. Check the Remotion license before using it
commercially.
"""


def create_remotion_artifact(
    brief: str,
    root: Path,
    plan: MediaPlan | None = None,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
) -> Path:
    plan = plan or plan_media(brief)
    project = root / "remotion"
    src = project / "src"
    public = project / "public"
    src.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)

    scene_data = asdict(plan)
    (project / "package.json").write_text(_package_json(plan.title), encoding="utf-8")
    (project / "tsconfig.json").write_text(_tsconfig_json(), encoding="utf-8")
    (project / "README.md").write_text(_readme(plan, fps, width, height), encoding="utf-8")
    (src / "index.ts").write_text(_index_ts(), encoding="utf-8")
    (src / "Root.tsx").write_text(_root_tsx(plan, fps, width, height), encoding="utf-8")
    (src / "Video.tsx").write_text(_video_tsx(), encoding="utf-8")
    (src / "style.css").write_text(_style_css(), encoding="utf-8")
    (public / "scene-data.json").write_text(_safe_json(scene_data), encoding="utf-8")
    return project


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Remotion-ready Ares video project.")
    parser.add_argument("brief", nargs="+")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    brief = " ".join(args.brief)
    root = args.root / f"remotion-{slugify(brief)}"
    root.mkdir(parents=True, exist_ok=True)
    project = create_remotion_artifact(brief, root=root, fps=args.fps, width=args.width, height=args.height)
    print(f"Created Remotion project: {project}")


if __name__ == "__main__":
    main()
