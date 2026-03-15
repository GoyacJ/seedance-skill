from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import ssl
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


DEFAULT_ARK_BASE_URL = "https://ark.cn-beijing.volces.com"
SEEDANCE_TASK_PATH = "/api/v3/contents/generations/tasks"
SEEDANCE_DEFAULT_MODEL = "doubao-seedance-2-0-260128"
DOUYIN_AUTHORIZE_URL = "https://open.douyin.com/platform/oauth/connect/"
DOUYIN_ACCESS_TOKEN_URL = "https://open.douyin.com/oauth/access_token/"
DOUYIN_REFRESH_ACCESS_TOKEN_URL = "https://open.douyin.com/oauth/refresh_token/"
DOUYIN_RENEW_REFRESH_TOKEN_URL = "https://open.douyin.com/oauth/renew_refresh_token/"
DOUYIN_CLIENT_TOKEN_URL = "https://open.douyin.com/oauth/client_token/"
DOUYIN_OPEN_TICKET_URL = "https://open.douyin.com/open/getticket/"
DOUYIN_UPLOAD_VIDEO_URL = "https://open.douyin.com/api/douyin/v1/video/upload_video/"
DOUYIN_CREATE_VIDEO_URL = "https://open.douyin.com/api/douyin/v1/video/create_video/"
DOUYIN_VIDEO_SHARE_RESULT_URL = "https://open.douyin.com/share-id/"
DOUYIN_H5_SCHEMA_PREFIX = "snssdk1128://openplatform/share"

STOP_WORDS = {
    "一个",
    "一些",
    "这个",
    "那个",
    "然后",
    "可以",
    "需要",
    "想法",
    "视频",
    "短视频",
    "抖音",
    "生成",
    "发布",
    "画面",
    "镜头",
}

KEYWORD_TAGS = {
    "猫": "萌宠日常",
    "狗": "萌宠日常",
    "雨": "雨夜氛围",
    "夜": "夜景故事",
    "城市": "城市漫游",
    "街": "街头观察",
    "早餐": "烟火日常",
    "老街": "烟火日常",
    "旅行": "旅行灵感",
    "海": "海边氛围",
    "山": "自然疗愈",
    "咖啡": "生活方式",
    "电影": "电影感短片",
    "纪实": "纪实氛围",
    "复古": "复古质感",
    "赛博": "未来感画面",
}


class ScriptError(RuntimeError):
    """Raised when a CLI script cannot complete its task."""


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def ensure_output_dir(output_dir: str | Path | None) -> Path:
    if output_dir:
        path = Path(output_dir).expanduser().resolve()
    else:
        path = (Path.cwd() / "outputs" / timestamp_slug()).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_seedance_request(prompt: str) -> dict[str, Any]:
    text = normalize_text(prompt)
    return {
        "model": SEEDANCE_DEFAULT_MODEL,
        "content": [{"type": "text", "text": text}],
        "ratio": "9:16",
        "duration": 5,
        "resolution": "720p",
        "generate_audio": True,
        "watermark": False,
        "return_last_frame": True,
    }


def slugify(value: str, max_length: int = 32) -> str:
    collapsed = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", normalize_text(value))
    collapsed = collapsed.strip("-") or "seedance-video"
    return collapsed[:max_length].rstrip("-") or "seedance-video"


def choose_title(idea: str, prompt: str) -> str:
    base = normalize_text(idea or prompt)
    if not base:
        return "Seedance 抖音短视频"
    title = re.sub(r"[。！？,.!?\-]+$", "", base)
    return title[:28] if len(title) > 28 else title


def extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]{2,8}", text)
    keywords: list[str] = []
    for token in tokens:
        if token in STOP_WORDS or token.isdigit():
            continue
        if token not in keywords:
            keywords.append(token)
    return keywords


def choose_hashtags(idea: str, prompt: str) -> list[str]:
    source = f"{idea} {prompt}"
    hashtags: list[str] = []
    for keyword, tag in KEYWORD_TAGS.items():
        if keyword in source and tag not in hashtags:
            hashtags.append(tag)
    for keyword in extract_keywords(source):
        if len(hashtags) >= 5:
            break
        candidate = keyword if keyword.startswith("#") else keyword
        if re.fullmatch(r"[\u4e00-\u9fff]+", candidate) and len(candidate) > 4:
            continue
        if candidate not in hashtags and 1 < len(candidate) <= 12:
            hashtags.append(candidate)
    for fallback in ["短视频创作", "Seedance生成", "抖音灵感"]:
        if fallback not in hashtags:
            hashtags.append(fallback)
        if len(hashtags) >= 5:
            break
    return hashtags[:5]


def build_publish_bundle(
    *,
    idea: str,
    prompt: str,
    mode: str,
    video_path: str | None = None,
    cover_path: str | None = None,
    title: str | None = None,
    hashtags: list[str] | None = None,
) -> dict[str, Any]:
    publish_title = title or choose_title(idea, prompt)
    publish_hashtags = hashtags or choose_hashtags(idea, prompt)
    return {
        "mode": mode,
        "idea": normalize_text(idea),
        "prompt": normalize_text(prompt),
        "title": publish_title,
        "hashtags": publish_hashtags,
        "cover_strategy": (
            "优先使用 Seedance 返回的尾帧作为封面；尾帧不可用时，回退为从成片中抽取首个稳定画面。"
        ),
        "assets": {
            "video_path": video_path,
            "cover_path": cover_path,
        },
        "publish_text": publish_title + "".join(f" #{tag}" for tag in publish_hashtags),
    }


