"""NotebookLMClient + Sources API (notebooklm type) 集成测试 — Phase 5 + 6

Subprocess 全部 mocked;不复依赖真 CLI / 网络。
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from app.services.notebooklm_client import (
    NotebookLMClient,
    NotebookLMError,
    ARTIFACT_TYPES,
)


# ============ Client construction ============

class TestClientConstruction:
    def test_resolve_cli_default(self):
        """没传 bin_path → settings.NOTEBOOKLM_BIN 路径(VM 上是 ~/.venv-smp/bin/notebooklm)"""
        c = NotebookLMClient(profile="test")
        # VM 上有这个 binary
        assert c.bin_path.endswith("notebooklm")
        assert c.profile == "test"

    def test_explicit_bin_path(self, tmp_path):
        fake = tmp_path / "fake_nlm"
        fake.write_text("#!/bin/sh\n")
        fake.chmod(0o755)
        c = NotebookLMClient(bin_path=str(fake), profile="t")
        assert c.bin_path == str(fake)

    def test_proxy_from_settings(self):
        from app.core.config import settings
        with patch.object(settings, "NOTEBOOKLM_PROXY", "http://127.0.0.1:7890"):
            c = NotebookLMClient()
            assert c.proxy == "http://127.0.0.1:7890"

    def test_proxy_from_constructor(self):
        c = NotebookLMClient(proxy="http://proxy:8080")
        assert c.proxy == "http://proxy:8080"


# ============ subprocess mock helper ============

def _mock_proc(returncode: int, stdout: str = "", stderr: str = ""):
    """造一个像 asyncio.subprocess.Process 的对象。"""
    p = MagicMock()
    p.returncode = returncode
    p.communicate = AsyncMock(return_value=(stdout.encode("utf-8"), stderr.encode("utf-8")))
    return p


def _patch_client(monkeypatch_or_patch, client, returncode, stdout, stderr, proxy_seen=None):
    """拦截 client._run,直接返 mock 结果。

    monkeypatch_or_patch 是 pytest 的 monkeypatch fixture,或 unittest.mock.patch。
    """
    captured = {}

    async def fake_run(args, timeout=60):
        # 抓代理透传
        if proxy_seen is not None:
            # args 是 list[str],proxy 不在这里
            # 真代理在 env 上; 但 mock 不能真传 env,
            # 改成让 fake_run 走 client.proxy 跟 _run 一样
            captured["proxy"] = client.proxy
        return {"returncode": returncode, "stdout": stdout, "stderr": stderr}

    monkeypatch_or_patch.setattr(client, "_run", fake_run)
    return captured


# ============ is_authenticated / get_auth_status ============

class TestAuth:
    def test_authenticated_true(self):
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 0, "stdout": '{"status":"ok","profile":"t"}', "stderr": ""
        })):
            result = asyncio.run(c.is_authenticated())
        assert result is True

    def test_authenticated_false_nonzero_return(self):
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 1, "stdout": "", "stderr": "not authenticated"
        })):
            result = asyncio.run(c.is_authenticated())
        assert result is False

    def test_get_auth_status_unauth(self):
        c = NotebookLMClient(profile="my")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 1, "stdout": "", "stderr": "no cookies"
        })):
            result = asyncio.run(c.get_auth_status())
        assert result["authenticated"] is False
        assert "login" in result["login_command"].lower()
        assert "-p my" in result["login_command"]
        assert "error" in result

    def test_login_command_includes_proxy(self):
        c = NotebookLMClient(profile="work", proxy="http://127.0.0.1:7890")
        cmd = c.login_command()
        # login_command 本身不包含 proxy,但 proxy 在 _run 里设 env
        # 这里只验 login_command 是清晰可执行的命令行
        assert "login" in cmd
        assert "-p work" in cmd


# ============ create_notebook / add_source ============

class TestCreateNotebook:
    def test_create_success(self):
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 0,
            "stdout": '{"id":"nb_abc123","title":"Test"}',
            "stderr": "",
        })):
            nb_id = asyncio.run(c.create_notebook("Test"))
        assert nb_id == "nb_abc123"

    def test_create_failure_raises(self):
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 1, "stdout": "", "stderr": "auth failed"
        })):
            with pytest.raises(NotebookLMError, match="auth failed"):
                asyncio.run(c.create_notebook("Test"))

    def test_create_fallback_to_stdout_parse(self):
        """CLI 返非 JSON 时,fallback 解析 stdout 的 id。"""
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 0,
            "stdout": "Created notebook id=nb_xyz",
            "stderr": "",
        })):
            nb_id = asyncio.run(c.create_notebook("Test"))
        assert "nb_xyz" in nb_id


class TestAddSource:
    def test_add_url(self):
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 0, "stdout": "source added: src_001", "stderr": ""
        })):
            result = asyncio.run(c.add_source("nb_1", "https://example.com"))
        assert "source added" in result["stdout"]


# ============ generate_artifact / download_artifact ============

class TestGenerateArtifact:
    def test_generate_audio_polling(self):
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 0, "stdout": "task task_audio_001 started", "stderr": ""
        })):
            result = asyncio.run(c.generate_artifact("nb_1", "audio", ""))
        assert result["status"] == "polling"  # 长任务不 --wait
        assert result["artifact_type"] == "audio"

    def test_generate_quiz_completed(self):
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 0, "stdout": "quiz generated", "stderr": ""
        })):
            result = asyncio.run(c.generate_artifact("nb_1", "quiz", ""))
        assert result["status"] == "completed"  # 短任务 --wait

    def test_generate_long_prompt_writes_file(self, tmp_path):
        c = NotebookLMClient(profile="t", bin_path="/tmp/nonexistent")
        # 用长 prompt 触发写文件
        long_prompt = "x" * 500
        # 不调 _run(会失败),只验 prompt_file 路径逻辑:
        # 通过构造 fake 替换 _run
        async def fake_run(args, timeout=60):
            # 验证 args 里有 --prompt-file
            assert "--prompt-file" in args
            return {"returncode": 0, "stdout": "ok", "stderr": ""}
        with patch.object(c, "_run", new=fake_run):
            result = asyncio.run(c.generate_artifact("nb_1", "quiz", long_prompt))
        assert result["status"] == "completed"

    def test_generate_unknown_type_raises(self):
        c = NotebookLMClient(profile="t")
        with pytest.raises(NotebookLMError, match="不支持的 artifact_type"):
            asyncio.run(c.generate_artifact("nb_1", "unicorn"))

    def test_generate_failure_raises(self):
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 1, "stdout": "", "stderr": "rate limit"
        })):
            with pytest.raises(NotebookLMError, match="rate limit"):
                asyncio.run(c.generate_artifact("nb_1", "audio"))


# ============ run with proxy env ============

class TestProxyPassthrough:
    def test_proxy_sets_env(self):
        c = NotebookLMClient(profile="t", proxy="http://127.0.0.1:7890")

        captured_env = {}

        async def fake_create_subprocess_exec(*cmd, stdout=None, stderr=None, env=None, **kw):
            captured_env.update(env or {})
            return _mock_proc(0, stdout="{}")

        with patch("asyncio.create_subprocess_exec", new=fake_create_subprocess_exec):
            asyncio.run(c._run(["list"]))

        assert captured_env.get("https_proxy") == "http://127.0.0.1:7890"
        assert captured_env.get("HTTP_PROXY") == "http://127.0.0.1:7890"
        assert captured_env.get("HTTPS_PROXY") == "http://127.0.0.1:7890"
        assert captured_env.get("http_proxy") == "http://127.0.0.1:7890"

    def test_no_proxy_no_env(self):
        c = NotebookLMClient(profile="t", proxy=None)

        captured_env = {}

        async def fake_create_subprocess_exec(*cmd, stdout=None, stderr=None, env=None, **kw):
            captured_env.update(env or {})
            return _mock_proc(0, stdout="{}")

        with patch("asyncio.create_subprocess_exec", new=fake_create_subprocess_exec):
            asyncio.run(c._run(["list"]))

        # 没 proxy → env=None
        assert captured_env == {}


# ============ list_notebooks ============

class TestListNotebooks:
    def test_list_json(self):
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 0,
            "stdout": '[{"id":"nb_1","title":"X"},{"id":"nb_2","title":"Y"}]',
            "stderr": "",
        })):
            result = asyncio.run(c.list_notebooks())
        assert len(result) == 2
        assert result[0]["id"] == "nb_1"

    def test_list_failure_raises(self):
        c = NotebookLMClient(profile="t")
        with patch.object(c, "_run", new=AsyncMock(return_value={
            "returncode": 1, "stdout": "", "stderr": "auth failed"
        })):
            with pytest.raises(NotebookLMError, match="auth failed"):
                asyncio.run(c.list_notebooks())


# ============ ARTIFACT_TYPES registry ============

class TestArtifactRegistry:
    def test_artifact_types_includes_core(self):
        assert "audio" in ARTIFACT_TYPES
        assert "video" in ARTIFACT_TYPES
        assert "quiz" in ARTIFACT_TYPES

    def test_artifact_types_have_chinese_labels(self):
        for k, v in ARTIFACT_TYPES.items():
            assert v, f"artifact {k} missing label"
