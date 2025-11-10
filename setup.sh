#!/usr/bin/env bash
set -e

# 기본 경로 설정
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_DIR="$ROOT_DIR/playwright-dev/playwright-python"
JS_DIR="$ROOT_DIR/playwright-dev/playwright"

echo "📦 Setting up Playwright development environment..."
echo "Python repo: $PY_DIR"
echo "JS repo:     $JS_DIR"
echo

# 1️⃣ JS 빌드
if [ -d "$JS_DIR" ]; then
  echo "🛠️ Building Playwright JS driver..."
  cd "$JS_DIR"
  npm install
  npm run build
  echo "✅ JS build complete."
else
  echo "❌ JS repo not found: $JS_DIR"
  exit 1
fi

# 2️⃣ Python venv 생성
cd "$PY_DIR"
echo
echo "🐍 Setting up Python virtual environment using uv..."
uv venv
source .venv/bin/activate

# 3️⃣ Python editable 설치
echo
echo "📦 Installing playwright-python in editable mode..."
uv pip install -U pip setuptools wheel
uv pip install -e .

# 5️⃣ 테스트 명령어 안내
echo
echo "✅ Setup complete!"
echo
echo "Try running:"
echo "  source $PY_DIR/.venv/bin/activate"
echo "  python -c 'import playwright; print(playwright.__file__)'"
