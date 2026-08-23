#!/usr/bin/env bash
# Gate de teste offline: compilação, smoke tests stdlib e sintaxe shell.
set -euo pipefail

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ -n "${AGENT_LOOP_WORKTREE:-}" ]]; then
  [[ -d "$AGENT_LOOP_WORKTREE" ]] || die "AGENT_LOOP_WORKTREE não é um diretório: $AGENT_LOOP_WORKTREE"
  ROOT="$(cd -- "$AGENT_LOOP_WORKTREE" && pwd -P)"
else
  ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"
fi
if git -C "$ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT="$(cd -- "$(git -C "$ROOT" rev-parse --show-toplevel)" && pwd -P)"
fi

cd -- "$ROOT"

command -v python3 >/dev/null || die "python3 indisponível"

python3 - <<'PY'
import sys

if sys.version_info < (3, 12):
    raise SystemExit("ERROR: Python >= 3.12 obrigatório")
PY

printf '[test] validando sintaxe shell dos scripts agent-loop e private-fixtures\n'
bash -n scripts/agent-loop/bootstrap.sh scripts/agent-loop/test.sh \
  scripts/private-fixtures/configure.sh

printf '[test] compilando scaffold Python\n'
python3 -m compileall -q src tests scripts/private-fixtures

printf '[test] executando smoke tests (stdlib unittest)\n'
PYTHONPATH=src:scripts/private-fixtures python3 -m unittest discover -s tests -p 'test_*.py' -v

printf '[test] gate concluído com sucesso\n'
exit 0
