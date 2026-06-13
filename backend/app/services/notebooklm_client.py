"""
NotebookLM Client — Phase 5
参考 qiaomu-anything-to-notebooklm + teng-lin/notebooklm-py 的模式:
  1. `notebooklm login` 浏览器引导登录(由用户手动跑,获取 cookies)
  2. `notebooklm auth check` 验证登录
  3. `notebooklm create` / `notebooklm source add` 灌来源
  4. `notebooklm generate <type>` AI 生成(audio / video / quiz / 等)
  5. `notebooklm download` 落本地

Subprocess wrapper,行为与 DouyinAdapter 一致:
  - mock-friendly(有 _request_override 模式可以测试)
  - 失败抛 NotebookLMError
"""
import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

log = logging.getLogger("notebooklm")


class NotebookLMError(Exception):
    """NotebookLM CLI 调用失败。"""


# 已实现的 artifact 类型(对应 `notebooklm generate` 的子命令)
ARTIFACT_TYPES = {
    "audio": "Audio Overview(播客)",
    "video": "Video Overview",
    "cinematic-video": "Cinematic Video",
    "slide-deck": "Slide Deck",
    "infographic": "Infographic",
    "quiz": "Quiz",
    "flashcards": "Flashcards",
    "report": "Report",
    "data-table": "Data Table",
    "mind-map": "Mind Map",
}


def _resolve_cli() -> str:
    """找 notebooklm CLI 路径(env > PATH > venv fallback)。"""
    from app.core.config import settings
    bin_name = getattr(settings, "NOTEBOOKLM_BIN", "notebooklm")
    # 1) 显式 bin(env 覆盖)
    if os.path.isabs(bin_name) and os.path.isfile(bin_name):
        return bin_name
    # 2) PATH
    found = shutil.which(bin_name)
    if found:
        return found
    # 3) venv fallback(.venv-smp/bin/notebooklm)
    candidate = Path("/home/lazy/.venv-smp/bin/notebooklm")
    if candidate.exists():
        return str(candidate)
    raise NotebookLMError(
        f"未找到 notebooklm CLI(查 $PATH / {bin_name} / /home/lazy/.venv-smp/bin/notebooklm)"
    )


