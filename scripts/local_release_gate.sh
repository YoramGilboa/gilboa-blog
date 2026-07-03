#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/local_release_gate.sh <posts/SLUG/index.qmd> [--run-pipeline] [--skip-render]" >&2
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

post_input="$1"
shift

if [[ "$post_input" = /* ]] || [[ "$post_input" =~ ^[A-Za-z]:\\ ]]; then
  resolved_post="$post_input"
else
  resolved_post="$repo_root/$post_input"
fi

if [[ ! -f "$resolved_post" ]]; then
  echo "Post path not found: $post_input" >&2
  exit 1
fi

resolved_post="$(python - <<'PY' "$resolved_post"
import os,sys
print(os.path.abspath(sys.argv[1]))
PY
)"

case "$resolved_post" in
  *"/posts/"*"/index.qmd") ;;
  *)
    echo "Post path must point to posts/.../index.qmd" >&2
    exit 1
    ;;
esac

case "$resolved_post" in
  *"/posts/drafts/"*)
    echo "Release gate requires a published post path under posts/<slug>/index.qmd (not drafts)." >&2
    exit 1
    ;;
esac

echo "Running strict post lint gate..."
"$python_bin" "$repo_root/tools/lint_post.py" "$resolved_post"

echo "Running preflight gate (final review PASS is required)..."
"$python_bin" "$repo_root/tools/check_post.py" "$resolved_post" "$@"

echo "Local release gate passed for $resolved_post"
