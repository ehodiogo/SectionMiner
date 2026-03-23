#!/usr/bin/env bash
set -euo pipefail

# Build SectionMiner artifacts and optionally upload to PyPI.
# Usage:
#   ./build_release.sh
#   ./build_release.sh --bump
#   ./build_release.sh --upload
#   ./build_release.sh --bump --upload

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

UPLOAD=false
BUMP=false

for arg in "$@"; do
  case "$arg" in
    --upload)
      UPLOAD=true
      ;;
    --bump)
      BUMP=true
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./build_release.sh [--bump] [--upload]

Options:
  --bump    Incrementa automaticamente a versao patch (x.y.z -> x.y.(z+1))
  --upload  Faz upload para PyPI usando PYPI_API_TOKEN do .env
EOF
      exit 0
      ;;
    *)
      echo "Error: argumento invalido: $arg"
      exit 1
      ;;
  esac
done

if [[ "$BUMP" == true ]]; then
  echo "[0/4] Bumping patch version..."
  python3 - <<'PY'
import pathlib
import re
import sys

root = pathlib.Path.cwd()
pyproject = root / "pyproject.toml"
init_file = root / "sectionminer" / "__init__.py"

pyproject_text = pyproject.read_text(encoding="utf-8")
match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"\s*$', pyproject_text, re.M)
if not match:
    print("Error: versao nao encontrada em pyproject.toml", file=sys.stderr)
    sys.exit(1)

major, minor, patch = map(int, match.groups())
new_version = f"{major}.{minor}.{patch + 1}"

pyproject_text = re.sub(
    r'^version\s*=\s*"\d+\.\d+\.\d+"\s*$',
    f'version = "{new_version}"',
    pyproject_text,
    count=1,
    flags=re.M,
)
pyproject.write_text(pyproject_text, encoding="utf-8")

init_text = init_file.read_text(encoding="utf-8")
init_text, count = re.subn(
    r'^__version__\s*=\s*"\d+\.\d+\.\d+"\s*$',
    f'__version__ = "{new_version}"',
    init_text,
    count=1,
    flags=re.M,
)
if count != 1:
    print("Error: __version__ nao encontrado em sectionminer/__init__.py", file=sys.stderr)
    sys.exit(1)
init_file.write_text(init_text, encoding="utf-8")

print(f"Version bumped to {new_version}")
PY
fi

PACKAGE_VERSION="$(python3 - <<'PY'
import pathlib
import re

txt = pathlib.Path('pyproject.toml').read_text(encoding='utf-8')
m = re.search(r'^version\s*=\s*"([^"]+)"\s*$', txt, re.M)
if not m:
    raise SystemExit('Nao foi possivel ler version em pyproject.toml')
print(m.group(1))
PY
)"

echo "[1/4] Cleaning old artifacts..."
rm -rf dist build sectionminer.egg-info

echo "[2/4] Building sdist and wheel..."
python3 -m build

echo "[3/4] Running twine checks..."
python3 -m twine check dist/*

if [[ "$UPLOAD" == true ]]; then
  echo "[4/4] Upload requested. Loading .env..."

  if [[ ! -f .env ]]; then
    echo "Error: .env file not found at $ROOT_DIR/.env"
    exit 1
  fi

  set -a
  # shellcheck disable=SC1091
  source .env
  set +a

  if [[ -z "${PYPI_API_TOKEN:-}" ]]; then
    echo "Error: PYPI_API_TOKEN is empty or undefined in .env"
    exit 1
  fi

  echo "Uploading to PyPI..."
  TWINE_USERNAME="__token__" \
  TWINE_PASSWORD="$PYPI_API_TOKEN" \
  python3 -m twine upload --non-interactive --repository-url https://upload.pypi.org/legacy/ "dist/sectionminer-${PACKAGE_VERSION}"*

  echo "Done: package uploaded."
else
  echo "[4/4] Build complete for version ${PACKAGE_VERSION}. To upload, run: ./build_release.sh --upload"
fi

