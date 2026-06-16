# CLAUDE.md — self-media-platform

## What this project is

A self-media content platform (Python backend + Vite/TypeScript frontend).
See `README.md` for product scope and `PLAN.md` for handover context.

## 会话重启指引 (READ THIS FIRST)

> 每次会话开始时,先读这两个文件再开工:
>
> 1. **`docs/TASKS.md`** — 当前活跃任务 + 完成历史 + 恢复点
> 2. **`docs/CHANGELOG.md`** — 最近完成的功能/改动 (commit SHA + 验证结果)
>
> **不要重新看完整 codebase**。TASKS.md 已经写明"下个会话从这里继续"。
>
> 接到"继续未完成任务"指令时,直接:
> ```bash
> cat docs/TASKS.md | head -60
> ```
> 然后认领第一个 `in_progress` 或 `pending` 任务,从"下个会话从这里继续"读起。
>
> **工作约定**:
> - 关键里程碑(开写代码 / 跑通测试 / commit)必写 `docs/TASKS.md` progress section
> - TDD 走通:RED 测试 agent → 我实现 GREEN → code-reviewer agent
> - 验证用子 agent (e2e-runner / tdd-guide / code-reviewer),不烧主对话 context
> - 完成后即时 commit + 更新 CHANGELOG,不留悬空状态

---

## The dev environment: atelier-smp

This project runs inside an **OrbStack Linux VM called `atelier-smp`**,
scaffolded from the parent `atelier/` project. The host Mac is a thin
client — terminal, browser, OrbStack. All dev work (Node 24, pnpm,
Python 3.12, uv, Go, Rust, gh, Docker CLI, open-design daemon, MCPs)
lives inside the VM.

**Why a separate VM (atelier-smp) instead of reusing `atelier`?**

The parent `atelier/` VM already runs another task in parallel.
Two independent VMs give us:

- **Physical isolation** — both Claude Code sessions can edit files
  in their respective worktrees without trampling each other's state,
  caches, lockfiles, or running services.
- **Independent yolo sandboxes** — each project keeps its own allow
  /deny list. `bin/devbox` in self-media-platform operates on
  `atelier-smp`; the parent `bin/devbox` operates on `atelier`.
- **Independent provisioning** — if atelier-smp gets into a bad
  state, `bin/devbox reset` rebuilds it in ~5 min without touching
  the parent atelier VM (and vice versa).
- **Shared parent mount** — both VMs see the same `/Users/lazy/Code/crack/`
  tree via OrbStack auto-share, so cross-project reads still work
  (e.g. inspecting a sibling repo from inside the VM is fine).

The cost is RAM: each VM is 4 CPU / 8 GB by default. **On a 16 GB
Mac, two VMs will fight for memory; 32 GB is comfortable.**

## The yolo-safety model (mirrored from atelier)

This project adopts the same architecture-as-the-wall model. The host
is supposed to be inert. Every mutating op routes through `bin/devbox`
into the VM.

- `.claude/settings.json` (this project) — allow list + yolo deny list
- `.claude/settings.local.json` — local overrides (user-controlled)
- Parent `atelier/.claude/settings.json` is unaffected; each project
  keeps its own sandbox.

The deny list protects `self-media-platform` from `rm -rf` of any
sibling directory in `~/Code/crack/`. The parent `atelier/` does the
same for itself. Running Claude Code with `--dangerously-skip-permissions`
inside either VM is safe within the architectural boundary.

## Where things live

- **Host (Mac)**: terminal display, browser tab. Files at
  `/Users/lazy/Code/crack/claude/self-media-platform/`.
- **VM (atelier-smp)**: Claude Code, open-design daemon, all dev tools.
  Project files mounted at
  `/mnt/mac/Users/lazy/Code/crack/claude/self-media-platform/`.
- **Auto-share**: OrbStack exposes the entire `~/Code/` tree to the
  VM, so the parent `atelier/` directory and any sibling projects
  are reachable from inside atelier-smp at `~/Code/crack/...` (created
  by `setup/provision.sh`).

## Daily loop

