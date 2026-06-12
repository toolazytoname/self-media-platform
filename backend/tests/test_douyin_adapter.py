"""DouyinAdapter 单元测试 — subprocess mocked"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from app.platforms.douyin import (
    DouyinAdapter,
    DouyinUploadError,
    _clamp_title_to_bytes,
    DOUYIN_TITLE_MAX_BYTES,
)


# ------------------- 纯函数测试 -------------------

class TestClampTitle:
    def test_short_unchanged(self):
        assert _clamp_title_to_bytes("OK 标题") == "OK 标题"

    def test_exact_max_unchanged(self):
        title = "x" * 30
        assert _clamp_title_to_bytes(title) == title

    def test_over_max_truncated(self):
        title = "x" * 50
        out = _clamp_title_to_bytes(title)
        assert len(out.encode("utf-8")) <= 30

    def test_chinese_truncated_safely(self):
        # 30 字节 = 10 个汉字
        title = "一二三四五六七八九十" * 4  # 40 chars
        out = _clamp_title_to_bytes(title)
        assert len(out.encode("utf-8")) <= 30
        # 不能把多字节字符切到一半
        out.encode("utf-8").decode("utf-8")  # 不抛

    def test_emoji_truncated_safely(self):
        # 4-byte emoji: 🚀 = 4 bytes
        title = "🚀" * 10  # 40 bytes
        out = _clamp_title_to_bytes(title)
        # 不强制 30 字节完整 — 至少不能切坏 UTF-8
        out.encode("utf-8").decode("utf-8")

    def test_constant_max_bytes_is_30(self):
        assert DOUYIN_TITLE_MAX_BYTES == 30


# ------------------- Adapter 行为测试 -------------------

class TestDouyinAdapterConstruction:
    def test_no_sau_still_constructs(self):
        """sau 不装时,adapter 仍能构造(不抛),只是 upload 时才报错"""
        acc = {"platform": "douyin", "name": "test", "id": "x"}
        # 显式清空 PATH,确保 sau 找不到
        with patch.dict("os.environ", {"PATH": "/nonexistent"}):
            import os
            os.environ["PATH"] = "/nonexistent"
            a = DouyinAdapter(acc)
        # sau_bin 可能是 None(如果 which 找不到)
        assert a.sau_bin is None or "sau" in (a.sau_bin or "")

    def test_explicit_sau_bin_via_account(self, tmp_path):
        """测试时通过 account dict 注入 sau_bin,跳过 PATH 查找"""
        fake_bin = tmp_path / "fake_sau"
        fake_bin.write_text("#!/bin/sh\necho hi\n")
        fake_bin.chmod(0o755)
        acc = {"platform": "douyin", "name": "test", "id": "x", "sau_bin": str(fake_bin)}
        a = DouyinAdapter(acc)
        assert a.sau_bin == str(fake_bin)

    def test_default_cookie_path(self, tmp_path):
        """不传 cookie_path 时,自动用 settings.COOKIES_DIR/{name}.json"""
        # settings 已经在 conftest 里能 import; 直接信任默认
        acc = {"platform": "douyin", "name": "default", "id": "x",
               "sau_bin": str(tmp_path / "fake")}
        a = DouyinAdapter(acc)
        assert a.cookie_path.endswith("default.json")
        assert "cookies" in a.cookie_path

    def test_explicit_cookie_path(self, tmp_path):
        cookie = tmp_path / "my.json"
        acc = {"platform": "douyin", "name": "x", "id": "y",
               "sau_bin": str(tmp_path / "fake"), "cookie_path": str(cookie)}
        a = DouyinAdapter(acc)
        assert a.cookie_path == str(cookie)


class TestDouyinAdapterUpload:
    @pytest.mark.asyncio
    async def test_happy_path(self, tmp_path):
        """exit=0 + 含 manage URL → 返 published + url"""
        video = tmp_path / "v.mp4"
        video.write_bytes(b"fake")
        cookie = tmp_path / "c.json"
        cookie.write_text("{}")
        sau_bin = tmp_path / "fake_sau"
        sau_bin.write_text("#!/bin/sh\nexit 0")
        sau_bin.chmod(0o755)

        acc = {"platform": "douyin", "name": "t", "id": "x",
               "sau_bin": str(sau_bin), "cookie_path": str(cookie)}
        adapter = DouyinAdapter(acc)

        # mock subprocess,返 manage URL
        fake_proc = AsyncMock()
        fake_proc.communicate = AsyncMock(
            return_value=(b"Published at https://creator.douyin.com/creator-micro/content/manage/123", b"")
        )
        fake_proc.returncode = 0
        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            result = await adapter.upload_video(
                video_path=str(video),
                title="测试视频",
                description="desc",
                tags=["t1", "t2"],
            )
        assert result["status"] == "published"
        assert "creator.douyin.com" in result["url"]
        assert result["platform_publish_id"] == result["url"]

    @pytest.mark.asyncio
    async def test_title_30_byte_clamp(self, tmp_path):
        """title > 30 字节时,sau 收到的是截断后的"""
        video = tmp_path / "v.mp4"
        video.write_bytes(b"x")
        sau_bin = tmp_path / "fake_sau"
        sau_bin.write_text("#!/bin/sh\nexit 0")
        sau_bin.chmod(0o755)
        cookie = tmp_path / "c.json"
        cookie.write_text("{}")

        acc = {"platform": "douyin", "name": "t", "id": "x",
               "sau_bin": str(sau_bin), "cookie_path": str(cookie)}
        adapter = DouyinAdapter(acc)

        fake_proc = AsyncMock()
        fake_proc.communicate = AsyncMock(return_value=(b"ok", b""))
        fake_proc.returncode = 0
        with patch("asyncio.create_subprocess_exec", return_value=fake_proc) as m:
            await adapter.upload_video(
                video_path=str(video),
                title="x" * 50,  # 50 bytes
                description="", tags=[],
            )
        cmd = m.call_args[0]
        # 找 --title 后面的参数
        idx = cmd.index("--title")
        clamped = cmd[idx + 1]
        assert len(clamped.encode("utf-8")) <= 30
        assert clamped == "x" * 30

    @pytest.mark.asyncio
    async def test_nonzero_exit_raises(self, tmp_path):
        video = tmp_path / "v.mp4"; video.write_bytes(b"x")
        sau_bin = tmp_path / "fake_sau"; sau_bin.write_text("#!/bin/sh\nexit 1")
        sau_bin.chmod(0o755)
        cookie = tmp_path / "c.json"; cookie.write_text("{}")
        acc = {"platform": "douyin", "name": "t", "id": "x",
               "sau_bin": str(sau_bin), "cookie_path": str(cookie)}
        adapter = DouyinAdapter(acc)

        fake_proc = AsyncMock()
        fake_proc.communicate = AsyncMock(return_value=(b"", b"upload failed: cookie expired"))
        fake_proc.returncode = 1
        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            with pytest.raises(DouyinUploadError) as exc_info:
                await adapter.upload_video(
                    str(video), "title", "", tags=[],
                )
        assert "exit=1" in str(exc_info.value)
        assert "cookie expired" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_sau_raises(self, tmp_path):
        video = tmp_path / "v.mp4"; video.write_bytes(b"x")
        acc = {"platform": "douyin", "name": "t", "id": "x",
               "sau_bin": "/nonexistent/path/sau", "cookie_path": str(tmp_path / "c.json")}
        adapter = DouyinAdapter(acc)
        # 强制 _require_sau 返回失败路径
        adapter.sau_bin = None
        with pytest.raises(DouyinUploadError, match="未找到 sau"):
            await adapter.upload_video(str(video), "t", "", tags=[])

    @pytest.mark.asyncio
    async def test_video_file_missing_raises(self, tmp_path):
        sau_bin = tmp_path / "fake_sau"; sau_bin.write_text("#!/bin/sh\nexit 0")
        sau_bin.chmod(0o755)
        cookie = tmp_path / "c.json"; cookie.write_text("{}")
        acc = {"platform": "douyin", "name": "t", "id": "x",
               "sau_bin": str(sau_bin), "cookie_path": str(cookie)}
        adapter = DouyinAdapter(acc)
        with pytest.raises(DouyinUploadError, match="video file not found"):
            await adapter.upload_video("/nonexistent/video.mp4", "t", "", tags=[])
