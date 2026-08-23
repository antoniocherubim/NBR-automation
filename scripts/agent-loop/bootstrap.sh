#!/usr/bin/env bash
# Bootstrap offline N+1: valida ambiente e materializa fixtures privadas
# somente quando a task declara private_fixtures: required.
# Não acessa rede, não instala pacotes e não altera arquivos rastreados
# além de criar cópias ignoradas sob inputs/private/ quando autorizado.
set -euo pipefail

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

note() {
  printf '[bootstrap] %s\n' "$*"
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

require_cmd() {
  local name="$1"
  command -v "$name" >/dev/null 2>&1 || die "ferramenta ausente: $name (provisione o ambiente antes do run; bootstrap não instala nada)"
}

require_cmd python3
require_cmd git
require_cmd bash
require_cmd sha256sum

PYTHON_VERSION="$(
  python3 - <<'PY'
import sys

if sys.version_info < (3, 12):
    raise SystemExit(
        f"ERROR: Python >= 3.12 obrigatório; encontrado {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
PY
)"
note "python=$PYTHON_VERSION"

[[ -f "$ROOT/manifests/private-fixtures-v1.json" ]] || die "inventário privado ausente"

MARKER="$(
  AGENT_LOOP_WORKTREE="$ROOT" \
  PYTHONPATH="$ROOT/src:$ROOT/scripts/private-fixtures" \
  python3 - <<'PY'
import os
import sys
from pathlib import Path

from adapter.errors import TaskMarkerError
from adapter.task_marker import read_task_marker

task_file = os.environ.get("AGENT_LOOP_TASK_FILE")
if not task_file:
    print("none")
    raise SystemExit(0)
path = Path(task_file)
if not path.is_absolute():
    path = Path(os.environ["AGENT_LOOP_WORKTREE"]) / path
try:
    print(read_task_marker(path))
except TaskMarkerError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
)"

note "private_fixtures=$MARKER"

if [[ "$MARKER" == "none" ]]; then
  note "task pública: store privado não consultado; inputs/private/ não criado"
  note "ambiente offline validado (adapter N+1)"
  exit 0
fi

if [[ "$MARKER" != "required" ]]; then
  die "marcador private_fixtures inválido: $MARKER"
fi

note "materializando fixtures privadas verificadas"
AGENT_LOOP_WORKTREE="$ROOT" \
  PYTHONPATH="$ROOT/src:$ROOT/scripts/private-fixtures" \
  python3 "$ROOT/scripts/private-fixtures/materialize.py"

note "ambiente offline validado; corpus privado materializado (adapter N+1)"
exit 0
