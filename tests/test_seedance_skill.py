import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_script(script_name: str, *args: str, extra_env: dict[str, str] | None = None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script_name), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


class SeedanceSkillTests(unittest.TestCase):
    def test_skill_frontmatter_exposes_openclaw_metadata_and_base_dir_paths(self):
        skill_md = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn('metadata: {"openclaw"', skill_md)
        self.assertIn('"skillKey":"seedance-skill"', skill_md)
        self.assertIn("{baseDir}/scripts/generate_video.py", skill_md)

    def test_seedance_api_defaults_match_ark_v3(self):
        from scripts.seedance_skill_common import DEFAULT_ARK_BASE_URL, SEEDANCE_TASK_PATH

        self.assertEqual(DEFAULT_ARK_BASE_URL, "https://ark.cn-beijing.volces.com")
        self.assertEqual(SEEDANCE_TASK_PATH, "/api/v3/contents/generations/tasks")

    def test_build_seedance_request_uses_current_defaults(self):
        from scripts.seedance_skill_common import build_seedance_request

        payload = build_seedance_request("一只橘猫在雨夜街头奔跑")

        self.assertEqual(payload["model"], "doubao-seedance-2-0-260128")
        self.assertEqual(payload["ratio"], "9:16")
        self.assertEqual(payload["duration"], 5)
        self.assertEqual(payload["resolution"], "720p")
        self.assertTrue(payload["generate_audio"])
        self.assertFalse(payload["watermark"])
        self.assertTrue(payload["return_last_frame"])
        self.assertEqual(payload["content"], [{"type": "text", "text": "一只橘猫在雨夜街头奔跑"}])

    def test_build_h5_share_schema_url_encodes_values(self):
        from scripts.seedance_skill_common import build_h5_share_schema

        schema = build_h5_share_schema(
            {
                "client_key": "tt123",
                "nonce_str": "nonce-value",
                "timestamp": "1700000000",
                "signature": "deadbeef",
                "state": "share-state",
                "video_path": "https://example.com/video path.mp4",
                "title": "城市夜雨",
                "share_to_publish": 1,
            }
        )

        self.assertTrue(schema.startswith("snssdk1128://openplatform/share?"))
        self.assertIn("share_type=h5", schema)
        self.assertIn("client_key=tt123", schema)
        self.assertIn("video_path=https%3A%2F%2Fexample.com%2Fvideo+path.mp4", schema)
        self.assertIn("title=%E5%9F%8E%E5%B8%82%E5%A4%9C%E9%9B%A8", schema)
        self.assertIn("share_to_publish=1", schema)

    def test_prepare_publish_package_creates_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            video_path = output_dir / "video.mp4"
            cover_path = output_dir / "cover.png"
            video_path.write_bytes(b"fake-video")
            cover_path.write_bytes(b"fake-cover")

            result = run_script(
                "prepare_publish_package.py",
                "--idea",
                "做一个关于老街早餐摊的抖音短视频",
                "--prompt",
                "清晨的老街上，热气腾腾的早餐摊位，暖色纪实镜头，9:16",
                "--video-path",
                str(video_path),
                "--cover-path",
                str(cover_path),
                "--mode",
                "preview",
                "--output-dir",
                str(output_dir),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ok")
            self.assertTrue((output_dir / "publish.json").exists())
            self.assertTrue((output_dir / "publish.md").exists())
            self.assertTrue(payload["package"]["title"])
            self.assertGreaterEqual(len(payload["package"]["hashtags"]), 3)

    def test_generate_video_rejects_dry_run_flag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_script(
                "generate_video.py",
                "--prompt",
                "暴雨中的霓虹天桥，电影感跟拍镜头",
                "--dry-run",
                "--output-dir",
                temp_dir,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unrecognized arguments: --dry-run", result.stderr)

    def test_generate_video_requires_ark_api_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_script(
                "generate_video.py",
                "--prompt",
                "暴雨中的霓虹天桥，电影感跟拍镜头",
                "--output-dir",
                temp_dir,
                extra_env={"ARK_API_KEY": ""},
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertIn("ARK_API_KEY", payload["missing"])
            self.assertTrue((Path(temp_dir) / "request.json").exists())
            self.assertTrue((Path(temp_dir) / "generation.json").exists())

    def test_no_legacy_las_variables_remain_in_project_docs_or_scripts(self):
        files = [
            ROOT / "SKILL.md",
            ROOT / "README.md",
            ROOT / "references" / "seedance.md",
            ROOT / "scripts" / "generate_video.py",
            ROOT / "scripts" / "seedance_skill_common.py",
        ]

        for path in files:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("LAS_API_KEY", content, path.as_posix())
            self.assertNotIn("LAS_BASE_URL", content, path.as_posix())
            self.assertNotIn("DEFAULT_LAS_BASE_URL", content, path.as_posix())

    def test_douyin_h5_publish_requires_credentials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_script(
                "douyin_h5_publish.py",
                "--video-path",
                "https://example.com/assets/video.mp4",
                "--title",
                "城市雨夜漫游",
                "--hashtag",
                "城市漫游",
                "--hashtag",
                "夜景",
                "--share-to-publish",
                "--output-dir",
                temp_dir,
                extra_env={
                    "DOUYIN_CLIENT_KEY": "",
                    "DOUYIN_CLIENT_SECRET": "",
                    "DOUYIN_OPEN_TICKET": "",
                },
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertIn("DOUYIN_CLIENT_KEY", payload["missing"])
            self.assertFalse((Path(temp_dir) / "qr_payload.txt").exists())

    def test_douyin_openapi_publish_requires_credentials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "video.mp4"
            video_path.write_bytes(b"fake-video")

            result = run_script(
                "douyin_openapi_publish.py",
                "--video-path",
                str(video_path),
                "--title",
                "城市清晨",
                "--output-dir",
                temp_dir,
                extra_env={
                    "DOUYIN_CLIENT_KEY": "",
                    "DOUYIN_CLIENT_SECRET": "",
                    "DOUYIN_ACCESS_TOKEN": "",
                    "DOUYIN_OPEN_ID": "",
                },
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["recommended_fallback"], "manual-package")
            self.assertIn("DOUYIN_CLIENT_KEY", payload["missing"])


if __name__ == "__main__":
    unittest.main()
