#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/check_post.sh <post_path> [--run-pipeline] [--allow-draft] [--skip-render]" >&2
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$repo_root" ]]; then
  echo "Run this script from inside the blog Git repository." >&2
  exit 1
fi

python_bin="$repo_root/.venv/Scripts/python.exe"
if [[ ! -x "$python_bin" ]]; then
  python_bin="python"
fi

tool="$repo_root/tools/check_post.py"
if [[ ! -f "$tool" ]]; then
  echo "Missing tool: $tool" >&2
  exit 1
fi

"$python_bin" "$tool" "$@"