```bash
# one-time (already done if VM is up)
make setup           # install-orbstack + provision + passthrough + doctor

# every session, in the self-media-platform project
bin/devbox claude    # Claude Code, inside atelier-smp, yolo
bin/devbox shell     # or just an interactive VM shell
bin/devbox run <cmd> # run any command inside the VM
bin/devbox gui       # open-design web UI tunneled to host browser
bin/devbox doctor    # health check
bin/devbox reset     # nuke + recreate (DESTRUCTIVE)
```

Convenience `make` targets: `make shell`, `make run CMD=...`,
`make doctor`, `make reset`.

## Rules of engagement (for Claude Code)

1. **Run heavy work in the VM.** Use `bin/devbox run <cmd>` or
   `bin/devbox shell`. The host is for display only.
2. **Python env lives in the VM.** Use `uv` (preinstalled) for any
   dependency work in `backend/`. Never `pip install` on the host.
3. **Frontend dev server stays in the VM.** `cd frontend && pnpm dev`
   runs inside the VM; the host browser reaches it via the standard
   Vite port (forwarded by OrbStack).
4. **Don't touch sibling projects.** The deny list blocks `rm -rf`
   on non-self-media-platform paths, but don't read or copy from
   `~/Code/crack/claude/atelier/` unless the user asks — it's a
   separate workstream.
5. **Multi-perspective verification.** After non-trivial changes,
   spin up `council` agents with different lenses and verify with
   the `verify` skill (real browser, real interactions).
6. **Treat the VM as disposable.** `bin/devbox reset` recreates it
   in ~5 min. Anything not under source control or in `/mnt/mac`
   is lost.

## What runs on the host vs. the VM

| Concern                  | Host | VM  | Notes                                                   |
|--------------------------|------|-----|---------------------------------------------------------|
| Terminal, browser        |  ✓   |     | OS does this for you                                    |
| OrbStack hypervisor      |  ✓   |     | runs the Linux VM on Apple Silicon                      |
| Claude Code              |      |  ✓  | `bin/devbox claude` — talks to local MCP                 |
| open-design daemon       |      |  ✓  | HTTP at 127.0.0.1:7456                                  |
| open-design MCP          |      |  ✓  | stdio bridge; configured via `.mcp.json`                |
| Node 24 / pnpm / uv / gh |      |  ✓  | see `setup/provision.sh`                                |
| Python 3.12 / venv       |      |  ✓  | preinstalled in the VM                                  |
| Docker engine            |  ✓   |     | OrbStack daemon is the host; VM CLI talks to socket     |
| project files            |  ✓   |     | mounted at `/mnt/mac/Users/lazy/Code/crack/claude/self-media-platform` |

## Troubleshooting

- **`orb: command not found`** → `export PATH="/opt/homebrew/bin:$PATH"`
  or `ln -sf $(pwd)/bin/devbox /usr/local/bin/devbox`.
- **`atelier-smp` not running** → `bin/devbox provision` (creates +
  starts + provisions) or `orbctl start atelier-smp`.
- **Port conflict with parent atelier** — each VM has its own network
  namespace. If you forward a host port, choose one that the parent
  atelier isn't using.
- **Token rotated** → re-run `./setup/host-passthrough.sh`.
- **VM borked** → `bin/devbox reset` (destructive: rebuilds from scratch).

## The two-VM landscape at a glance

```
Host (Mac) — 32 GB RAM
├── Terminal tabs (one per VM)
│   ├── tab A: ~/Code/crack/claude/atelier/         → bin/devbox claude → atelier VM
│   └── tab B: ~/Code/crack/claude/self-media-platform/  → bin/devbox claude → atelier-smp VM
├── Browser tab → http://localhost:7456 (open-design UI, per VM via tunnel)
└── OrbStack
        ├── atelier     (running, 7.7 GB) — parent project's task
        ├── atelier-smp (will be created)  — this project's task
        └── foo         (running, 892 MB)  — unrelated
```

The two worktrees share `~/Code/crack/` on disk; they only diverge
inside their own VM sandboxes. The host filesystem is the integration
point — files edited on the host are visible inside the VM (and
vice versa) at `/mnt/mac/`.
