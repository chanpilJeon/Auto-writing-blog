# ToDo: 블로그 자동 작성 CLI — 세부 기술 구현 계획

> 실행 형태 결정: **로컬 설치형 CLI (Python + uv)**
> 웹앱 ❌ / 모바일 앱 ❌ / Backend 서버 ❌ / 외부 DB ❌
> 근거는 하단 [기술 결정 기록](#8-기술-결정-기록adr) 참고. Concept.md의 "옵션 A" 경로를 채택.

---

## 1. 기술 스택 확정

| 영역 | 선택 | 이유 |
|------|------|------|
| 언어/런타임 | Python 3.12 | 본문 추출·텍스트 처리 생태계가 압도적. Concept.md 파이프라인과 일치 |
| 패키지/배포 | **uv** (`pyproject.toml`) | 설치 한 줄(`uv tool install`), 락파일로 재현 가능한 빌드, PyPI 배포까지 커버 |
| CLI 프레임워크 | **Typer** | 서브커맨드·옵션·도움말 자동 생성, 타입 힌트 기반 |
| LLM | **anthropic SDK** (Claude API) | 기획→작성→다듬기 3단계 호출. 기본 Sonnet, 작성 단계만 Opus 옵션 |
| 본문 추출 | **trafilatura** | URL → 광고 제거된 본문 텍스트. 크롤링 실패 시 원문 텍스트 직접 입력 폴백 |
| 로컬 저장 | 파일 시스템(마크다운) + **SQLite**(파이썬 내장) | 글 = `.md` 파일, 처리 이력·메타데이터 = SQLite 한 파일. 설치·운영 비용 0 |
| 설정 | `~/.config/blogwriter/config.toml` + 환경변수 `ANTHROPIC_API_KEY` | API 키는 파일에 저장하지 않음 |
| 출력 형식 | frontmatter 포함 마크다운 (`python-frontmatter`) | 어떤 발행 경로로든 변환 가능한 중립 포맷 |
| 발행 | Phase 3에서 플랫폼 확정 후 어댑터 추가 | 클립보드 복사(`pyperclip`) → WordPress/GitHub Pages 어댑터 순 |
| 테스트 | pytest + API 호출 목킹(`respx`/fixture) | 프롬프트 회귀 확인용 골든 파일 테스트 |
| 배포 | GitHub Actions → PyPI (`uv build` + `uv publish`) | 태그 푸시 = 자동 릴리스. 사용자는 `uv tool install blogwriter` |

### 명시적으로 채택하지 않은 것
- **React 웹 프론트/Node.js 백엔드**: 단일 사용자 로컬 도구라 서버 계층이 무의미. 파이프라인을 `core/`에 분리해두므로, 나중에 웹 UI가 필요해지면 FastAPI + React를 껍데기로 얹을 수 있음.
- **Flutter 모바일 앱**: 모바일에서의 요구는 "자료 던져두기"뿐 → 기존 콜드필 아카이브(Notion)를 입력 큐로 활용하면 앱 개발 없이 해결(Phase 4).
- **MariaDB / DynamoDB**: 관계형 조인도, 분산 키-값도 필요한 데이터가 없음. SQLite로 시작하고, AWS 배포가 실제로 필요해지는 시점(=서버가 생기는 시점)에 재검토.

---

## 2. 프로젝트 구조

```
blogwriter/
├── pyproject.toml            # uv 프로젝트 정의, [project.scripts] blog = "blogwriter.cli:app"
├── uv.lock
├── setup.sh                  # 개발환경 원커맨드 셋업 (아래 §6)
├── README.md
├── src/blogwriter/
│   ├── cli.py                # Typer 앱: write / plan / list / config / publish
│   ├── config.py             # config.toml 로드, API 키 확인
│   ├── core/                 # ★ 파이프라인 (CLI와 완전 분리 — 추후 웹/에이전트 재사용 지점)
│   │   ├── ingest.py         # ① 수집·정제: URL 크롤링(trafilatura) / 텍스트 / 파일
│   │   ├── planner.py        # ② 분석·구조화: 글 각도·목차 기획 (Claude 호출 1)
│   │   ├── writer.py         # ③ 초안 작성: 스타일 가이드 적용 (Claude 호출 2)
│   │   ├── polisher.py       # ④ 다듬기: 제목 후보·태그·메타 설명 (Claude 호출 3)
│   │   └── models.py         # Source / Plan / Draft / Post 데이터클래스
│   ├── store/
│   │   ├── db.py             # SQLite: 처리 이력, 단계별 중간 산출물 저장
│   │   └── posts.py          # 완성 글 .md 저장/조회 (~/BlogDrafts/)
│   ├── publish/
│   │   ├── base.py           # Publisher 인터페이스
│   │   ├── clipboard.py      # HTML/마크다운 클립보드 복사 (티스토리·네이버 복붙용)
│   │   └── ...               # wordpress.py / ghpages.py (Phase 3)
│   └── prompts/
│       ├── plan.md           # 기획 프롬프트 템플릿
│       ├── write.md          # 작성 프롬프트 템플릿
│       └── polish.md         # 다듬기 프롬프트 템플릿
├── style-guide.md            # 내 말투·구조 정의 + 내 글 예시 2~3편 (품질의 핵심)
└── tests/
    ├── test_pipeline.py
    └── fixtures/             # 목킹된 API 응답, 골든 출력
```

**설계 원칙**: `core/`는 CLI를 전혀 모르게 작성한다(입출력은 데이터클래스). 이 경계 하나로 "나중에 웹 UI/에이전트로 확장" 요구를 코드 재작성 없이 수용한다.

---

## 3. CLI 인터페이스 설계

```bash
# 설치 (최종 사용자)
uv tool install blogwriter          # PyPI 배포 후
uv tool install git+https://github.com/<me>/blogwriter  # PyPI 전에도 가능

# 사용
blog write "https://example.com/article"        # URL → 완성 글
blog write --text "붙여넣은 자료..."             # 텍스트 직접 입력
blog write a.txt b.txt --merge                  # 여러 자료 종합 (Phase 2)
blog plan "https://..."                         # 기획(목차)까지만 → 확인 후 이어서 작성
blog resume <id>                                # 저장된 기획으로 작성 재개
blog list                                       # 생성 이력 (SQLite)
blog publish <id> --to clipboard                # 발행 (기본: 클립보드)
blog config                                     # 설정 확인/편집
```

---

## 4. 구현 ToDo (Phase별)

### Phase 0 — 프로젝트 뼈대 (0.5일)
- [x] `uv init --package blogwriter` 로 프로젝트 생성, `src/` 레이아웃 구성
- [x] 의존성 추가: `uv add anthropic typer trafilatura python-frontmatter pyperclip`
- [x] 개발 의존성: `uv add --dev pytest respx ruff`
- [x] `pyproject.toml`에 `[project.scripts] blog = "blogwriter.cli:app"` 등록
- [x] `setup.sh` 작성 (§6) 및 동작 확인: 클린 클론 → `./setup.sh` → `blog --help` 성공
- [x] git 저장소 초기화, `.gitignore` (`.venv/`, `*.db`, `__pycache__/`)

### Phase 1 — MVP: 텍스트 → 완성 글 (1~2일)
- [ ] `config.py`: `ANTHROPIC_API_KEY` 검증, `config.toml` 생성 (모델명·출력 폴더·스타일 가이드 경로)
- [ ] `models.py`: `Source`, `Plan`, `Draft`, `Post` 데이터클래스 정의
- [ ] `prompts/plan.md`: 자료 → 글 각도 + 목차 JSON 산출 프롬프트
- [ ] `prompts/write.md`: 목차 + 스타일 가이드 → 본문 마크다운 프롬프트 (원문 재서술 필수 규칙 포함)
- [ ] `prompts/polish.md`: 본문 → 제목 후보 5개·태그·메타 설명 JSON 프롬프트
- [ ] `planner.py` / `writer.py` / `polisher.py` 구현 — 각 단계 산출물을 SQLite에 저장(재실행 대비)
- [ ] `posts.py`: frontmatter(제목·날짜·태그·출처·상태) 붙여 `~/BlogDrafts/YYYY-MM-DD-슬러그.md` 저장
- [ ] `cli.py`: `blog write --text`, `blog list` 연결
- [ ] **style-guide.md 작성**: 내가 쓴 글 2~3편 수집 + 말투/구조/금지어 정의
- [ ] 검증 루프: 서로 다른 주제 자료 10건으로 글 생성 → 스타일 가이드·프롬프트 튜닝 (품질 게이트: "내가 쓴 글 같다"고 느껴질 때까지)

### Phase 2 — 입력 확장 + 검토 워크플로우 (2~3일)
- [ ] `ingest.py`: URL 입력 → trafilatura 본문 추출, 실패 시 명확한 에러 + `--text` 폴백 안내
- [ ] 여러 자료 입력(`--merge`): 자료별 요점 추출 → 통합 기획
- [ ] `blog plan` / `blog resume`: 목차를 먼저 보여주고 승인 후 작성하는 2단계 모드
- [ ] `blog write --style <이름>`: 스타일 가이드 여러 벌 지원 (정보성/리뷰/에세이)
- [ ] pytest: API 목킹 기반 파이프라인 테스트 + 프롬프트 골든 파일 테스트
- [ ] `ruff` 린트 통과, GitHub Actions CI (테스트 + 린트)

### Phase 3 — 발행 + 배포 (2~3일)
- [ ] **발행 플랫폼 확정** (선행 결정 — Concept.md §3 표 참고)
- [ ] `publish/clipboard.py`: 마크다운→HTML 변환 후 클립보드 복사 (티스토리/네이버 복붙 경로)
- [ ] 선택한 플랫폼 어댑터 1개 구현:
  - WordPress: REST API, **draft 상태로 업로드** (최종 발행 버튼은 사람이)
  - GitHub Pages: `_posts/`에 파일 생성 → `git commit & push`
- [ ] 태그/카테고리 자동 매핑 (polisher 산출물 → 플랫폼 값)
- [ ] **PyPI 배포 파이프라인**: GitHub Actions — 태그 푸시 시 `uv build` → `uv publish` (Trusted Publishing 사용, 토큰 하드코딩 금지)
- [ ] README에 설치·사용법 정리, `v0.1.0` 릴리스

### Phase 4 — 고도화 (선택)
- [ ] 콜드필 아카이브(Notion) 연동: 아카이브 항목 → `blog write --from-notion <페이지>` (모바일 입력 큐 역할)
- [ ] `blog batch`: 미처리 아카이브 항목 일괄 초안 생성
- [ ] 이미지 삽입, 예약 발행, 시리즈 글 관리
- [ ] (요구가 실제로 생기면) `core/`를 FastAPI로 감싸 웹 UI 추가 — React는 이 시점에만 등장

---

## 5. 데이터 설계 (SQLite)

```sql
-- ~/.local/share/blogwriter/blogwriter.db
CREATE TABLE runs (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,            -- ISO8601
  source_type TEXT NOT NULL,           -- url | text | file | notion
  source_ref TEXT,                     -- URL 또는 파일 경로
  status TEXT NOT NULL,                -- planned | drafted | polished | published | failed
  plan_json TEXT,                      -- ② 기획 산출물 (재실행용)
  post_path TEXT,                      -- 완성 .md 경로
  published_to TEXT,                   -- clipboard | wordpress | ghpages
  tokens_in INTEGER, tokens_out INTEGER, cost_usd REAL   -- 비용 추적
);
```
단계별 산출물을 저장하므로 "기획은 좋은데 글이 별로"면 `blog resume <id>`로 ③부터만 재실행.

---

## 6. setup.sh (개발환경 원커맨드 셋업)

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "== blogwriter 개발환경 셋업 =="

# 1. uv 설치 확인
if ! command -v uv >/dev/null 2>&1; then
  echo "-> uv 설치 중..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "-> uv $(uv --version)"

# 2. 의존성 설치 (uv가 Python 3.12도 자동 확보)
uv sync --dev

# 3. API 키 확인
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo ""
  echo "⚠ ANTHROPIC_API_KEY가 설정되어 있지 않습니다."
  echo "  셸 프로필에 추가하세요:  export ANTHROPIC_API_KEY='sk-ant-...'"
fi

# 4. 기본 설정 파일 생성
CONFIG_DIR="$HOME/.config/blogwriter"
if [ ! -f "$CONFIG_DIR/config.toml" ]; then
  mkdir -p "$CONFIG_DIR"
  cat > "$CONFIG_DIR/config.toml" <<'EOF'
[model]
plan = "claude-sonnet-5"
write = "claude-sonnet-5"    # 품질 아쉬우면 opus로 교체
polish = "claude-sonnet-5"

[output]
drafts_dir = "~/BlogDrafts"

[style]
guide = "./style-guide.md"
EOF
  echo "-> 설정 생성: $CONFIG_DIR/config.toml"
fi

# 5. 동작 확인
uv run blog --help >/dev/null && echo "✅ 셋업 완료.  개발 실행: uv run blog write --text '...'"
```

최종 사용자 설치는 스크립트조차 불필요:
```bash
uv tool install blogwriter && blog config
```

---

## 7. 배포 전략 (안정성 확보)

1. **버전 관리**: SemVer. `pyproject.toml` 버전 = git 태그.
2. **CI** (GitHub Actions): PR마다 `uv sync` → `ruff check` → `pytest`. API 호출은 전부 목킹 — CI에 키 불필요.
3. **릴리스**: `v*` 태그 푸시 → `uv build` → PyPI Trusted Publishing으로 `uv publish`. 시크릿 토큰 저장 안 함.
4. **재현성**: `uv.lock` 커밋. 사용자 설치는 uv가 Python 버전까지 자동 해결하므로 "파이썬 안 깔려 있어요" 문제 없음.
5. **업그레이드**: `uv tool upgrade blogwriter` 한 줄.

---

## 8. 기술 결정 기록(ADR)

| 질문 | 결정 | 근거 |
|------|------|------|
| 웹앱? | ❌ | 단일 사용자·비상시 실행 도구. 서버/인증/호스팅이 순수 오버헤드. 개발 중 확인도 터미널 재실행이 브라우저 리로드보다 빠름 |
| 모바일 앱(Flutter)? | ❌ | 모바일 요구는 "자료 투입"뿐 → Notion 아카이브가 이미 그 역할(Phase 4 연동). 앱 스토어 배포 비용 대비 이득 없음 |
| 로컬 CLI 배포 방식 | **uv** (npm 아님) | 파이프라인 핵심 라이브러리(trafilatura, anthropic)가 Python. uv는 설치·락·퍼블리시를 단일 도구로 해결 |
| Backend(Node.js)? | ❌ | CLI가 Claude API를 직접 호출. 중간 서버는 지연·비용·장애 지점만 추가. 웹 확장 시에도 FastAPI(파이썬)로 `core/` 재사용이 맞음 |
| DB — MariaDB? | ❌ | 조인이 필요한 관계형 데이터가 없음 (이력 테이블 1개) |
| DB — DynamoDB(local→AWS)? | ❌ | AWS에 올릴 서버 자체가 없으므로 배포 대상도 없음. SQLite는 내장이라 설치·운영 0 |
| 확장 경로 | `core/` 분리 | 웹 UI가 진짜 필요해지는 날: FastAPI + React를 얹고, 모바일 요구가 커지면 그때 API 서버 + Flutter 검토. 지금 결정을 되돌릴 필요 없는 구조 |

---

## 9. 바로 시작하는 순서

1. Phase 0 체크리스트 실행 (`uv init` → `setup.sh` 검증)
2. `style-guide.md`에 넣을 **내 글 2~3편 수집** ← 코드보다 이게 품질을 좌우
3. Phase 1 구현 → 자료 10건으로 품질 게이트 통과
4. 발행 플랫폼 결정 (현재 운영 중인 블로그 확인) → Phase 3 어댑터 선택