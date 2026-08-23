#!/usr/bin/env bash
# Configura o root local de fixtures privadas via XDG.
# Uso:
#   NBR12721_PRIVATE_INPUTS="/caminho/absoluto" bash scripts/private-fixtures/configure.sh
#   bash scripts/private-fixtures/configure.sh --check
set -euo pipefail

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

note() {
  printf '[private-fixtures] %s\n' "$*"
}

is_filesystem_root() {
  # True para /, //, ///, etc. (somente barras).
  local value="$1"
  [[ -n "$value" ]] || return 1
  local stripped="${value//\//}"
  [[ -z "$stripped" ]]
}

strip_trailing_slashes() {
  local value="$1"
  if is_filesystem_root "$value"; then
    printf '%s' "/"
    return
  fi
  while [[ "$value" == */ ]]; do
    value="${value%/}"
  done
  printf '%s' "$value"
}

is_git_worktree() {
  local path="$1"
  local inside
  inside="$(git -C "$path" rev-parse --is-inside-work-tree 2>/dev/null || true)"
  [[ "$inside" == "true" ]]
}

MODE="write"
if [[ "${1:-}" == "--check" ]]; then
  MODE="check"
  shift
fi
if [[ "$#" -ne 0 ]]; then
  die "uso: [NBR12721_PRIVATE_INPUTS=...] bash scripts/private-fixtures/configure.sh [--check]"
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"
if git -C "$REPO_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO_ROOT="$(cd -- "$(git -C "$REPO_ROOT" rev-parse --show-toplevel)" && pwd -P)"
fi

if [[ -n "${XDG_CONFIG_HOME:-}" ]]; then
  CONFIG_DIR="${XDG_CONFIG_HOME}/nbr12721"
else
  [[ -n "${HOME:-}" ]] || die "HOME ausente e XDG_CONFIG_HOME não definido"
  CONFIG_DIR="${HOME}/.config/nbr12721"
fi
CONFIG_FILE="${CONFIG_DIR}/private-inputs-root"

validate_resolved_root() {
  local resolved="$1"
  local label="$2"
  is_filesystem_root "$resolved" && die "${label} não pode ser /"
  [[ "$resolved" != "$REPO_ROOT" ]] || die "${label} não pode ser o repositório"
  case "$resolved" in
    "$REPO_ROOT"/*) die "${label} não pode ficar dentro do repositório" ;;
  esac
  if is_git_worktree "$resolved"; then
    die "${label} não pode ser um checkout/worktree Git"
  fi
}

if [[ "$MODE" == "check" ]]; then
  [[ -f "$CONFIG_FILE" ]] || die "configuração ausente"
  command -v python3 >/dev/null 2>&1 || die "python3 é obrigatório para --check"
  # Leitura byte a byte: Bash/mapfile truncam em NUL e aceitariam path parcial.
  CONFIGURED="$(
    python3 - "$CONFIG_FILE" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = path.read_bytes()
except OSError:
    raise SystemExit(2)
if b"\x00" in data:
    raise SystemExit(3)
try:
    text = data.decode("utf-8")
except UnicodeDecodeError:
    raise SystemExit(4)
if text.endswith("\n"):
    text = text[:-1]
if text == "" or "\n" in text or "\r" in text:
    raise SystemExit(5)
sys.stdout.write(text)
PY
  )" || die "configuração inválida (vazia, multiline, NUL, CR ou encoding)"
  case "$CONFIGURED" in
    /*) ;;
    *) die "configuração não é path absoluto" ;;
  esac
  is_filesystem_root "$CONFIGURED" && die "root privado não pode ser /"
  CHECK_PATH="$(strip_trailing_slashes "$CONFIGURED")"
  [[ ! -L "$CHECK_PATH" ]] || die "root privado não pode ser symlink"
  [[ -d "$CHECK_PATH" ]] || die "root privado inexistente ou não é diretório"
  # stderr de cd pode revelar o path absoluto; sanitizar.
  if ! RESOLVED="$(cd -- "$CHECK_PATH" 2>/dev/null && pwd -P)"; then
    die "root privado inacessível"
  fi
  validate_resolved_root "$RESOLVED" "root privado"
  note "configuração válida"
  exit 0
fi

RAW="${NBR12721_PRIVATE_INPUTS:-}"
[[ -n "$RAW" ]] || die "NBR12721_PRIVATE_INPUTS é obrigatório"
# Env vars POSIX não carregam NUL; rejeita newline e carriage return.
case "$RAW" in
  *$'\n'*|*$'\r'*) die "NBR12721_PRIVATE_INPUTS contém caracteres proibidos" ;;
esac
case "$RAW" in
  /*) ;;
  *) die "NBR12721_PRIVATE_INPUTS deve ser path absoluto" ;;
esac
is_filesystem_root "$RAW" && die "NBR12721_PRIVATE_INPUTS não pode ser /"
CHECK_PATH="$(strip_trailing_slashes "$RAW")"
[[ ! -L "$CHECK_PATH" ]] || die "NBR12721_PRIVATE_INPUTS não pode ser symlink"
[[ -d "$CHECK_PATH" ]] || die "NBR12721_PRIVATE_INPUTS deve existir como diretório"

if ! RESOLVED="$(cd -- "$CHECK_PATH" 2>/dev/null && pwd -P)"; then
  die "NBR12721_PRIVATE_INPUTS inacessível"
fi
validate_resolved_root "$RESOLVED" "NBR12721_PRIVATE_INPUTS"

umask 077
mkdir -p -- "$CONFIG_DIR"
chmod 700 -- "$CONFIG_DIR" 2>/dev/null || true

TMP_FILE="$(mktemp "${CONFIG_FILE}.tmp.XXXXXX")"
cleanup() {
  rm -f -- "$TMP_FILE"
}
trap cleanup EXIT

printf '%s\n' "$RESOLVED" >"$TMP_FILE"
chmod 600 -- "$TMP_FILE"
mv -f -- "$TMP_FILE" "$CONFIG_FILE"
trap - EXIT

note "configuração gravada"
exit 0