class NotebookLMClient:
    """Subprocess wrapper 围着 `notebooklm` CLI 转。

    主要场景:
      - Sources 页"连接 NotebookLM"按钮 → 后端走 _auth_check()
        没登录就返 login_command 给前端,前端显示给用户跑
      - 提交 notebooklm 类型来源 → _create_notebook() + _add_source()
      - 触发 AI 生成 → generate_artifact() 返 {task_id, status}
    """

    def __init__(
        self,
        bin_path: Optional[str] = None,
        profile: Optional[str] = None,
        timeout: int = 300,
        proxy: Optional[str] = None,
    ):
        from app.core.config import settings
        self.bin_path = bin_path or _resolve_cli()
        self.profile = profile or "default"
        self.timeout = timeout
        # 代理:参数 > env > settings
        self.proxy = (
            proxy
            or os.getenv("NOTEBOOKLM_PROXY")
            or getattr(settings, "NOTEBOOKLM_PROXY", None)
        )
        # 测时 override: callable(cmd) → CompletedProcess-like
        self._request_override: Optional[Any] = None

    # ============== 公共 ==============

    async def is_authenticated(self) -> bool:
        """调 `notebooklm auth check --test --json` 验证。"""
        result = await self._run(["auth", "check", "--test", "--json"], timeout=30)
        if result["returncode"] != 0:
            return False
        try:
            data = json.loads(result["stdout"])
            return data.get("status") == "ok"
        except Exception:
            return False

    def login_command(self) -> str:
        """返用户需要跑的登录命令(给前端展示)。"""
        return f"{self.bin_path} login -p {self.profile}"

    async def list_notebooks(self) -> List[Dict[str, Any]]:
        """`notebooklm list --json` 返 [{id, title, ...}, ...]。"""
        result = await self._run(["list", "--json"], timeout=30)
        if result["returncode"] != 0:
            raise NotebookLMError(
                f"list notebooks 失败: {result['stderr'][-300:]}"
            )
        try:
            return json.loads(result["stdout"])
        except Exception:
            return []

    async def create_notebook(self, name: str) -> str:
        """`notebooklm create <name> --json` 返 notebook id。"""
        result = await self._run(["create", name, "--json"], timeout=30)
        if result["returncode"] != 0:
            raise NotebookLMError(
                f"create notebook 失败: {result['stderr'][-300:]}"
            )
        try:
            data = json.loads(result["stdout"])
            return data.get("id") or data.get("notebook_id")
        except Exception:
            # CLI 失败但返非 JSON(可能只 print 了 id)
            for line in result["stdout"].splitlines():
                if "id" in line.lower():
                    return line.split()[-1]
            raise NotebookLMError(f"无法解析 create 输出: {result['stdout'][:200]}")

    async def add_source(
        self, notebook_id: str, content: str, source_type: str = "auto",
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """`notebooklm source add <content>` 把 URL/文件/文本加到 notebook。"""
        cmd = ["source", "add"]
        if source_type and source_type != "auto":
            cmd.extend(["--type", source_type])
        if title:
            cmd.extend(["--title", title])
        cmd.extend(["-n", notebook_id, content])
        result = await self._run(cmd, timeout=120)
        if result["returncode"] != 0:
            raise NotebookLMError(
                f"source add 失败: {result['stderr'][-300:]}"
            )
        # stdout 含 source id / 摘要
        return {
            "stdout": result["stdout"][-500:],
            "stderr": result["stderr"][-200:],
        }

    async def generate_artifact(
        self,
        notebook_id: str,
        artifact_type: str,
        instructions: str = "",
    ) -> Dict[str, Any]:
        """`notebooklm generate <type> [--wait]` 触发 AI 生成。

        artifact_type: audio / video / quiz / ...
        """
        if artifact_type not in ARTIFACT_TYPES:
            raise NotebookLMError(
                f"不支持的 artifact_type: {artifact_type}(应属: {list(ARTIFACT_TYPES.keys())})"
            )
        # long prompt 写文件
        prompt_file = None
        cmd = ["generate", artifact_type, "-n", notebook_id]
        if instructions:
            if len(instructions) > 200:
                prompt_file = Path(f"/tmp/_nlm_prompt_{os.getpid()}.txt")
                prompt_file.write_text(instructions, encoding="utf-8")
                cmd.extend(["--prompt-file", str(prompt_file)])
            else:
                cmd.append(instructions)
        # 短任务(quiz/flashcards/mind-map)同步等,长任务(audio/video)异步
        sync_types = {"quiz", "flashcards", "report", "data-table", "mind-map"}
        if artifact_type in sync_types:
            cmd.append("--wait")
        result = await self._run(cmd, timeout=self.timeout)
        if prompt_file:
            try: prompt_file.unlink()
            except: pass
        if result["returncode"] != 0:
            raise NotebookLMError(
                f"generate {artifact_type} 失败: {result['stderr'][-300:]}"
            )
        return {
            "status": "completed" if artifact_type in sync_types else "polling",
            "artifact_type": artifact_type,
            "stdout": result["stdout"][-500:],
        }

    async def download_artifact(
        self,
        notebook_id: str,
        artifact_type: str,
        output_path: str,
    ) -> str:
        """`notebooklm download <type> <output>` 落本地。"""
        cmd = ["download", artifact_type, "-n", notebook_id, output_path]
        result = await self._run(cmd, timeout=120)
        if result["returncode"] != 0:
            raise NotebookLMError(
                f"download 失败: {result['stderr'][-300:]}"
            )
        if not Path(output_path).exists():
            raise NotebookLMError(
                f"download 报成功但文件不存在: {output_path}"
            )
        return output_path

    async def get_auth_status(self) -> Dict[str, Any]:
        """返详细 auth 状态 + login_command。"""
        result = await self._run(["auth", "check", "--json"], timeout=15)
        if result["returncode"] != 0:
            return {
                "authenticated": False,
                "login_command": self.login_command(),
                "error": (result["stderr"] or result["stdout"])[-300:],
            }
        try:
            data = json.loads(result["stdout"])
        except Exception:
            data = {"raw": result["stdout"][-500:]}
        return {
            "authenticated": data.get("status") == "ok",
            "login_command": self.login_command(),
            "details": data,
        }

    # ============== subprocess 内部 ==============

    async def _run(self, args: List[str], timeout: int = 60) -> Dict[str, Any]:
        cmd = [self.bin_path, "-p", self.profile, *args]
        if self._request_override:
            proc = await self._request_override(cmd, timeout=timeout)
            return {
                "returncode": getattr(proc, "returncode", 0),
                "stdout": getattr(proc, "stdout", b""),
                "stderr": getattr(proc, "stderr", b""),
            }
        # 代理透传:CLI 一般是 httpx/Playwright,读 https_proxy / HTTP_PROXY env
        env = None
        if self.proxy:
            env = {
                "https_proxy": self.proxy,
                "HTTP_PROXY": self.proxy,
                "HTTPS_PROXY": self.proxy,
                "http_proxy": self.proxy,
            }
            log.info("notebooklm cmd (via proxy %s): %s", self.proxy,
                     " ".join(cmd[:6]) + (" ..." if len(cmd) > 6 else ""))
        else:
            log.info("notebooklm cmd: %s", " ".join(cmd[:6]) + (" ..." if len(cmd) > 6 else ""))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise NotebookLMError(f"notebooklm 命令 timeout({timeout}s): {' '.join(cmd[:4])}")
        return {
            "returncode": proc.returncode or 0,
            "stdout": (stdout or b"").decode("utf-8", errors="replace"),
            "stderr": (stderr or b"").decode("utf-8", errors="replace"),
        }
