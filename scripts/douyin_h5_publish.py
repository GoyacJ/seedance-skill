#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from seedance_skill_common import (
    DOUYIN_CLIENT_TOKEN_URL,
    DOUYIN_OPEN_TICKET_URL,
    DOUYIN_VIDEO_SHARE_RESULT_URL,
    build_h5_share_schema,
    build_h5_signature,
    ensure_output_dir,
    env,
    http_json,
    http_request,
    new_state,
    print_json,
    require_values,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成抖音 H5 投稿所需 schema 与扫码 payload。")
    parser.add_argument("--video-path", required=True, help="视频 URL 或可访问路径。")
    parser.add_argument("--title", help="视频标题。")
    parser.add_argument("--hashtag", action="append", default=[], help="预设话题，可重复传入。")
    parser.add_argument("--state", help="用于串联分享结果查询的 state。")
    parser.add_argument("--client-key", default=env("DOUYIN_CLIENT_KEY"))
    parser.add_argument("--client-secret", default=env("DOUYIN_CLIENT_SECRET"))
    parser.add_argument("--ticket", default=env("DOUYIN_OPEN_TICKET"))
    parser.add_argument("--nonce-str", default="seedance-h5")
    parser.add_argument("--timestamp", help="秒级时间戳。")
    parser.add_argument("--signature", help="显式传入签名；不传时使用 ticket 计算。")
    parser.add_argument("--share-to-publish", action="store_true", help="直接分享到发布页。")
    parser.add_argument("--share-to-type", type=int, default=0, help="0=投稿，1=转发到日常。")
    parser.add_argument("--output-dir", help="输出目录；不传时写入 outputs/<timestamp>/。")
    return parser.parse_args()


def fetch_client_token(client_key: str, client_secret: str) -> str:
    payload = http_json(
        "POST",
        DOUYIN_CLIENT_TOKEN_URL,
        payload={
            "grant_type": "client_credential",
            "client_key": client_key,
            "client_secret": client_secret,
        },
    )
    return payload["data"]["access_token"]


def fetch_open_ticket(access_token: str) -> str:
    _, _, body = http_request(
        "GET",
        DOUYIN_OPEN_TICKET_URL,
        headers={
            "access-token": access_token,
            "content-type": "application/json",
        },
    )
    payload = json.loads(body.decode("utf-8"))
    return payload["data"]["ticket"]


def main() -> int:
    args = parse_args()
    output_dir = ensure_output_dir(args.output_dir)
    state = args.state or new_state("h5")
    timestamp = args.timestamp or str(int(time.time()))
    qr_payload_file = output_dir / "qr_payload.txt"
    result_file = output_dir / "h5_publish.json"

    client_key = args.client_key
    signature = args.signature
    ticket = args.ticket

    values, missing = require_values(
        {
            "DOUYIN_CLIENT_KEY": args.client_key,
            "DOUYIN_CLIENT_SECRET": args.client_secret,
        }
    )
    if missing:
        payload = {
            "status": "blocked",
            "message": "缺少 H5 投稿所需凭证，无法生成 schema。",
            "missing": missing,
            "recommended_fallback": "manual-package",
            "output_dir": str(output_dir),
        }
        write_json(result_file, payload)
        print_json(payload)
        return 1

    client_key = values["DOUYIN_CLIENT_KEY"]

    if not signature and not ticket:
        try:
            client_token = fetch_client_token(values["DOUYIN_CLIENT_KEY"], values["DOUYIN_CLIENT_SECRET"])
            ticket = fetch_open_ticket(client_token)
        except Exception as exc:  # noqa: BLE001
            payload = {
                "status": "error",
                "message": "获取 H5 投稿 ticket 失败。",
                "detail": str(exc),
                "recommended_fallback": "manual-package",
                "output_dir": str(output_dir),
            }
            write_json(result_file, payload)
            print_json(payload)
            return 1

    if not signature:
        signature = build_h5_signature(ticket, args.nonce_str, timestamp)

    schema_params: dict[str, object] = {
        "client_key": client_key,
        "nonce_str": args.nonce_str,
        "timestamp": timestamp,
        "signature": signature,
        "state": state,
        "video_path": args.video_path,
        "share_to_type": args.share_to_type,
    }
    if args.title:
        schema_params["title"] = args.title
    if args.hashtag:
        schema_params["hashtag_list"] = json.dumps(args.hashtag, ensure_ascii=False)
    if args.share_to_publish:
        schema_params["share_to_publish"] = 1

    schema = build_h5_share_schema(schema_params)
    qr_payload_file.write_text(schema, encoding="utf-8")

    payload = {"status": "ok", "message": "已生成 H5 投稿 schema。", "schema": schema}
    payload.update(
        {
            "state": state,
            "share_result_endpoint": DOUYIN_VIDEO_SHARE_RESULT_URL,
            "output_dir": str(output_dir),
            "artifacts": {
                "qr_payload": str(qr_payload_file),
                "result": str(result_file),
            },
        }
    )
    write_json(result_file, payload)
    print_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