def publish_bundle_markdown(bundle: dict[str, Any]) -> str:
    hashtags = " ".join(f"#{tag}" for tag in bundle["hashtags"])
    assets = bundle.get("assets", {})
    return "\n".join(
        [
            f"# {bundle['title']}",
            "",
            "## 发布模式",
            bundle["mode"],
            "",
            "## 视频想法",
            bundle["idea"],
            "",
            "## 生成提示词",
            bundle["prompt"],
            "",
            "## 标题与话题",
            bundle["title"],
            hashtags,
            "",
            "## 封面策略",
            bundle["cover_strategy"],
            "",
            "## 素材路径",
            f"- video: {assets.get('video_path')}",
            f"- cover: {assets.get('cover_path')}",
            "",
        ]
    ).strip() + "\n"


def build_douyin_authorize_url(
    *,
    client_key: str,
    redirect_uri: str,
    scope: str,
    state: str | None = None,
    optional_scope: str | None = None,
) -> str:
    params: dict[str, str] = {
        "client_key": client_key,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": redirect_uri,
    }
    if state:
        params["state"] = state
    if optional_scope:
        params["optionalScope"] = optional_scope
    return DOUYIN_AUTHORIZE_URL + "?" + urlencode(params)


def build_h5_signature(ticket: str, nonce_str: str, timestamp: str) -> str:
    string_to_sign = f"nonce_str={nonce_str}&ticket={ticket}&timestamp={timestamp}"
    return hashlib.md5(string_to_sign.encode("utf-8")).hexdigest()


def build_h5_share_schema(params: dict[str, Any]) -> str:
    query_params = {"share_type": "h5", **params}
    return f"{DOUYIN_H5_SCHEMA_PREFIX}?{urlencode(query_params, doseq=True)}"


def new_state(prefix: str = "seedance") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 60,
) -> tuple[int, dict[str, str], bytes]:
    request = Request(url=url, data=body, method=method.upper(), headers=headers or {})
    context = _ssl_context()
    with urlopen(request, timeout=timeout, context=context) as response:
        return response.status, dict(response.headers.items()), response.read()


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    request_headers = dict(headers or {})
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    _, _, response_body = http_request(method, url, headers=request_headers, body=body, timeout=timeout)
    return json.loads(response_body.decode("utf-8"))


def http_form(
    method: str,
    url: str,
    *,
    fields: dict[str, str],
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    request_headers = dict(headers or {})
    request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    body = urlencode(fields).encode("utf-8")
    _, _, response_body = http_request(method, url, headers=request_headers, body=body, timeout=timeout)
    return json.loads(response_body.decode("utf-8"))


def http_multipart_file(
    url: str,
    *,
    query: dict[str, str],
    file_field: str,
    file_path: Path,
    headers: dict[str, str] | None = None,
    timeout: int = 300,
) -> dict[str, Any]:
    boundary = f"----seedance-skill-{uuid.uuid4().hex}"
    file_bytes = file_path.read_bytes()
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8"),
        file_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    request_headers = dict(headers or {})
    request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    request_url = url + "?" + urlencode(query)
    _, _, response_body = http_request(
        "POST",
        request_url,
        headers=request_headers,
        body=b"".join(parts),
        timeout=timeout,
    )
    return json.loads(response_body.decode("utf-8"))


def download_file(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url=url, method="GET")
    context = _ssl_context()
    with urlopen(request, timeout=300, context=context) as response:
        destination.write_bytes(response.read())
    return destination


def _ssl_context() -> ssl.SSLContext | None:
    cafile = env("SSL_CERT_FILE")
    if cafile:
        return ssl.create_default_context(cafile=cafile)
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def is_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _collect_urls(value: Any, breadcrumbs: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            matches.extend(_collect_urls(item, (*breadcrumbs, str(key))))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            matches.extend(_collect_urls(item, (*breadcrumbs, str(index))))
    elif isinstance(value, str) and is_url(value):
        matches.append((".".join(breadcrumbs), value))
    return matches


def extract_seedance_outputs(payload: dict[str, Any]) -> dict[str, str | None]:
    matches = _collect_urls(payload)
    video_url = None
    cover_url = None
    for key_path, value in matches:
        lowered = f"{key_path}::{value}".lower()
        if video_url is None and any(ext in lowered for ext in (".mp4", ".mov", ".webm")):
            video_url = value
        if cover_url is None and any(token in lowered for token in ("last_frame", "lastframe", "cover", ".png", ".jpg", ".jpeg")):
            cover_url = value
    return {"video_url": video_url, "cover_url": cover_url}


def ffmpeg_extract_cover(video_path: Path, cover_path: Path) -> Path | None:
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vf",
                "select=eq(n\\,0)",
                "-vframes",
                "1",
                str(cover_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return cover_path if cover_path.exists() else None


def require_values(mapping: dict[str, str | None], *, allow_empty: bool = False) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    missing: list[str] = []
    for key, value in mapping.items():
        if value is None or (not allow_empty and str(value).strip() == ""):
            missing.append(key)
        else:
            values[key] = str(value)
    return values, missing


def env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value is not None else None


def error_payload(message: str, **extra: Any) -> dict[str, Any]:
    return {"status": "error", "message": message, **extra}


def blocked_payload(message: str, **extra: Any) -> dict[str, Any]:
    return {"status": "blocked", "message": message, **extra}


def ensure_script_import_path() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
