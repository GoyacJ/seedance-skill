#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from pathlib import Path

from seedance_skill_common import (
    DEFAULT_ARK_BASE_URL,
    SEEDANCE_TASK_PATH,
    blocked_payload,
    build_seedance_request,
    download_file,
    ensure_output_dir,
    env,
    error_payload,
    extract_seedance_outputs,
    ffmpeg_extract_cover,
    http_json,
    print_json,
    require_values,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用豆包 Seedance 文生视频接口生成短视频。")
    parser.add_argument("--prompt", required=True, help="视频创意或详细提示词。")
    parser.add_argument("--output-dir", help="输出目录；不传时写入 outputs/<timestamp>/。")
    parser.add_argument("--base-url", default=env("ARK_BASE_URL") or DEFAULT_ARK_BASE_URL, help="Seedance Base URL。")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="轮询任务状态的间隔秒数。")
    parser.add_argument("--max-polls", type=int, default=120, help="最多轮询次数。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = ensure_output_dir(args.output_dir)
    request_payload = build_seedance_request(args.prompt)
    request_file = output_dir / "request.json"
    result_file = output_dir / "generation.json"
    write_json(request_file, request_payload)

    api_key = env("ARK_API_KEY")
    if not api_key:
        payload = blocked_payload(
            "缺少 Seedance 凭证，无法发起真实生成。",
            missing=["ARK_API_KEY"],
            output_dir=str(output_dir),
        )
        write_json(result_file, payload)
        print_json(payload)
        return 1

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    task_url = args.base_url.rstrip("/") + SEEDANCE_TASK_PATH

    try:
        create_payload = http_json("POST", task_url, headers=headers, payload=request_payload, timeout=120)
        task_id = create_payload["id"]
        task_payload: dict[str, object] = create_payload
        for _ in range(args.max_polls):
            task_payload = http_json("GET", f"{task_url}/{task_id}", headers=headers, timeout=120)
            status = str(task_payload.get("status", "")).lower()
            if status in {"succeeded", "failed", "expired", "cancelled"}:
                break
            time.sleep(args.poll_interval)
        else:
            payload = blocked_payload(
                "轮询超时，任务仍未完成。",
                task_id=task_id,
                output_dir=str(output_dir),
            )
            write_json(result_file, payload)
            print_json(payload)
            return 0

        status = str(task_payload.get("status", "")).lower()
        if status != "succeeded":
            payload = blocked_payload(
                "Seedance 任务未成功完成。",
                task_id=task_id,
                task_status=status,
                task=task_payload,
                output_dir=str(output_dir),
            )
            write_json(result_file, payload)
            print_json(payload)
            return 0

        extracted = extract_seedance_outputs(task_payload)
        video_path = None
        cover_path = None
        if extracted["video_url"]:
            video_path = str(download_file(extracted["video_url"], output_dir / "video.mp4"))
        if extracted["cover_url"]:
            cover_path = str(download_file(extracted["cover_url"], output_dir / "cover.png"))
        elif video_path:
            fallback = ffmpeg_extract_cover(Path(video_path), output_dir / "cover.png")
            cover_path = str(fallback) if fallback else None

        payload = {
            "status": "ok",
            "task_id": task_id,
            "request": request_payload,
            "task": task_payload,
            "output_dir": str(output_dir),
            "artifacts": {
                "request": str(request_file),
                "result": str(result_file),
                "video": video_path,
                "cover": cover_path,
            },
        }
        write_json(result_file, payload)
        print_json(payload)
        return 0
    except Exception as exc:  # noqa: BLE001
        payload = error_payload(
            "Seedance 调用失败。",
            detail=str(exc),
            output_dir=str(output_dir),
        )
        write_json(result_file, payload)
        print_json(payload)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
