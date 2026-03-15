#!/usr/bin/env python3
from __future__ import annotations

import argparse

from seedance_skill_common import (
    build_publish_bundle,
    ensure_output_dir,
    print_json,
    publish_bundle_markdown,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成抖音发布用的文案、话题和素材清单。")
    parser.add_argument("--idea", required=True, help="用户原始想法。")
    parser.add_argument("--prompt", required=True, help="实际用于视频生成的提示词。")
    parser.add_argument("--video-path", help="视频文件路径。")
    parser.add_argument("--cover-path", help="封面文件路径。")
    parser.add_argument(
        "--mode",
        default="preview",
        choices=["preview", "openapi", "h5", "manual-package"],
        help="当前发布模式。",
    )
    parser.add_argument("--title", help="手动指定标题，不传时自动生成。")
    parser.add_argument("--hashtag", action="append", default=[], help="额外话题，可重复传入。")
    parser.add_argument("--output-dir", help="输出目录；不传时写入 outputs/<timestamp>/。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = ensure_output_dir(args.output_dir)
    bundle = build_publish_bundle(
        idea=args.idea,
        prompt=args.prompt,
        mode=args.mode,
        video_path=args.video_path,
        cover_path=args.cover_path,
        title=args.title,
        hashtags=args.hashtag or None,
    )
    publish_json = output_dir / "publish.json"
    publish_md = output_dir / "publish.md"
    write_json(publish_json, bundle)
    publish_md.write_text(publish_bundle_markdown(bundle), encoding="utf-8")
    payload = {
        "status": "ok",
        "output_dir": str(output_dir),
        "package": bundle,
        "artifacts": {
            "publish_json": str(publish_json),
            "publish_md": str(publish_md),
        },
    }
    print_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
