#!/usr/bin/env bash
# blogwriter 개발환경 원커맨드 셋업.
# 사용법:  ./setup.sh
set -euo pipefail

echo "== blogwriter 개발환경 셋업 =="

# 1. uv 설치 확인 (없으면 자동 설치)
if ! command -v uv >/dev/null 2>&1; then
  echo "-> uv가 없어서 설치합니다..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "-> uv $(uv --version)"

# 2. 의존성 설치 (Python 3.12도 uv가 알아서 받아 온다)
echo "-> 라이브러리 설치 중..."
uv sync --dev

# 3. Claude Code 확인 (글쓰기는 이걸로 돌아간다 — API 키 불필요)
if command -v claude >/dev/null 2>&1; then
  echo "-> Claude Code $(claude --version 2>/dev/null || echo '확인됨')"
else
  echo ""
  echo "!  claude 명령을 찾을 수 없습니다."
  echo "   이 프로그램은 이미 쓰고 계신 Claude Code로 글을 씁니다."
  echo "   터미널에서 'claude --version' 이 되는지 확인하세요."
  echo ""
fi

# 4. 기본 설정 파일·스타일 가이드 생성 (blogwriter가 직접 만든다)
uv run blog config >/dev/null 2>&1 || true
echo "-> 설정 위치: $HOME/.config/blogwriter/"

# 5. 동작 확인
if uv run blog --help >/dev/null 2>&1; then
  echo ""
  echo "[완료] 셋업이 끝났습니다."
  echo "   실행해 보기:  uv run blog --help"
else
  echo "[실패] 'uv run blog --help' 실행에 실패했습니다. 위 로그를 확인하세요."
  exit 1
fi
