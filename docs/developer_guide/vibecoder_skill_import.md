# Vibe-Coder Skill Import (GitHub -> Local Agent Setup)

Update Date: 2026-05-28  
Status: Active

This guide describes a reproducible way to import `SKILL.md` / `AGENT.md` files from GitHub
for popular AI coding agents (`codex`, `claude`, `cursor`).

Scope note:
- in this repository, "token contribution" means contribution via AI agents (vibe-coding), not financial donations.
- this flow is for local agent setup only; it does not change project governance, roadmap priority, or review bar.

## 1. Script

Use:

`backend/scripts/import_agent_skill.py`

What it does:
- downloads markdown skill/agent files from GitHub;
- supports `github.com/.../blob/...` and `raw.githubusercontent.com/...` URLs;
- supports `--repo owner/name --path file.md --ref <branch|tag|sha>`;
- writes file under `.vibecoder/skills/<agent>/...` by default.

Built-in safety checks:
- only GitHub hosts are accepted (`github.com`, `raw.githubusercontent.com`);
- only `.md` files are accepted;
- download size limit (`--max-bytes`, default `512000`);
- existing target file is not replaced unless `--overwrite` is provided.

## 2. Examples

Import directly from URL:

```bash
python backend/scripts/import_agent_skill.py \
  --agent codex \
  --skill-url https://github.com/owner/repo/blob/main/SKILL.md
```

Import by repository path:

```bash
python backend/scripts/import_agent_skill.py \
  --agent cursor \
  --repo owner/repo \
  --path agents/AGENT.md \
  --ref main
```

Dry-run only (no file write):

```bash
python backend/scripts/import_agent_skill.py \
  --agent claude \
  --skill-url https://raw.githubusercontent.com/owner/repo/main/SKILL.md \
  --dry-run
```

Overwrite existing local file:

```bash
python backend/scripts/import_agent_skill.py \
  --agent codex \
  --repo owner/repo \
  --path SKILL.md \
  --overwrite
```

## 3. How to use in contribution flow

1. Import or update local skill file from a versioned GitHub source.
2. Keep your PR scope narrow (one slice per PR).
3. Run required checks from `CONTRIBUTING.md`.
4. Open PR with explicit validation notes and known limitations.

This keeps vibe-coder contribution speed high while preserving the same quality bar for everyone.
