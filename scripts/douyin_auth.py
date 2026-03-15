#!/usr/bin/env python3
from __future__ import annotations

import argparse

from seedance_skill_common import (
    DOUYIN_ACCESS_TOKEN_URL,
    DOUYIN_REFRESH_ACCESS_TOKEN_URL,
    DOUYIN_RENEW_REFRESH_TOKEN_URL,
    build_douyin_authorize_url,
    env,
    http_form,
    print_json,
    require_values,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="处理抖音 OAuth 授权、换 token 和刷新 token。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    authorize = subparsers.add_parser("authorize", help="生成抖音授权链接。")
    authorize.add_argument("--client-key", default=env("DOUYIN_CLIENT_KEY"))
    authorize.add_argument("--redirect-uri", default=env("DOUYIN_REDIRECT_URI"))
    authorize.add_argument("--scope", default="video.create.bind,user_info")
    authorize.add_argument("--state")
    authorize.add_argument("--optional-scope")

    exchange = subparsers.add_parser("exchange", help="用 code 换 access_token。")
    exchange.add_argument("--code", required=True)
    exchange.add_argument("--client-key", default=env("DOUYIN_CLIENT_KEY"))
    exchange.add_argument("--client-secret", default=env("DOUYIN_CLIENT_SECRET"))

    refresh = subparsers.add_parser("refresh", help="刷新 access_token。")
    refresh.add_argument("--refresh-token", required=True)
    refresh.add_argument("--client-key", default=env("DOUYIN_CLIENT_KEY"))

    renew = subparsers.add_parser("renew-refresh-token", help="续期 refresh_token。")
    renew.add_argument("--refresh-token", required=True)
    renew.add_argument("--client-key", default=env("DOUYIN_CLIENT_KEY"))

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "authorize":
        values, missing = require_values(
            {
                "DOUYIN_CLIENT_KEY": args.client_key,
                "DOUYIN_REDIRECT_URI": args.redirect_uri,
            }
        )
        if missing:
            print_json({"status": "blocked", "message": "缺少授权参数。", "missing": missing})
            return 0
        payload = {
            "status": "ok",
            "auth_url": build_douyin_authorize_url(
                client_key=values["DOUYIN_CLIENT_KEY"],
                redirect_uri=values["DOUYIN_REDIRECT_URI"],
                scope=args.scope,
                state=args.state,
                optional_scope=args.optional_scope,
            ),
            "scope": args.scope,
            "state": args.state,
        }
        print_json(payload)
        return 0

    if args.command == "exchange":
        values, missing = require_values(
            {
                "DOUYIN_CLIENT_KEY": args.client_key,
                "DOUYIN_CLIENT_SECRET": args.client_secret,
            }
        )
        if missing:
            print_json({"status": "blocked", "message": "缺少换 token 所需参数。", "missing": missing})
            return 0
        payload = http_form(
            "POST",
            DOUYIN_ACCESS_TOKEN_URL,
            fields={
                "client_key": values["DOUYIN_CLIENT_KEY"],
                "client_secret": values["DOUYIN_CLIENT_SECRET"],
                "code": args.code,
                "grant_type": "authorization_code",
            },
        )
        print_json({"status": "ok", "result": payload})
        return 0

    if args.command == "refresh":
        values, missing = require_values({"DOUYIN_CLIENT_KEY": args.client_key})
        if missing:
            print_json({"status": "blocked", "message": "缺少刷新 access_token 所需参数。", "missing": missing})
            return 0
        payload = http_form(
            "POST",
            DOUYIN_REFRESH_ACCESS_TOKEN_URL,
            fields={
                "client_key": values["DOUYIN_CLIENT_KEY"],
                "grant_type": "refresh_token",
                "refresh_token": args.refresh_token,
            },
        )
        print_json({"status": "ok", "result": payload})
        return 0

    values, missing = require_values({"DOUYIN_CLIENT_KEY": args.client_key})
    if missing:
        print_json({"status": "blocked", "message": "缺少续期 refresh_token 所需参数。", "missing": missing})
        return 0
    payload = http_form(
        "POST",
        DOUYIN_RENEW_REFRESH_TOKEN_URL,
        fields={
            "client_key": values["DOUYIN_CLIENT_KEY"],
            "refresh_token": args.refresh_token,
        },
    )
    print_json({"status": "ok", "result": payload})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
