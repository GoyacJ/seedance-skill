#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from seedance_skill_common import (
    DOUYIN_CREATE_VIDEO_URL,
    DOUYIN_UPLOAD_VIDEO_URL,
    blocked_payload,
    ensure_output_dir,
    env,
    error_payload,
    http_json,
    http_multipart_file,
    print_json,
    require_values,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="通过抖音 OpenAPI 上传并创建视频。")
    parser.add_argument("--video-path", required=True, help="待发布视频路径。")
    parser.add_argument("--title", required=True, help="视频标题，可包含话题。")
    parser.add_argument("--open-id", default=env("DOUYIN_OPEN_ID"), help="用户 open_id。")
    parser.add_argument("--access-token", default=env("DOUYIN_ACCESS_TOKEN"), help="用户 access_token。")
    parser.add_argument("--client-key", default=env("DOUYIN_CLIENT_KEY"))
    parser.add_argument("--client-secret", default=env("DOUYIN_CLIENT_SECRET"))
    parser.add_argument("--private-status", type=int, default=0, help="0=公开，1=自己可见，2=好友可见。")
    parser.add_argument("--download-type", type=int, default=0, help="0=允许下载，1=作者不允许下载。")
    parser.add_argument("--cover-tsp", type=float, default=0.5, help="默认封面取样秒数。")
    parser.add_argument("--output-dir", help="输出目录；不传时写入 outputs/<timestamp>/。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = ensure_output_dir(args.output_dir)
    result_file = output_dir / "openapi_publish.json"
    video_path = Path(args.video_path).expanduser().resolve()

    required = {
        "DOUYIN_CLIENT_KEY": args.client_key,
        "DOUYIN_CLIENT_SECRET": args.client_secret,
        "DOUYIN_ACCESS_TOKEN": args.access_token,
        "DOUYIN_OPEN_ID": args.open_id,
    }
    values, missing = require_values(required)

    if missing:
        payload = blocked_payload(
            "缺少自动发布所需凭证。",
            missing=missing,
            recommended_fallback="manual-package",
            output_dir=str(output_dir),
        )
        write_json(result_file, payload)
        print_json(payload)
        return 1

    try:
        upload_payload = http_multipart_file(
            DOUYIN_UPLOAD_VIDEO_URL,
            query={"open_id": values["DOUYIN_OPEN_ID"]},
            file_field="video",
            file_path=video_path,
            headers={"access-token": values["DOUYIN_ACCESS_TOKEN"]},
        )
        video_id = upload_payload["data"]["video"]["video_id"]
        create_payload = http_json(
            "POST",
            f"{DOUYIN_CREATE_VIDEO_URL}?open_id={values['DOUYIN_OPEN_ID']}",
            headers={
                "access-token": values["DOUYIN_ACCESS_TOKEN"],
                "content-type": "application/json",
            },
            payload={
                "video_id": video_id,
                "text": args.title,
                "cover_tsp": args.cover_tsp,
                "download_type": args.download_type,
                "private_status": args.private_status,
            },
            timeout=180,
        )
        payload = {
            "status": "ok",
            "message": "已完成视频上传与创建请求。",
            "output_dir": str(output_dir),
            "upload": upload_payload,
            "create": create_payload,
        }
        write_json(result_file, payload)
        print_json(payload)
        return 0
    except Exception as exc:  # noqa: BLE001
        payload = error_payload(
            "抖音自动发布失败。",
            detail=str(exc),
            recommended_fallback="manual-package",
            output_dir=str(output_dir),
        )
        write_json(result_file, payload)
        print_json(payload)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
