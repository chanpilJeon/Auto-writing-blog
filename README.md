# blogwriter (블로그 자동 작성 CLI)

정보(기사 텍스트·메모·자료)를 던져주면 내 말투로 쓰인 블로그 글 초안을 만들어 주는 터미널 도구.

- 기획 배경: [Concept.md](Concept.md)
- 개발 계획·체크리스트: [ToDo.md](ToDo.md)

현재 상태: **글 쓰기 + 네이버 블로그 붙여넣기까지 완성.**
(URL 자동 크롤링과 목차 승인 단계는 Phase 2에서 만듭니다.)

---

## 1. 처음 한 번만 하는 준비

### 1-1. 터미널 열기
`Command(⌘) + 스페이스` → `터미널` 입력 → 엔터.

### 1-2. 프로젝트 폴더로 이동
아래 한 줄을 복사해서 붙여넣고 엔터.

```bash
cd ~/프로젝트/블로그-자동작성/Auto-writing-blog
```

### 1-3. 셋업 스크립트 실행
필요한 것(파이썬, 라이브러리, 설정 파일)을 알아서 준비합니다.

```bash
./setup.sh
```

마지막에 `[완료] 셋업이 끝났습니다.` 가 나오면 성공입니다.

### 1-4. API 키 넣기 (글을 쓰려면 필수)

이 프로그램은 Claude에게 글을 대신 쓰게 하므로 **Claude API 키**가 필요합니다.

1. https://console.anthropic.com 에 로그인 → 왼쪽 메뉴 `API Keys` → `Create Key`
2. `sk-ant-` 로 시작하는 긴 문자열이 나옵니다. **그 창을 닫으면 다시 볼 수 없으니 복사해 두세요.**
3. 터미널에 아래를 붙여넣되, `sk-ant-여기에키` 부분을 복사한 키로 바꾸세요.

```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-여기에키"' >> ~/.zshrc
```

4. **터미널을 완전히 껐다가 다시 켭니다.** (안 그러면 키가 적용되지 않습니다)
5. 폴더로 다시 이동한 뒤 아래로 확인:

```bash
cd ~/프로젝트/블로그-자동작성/Auto-writing-blog && uv run blog config
```

`API 키  설정됨 (sk-ant-api...)` 이라고 초록색으로 나오면 준비 끝입니다.

> 💡 API 키는 컴퓨터 안에만 저장되고, 이 프로그램의 설정 파일에는 절대 기록되지 않습니다.

---

## 2. 글 쓰기

### 방법 A — 자료를 직접 붙여넣기

```bash
uv run blog write --text "여기에 기사나 자료 내용을 통째로 붙여넣으세요"
```

### 방법 B — 자료가 긴 경우 (파일로 저장해서 넣기, 추천)

긴 기사는 따옴표 안에 넣기 불편합니다. 메모장이나 텍스트편집기에 붙여넣고 `자료.txt` 로 저장한 뒤:

```bash
uv run blog write --file 자료.txt --source "https://원문주소"
```

`--source` 는 선택입니다. 넣으면 글 파일에 출처가 함께 기록됩니다.

### 실행하면 이렇게 진행됩니다

```
글을 쓰기 시작합니다. (자료 3241자, 보통 1~2분 걸립니다)

  [1/4] 자료를 읽고 글의 각도와 목차를 잡는 중...
  [2/4] 본문을 쓰는 중 (가장 오래 걸립니다)...
  [3/4] 제목 후보와 태그를 뽑는 중...
  [4/4] 파일로 저장하는 중...

[완료] 초안이 만들어졌습니다.
  제목    (Claude가 고른 제목)
  태그    태그1, 태그2, 태그3
  저장    /Users/…/BlogDrafts/2026-09-04-제목.md

다른 제목 후보
  - 후보 2
  - 후보 3
  …

  이력 번호 1 · 예상 비용 약 $0.042
```

### 결과물 열어 보기

```bash
open ~/BlogDrafts
```

Finder가 열리면 방금 만든 `.md` 파일을 더블클릭하세요.
파일 맨 위의 `---` 사이 부분은 제목·태그 같은 메타정보이고, 그 아래가 본문입니다.
블로그에 올릴 때는 본문 부분만 복사해서 붙여넣으면 됩니다.

---

## 3. 네이버 블로그에 올리기

글이 마음에 들면 클립보드로 복사해서 네이버 에디터에 붙여넣습니다.

```bash
uv run blog publish
```

(번호를 주면 그 글, 생략하면 가장 최근 글입니다. `uv run blog publish 3`)

```
[완료] 본문을 서식 그대로 클립보드에 복사했습니다.

이제 이렇게 하세요
  1. 네이버 블로그 > 글쓰기 를 엽니다.
  2. 제목 칸에 붙여넣기:  가격이 내려간 뒤 달라진 것
  3. 본문 칸을 클릭하고 ⌘+V 로 붙여넣습니다.
  4. 태그 칸에 입력:  #AI #가격정책
  5. 내용을 한 번 읽어 보고 발행 버튼을 누릅니다.
```

**소제목·굵은 글씨·링크·인용문 서식이 그대로 붙습니다.** 마크다운 기호(`##`, `**`)가
그대로 보이는 일은 없습니다. 글 끝에는 출처 링크가 자동으로 붙습니다.

### 왜 "자동 발행"이 아니라 복붙인가

네이버는 2020년 5월에, 티스토리는 2024년 2월에 **글쓰기 API를 종료**했습니다.
지금 프로그램이 네이버에 직접 글을 올릴 수 있는 공식적인 방법은 없습니다.
브라우저를 자동 조작하는 방법은 약관 위반이고 계정이 정지될 수 있어 쓰지 않습니다.
그래서 "붙여넣기 직전"까지를 자동화했습니다.

### 발행 옵션

| 명령 | 언제 쓰나 |
|------|-----------|
| `uv run blog publish` | 기본. 서식 그대로 복사 |
| `uv run blog publish 3` | 3번 글을 복사 |
| `uv run blog publish --format text` | 서식이 깨져 보일 때. 마크다운 기호를 지운 평문으로 복사 |
| `uv run blog publish --no-source` | 글 끝의 출처 링크를 빼고 복사 |

> 붙여넣은 뒤 네이버가 "외부 콘텐츠를 붙여넣었습니다" 같은 안내를 띄우면 그대로 두면 됩니다.

---

## 4. 지금까지 쓴 글 목록 보기

```bash
uv run blog list
```

```
번호 날짜                 상태       제목
2    2026-09-04T21:40:11  polished   두 번째로 쓴 글 제목
1    2026-09-04T20:12:03  polished   첫 번째로 쓴 글 제목

합계 예상 비용 약 $0.085
```

---

## 5. 글 품질을 올리는 가장 중요한 한 가지

**스타일 가이드에 내가 쓴 글을 붙여넣는 것.** 규칙을 백 줄 적는 것보다 실제 글 두 편이 훨씬 효과가 큽니다.

```bash
open -e ~/.config/blogwriter/style-guide.md
```

파일 맨 아래 `## 좋은 예시` 부분에 직접 쓴 글 2~3편을 통째로 붙여넣고 저장하세요.
다음 번 `blog write` 부터 바로 반영됩니다. 말투가 마음에 안 들면 위쪽 "말투 / 금지 사항"도 고치면 됩니다.

### 모델 바꾸기 (글이 더 잘 써졌으면 할 때)

```bash
open -e ~/.config/blogwriter/config.toml
```

`write = "claude-sonnet-5"` 를 `write = "claude-opus-5"` 로 바꾸면 본문 품질이 올라갑니다.
대신 비용이 2~3배가 됩니다. (그래도 글 한 편에 수백 원 수준)

---

## 6. 자주 나오는 문제

| 증상 | 해결 |
|------|------|
| `zsh: command not found: uv` | 터미널을 껐다 켜세요. 그래도 안 되면 `export PATH="$HOME/.local/bin:$PATH"` 실행 |
| `ANTHROPIC_API_KEY 환경변수가 없습니다` | 1-4번을 다시 하고 **터미널을 껐다 켜세요** |
| `API 키가 올바르지 않습니다` | 키를 복사할 때 앞뒤 공백이나 따옴표가 섞였는지 확인 |
| `자료가 너무 짧습니다` | 자료는 최소 100자 이상 필요합니다 |
| `요청이 몰려 잠시 거부됐습니다` | 1~2분 뒤 다시 실행 |
| `permission denied: ./setup.sh` | `chmod +x setup.sh` 실행 후 다시 `./setup.sh` |
| 붙여넣었더니 `##`, `**` 기호가 그대로 보임 | 서식 붙여넣기가 막힌 것. `blog publish --format text` 로 다시 복사 |
| 붙여넣기가 안 됨 / 빈 화면 | 다른 걸 복사해서 클립보드가 덮인 경우. `blog publish` 를 다시 실행 |
| `아직 발행할 글이 없습니다` | 먼저 `blog write` 로 글을 만든 뒤 `blog publish` |

무슨 파일이 어디 있는지 헷갈리면 언제든:

```bash
uv run blog config
```

---

## 7. 아직 안 되는 것 (다음 단계)

- URL만 넣으면 자동으로 본문 긁어오기 → **Phase 2**
- 목차를 먼저 보여주고 승인받은 뒤 본문 쓰기 (`blog plan` / `blog resume`) → **Phase 2**
- 여러 자료를 한 편으로 종합하기 (`--merge`) → **Phase 2**

---

## 개발자용 메모

```bash
uv sync --dev        # 의존성 설치
uv run blog --help   # 실행
uv run pytest -q     # 테스트 (Claude 호출은 전부 목킹 — API 키 불필요)
uv run ruff check .  # 린트
```

구조 (자세한 내용은 [ToDo.md](ToDo.md) §2):

```
src/blogwriter/
  cli.py            Typer CLI — core를 터미널에 연결하는 껍데기
  config.py         config.toml + ANTHROPIC_API_KEY
  core/             ★ 파이프라인 (CLI를 전혀 모름 — 웹 UI 확장 시 재사용 지점)
    models.py       Source / Plan / Draft / Polish / Post
    llm.py          Claude 호출 + 프롬프트 로드 + JSON 파싱 + 비용 계산
    planner.py      ② 기획   (Claude 호출 1)
    writer.py       ③ 작성   (Claude 호출 2)
    polisher.py     ④ 다듬기 (Claude 호출 3)
    pipeline.py     ①~⑤ 순서대로 실행하는 오케스트레이터
  store/
    db.py           SQLite 이력 (~/.local/share/blogwriter/blogwriter.db)
    posts.py        frontmatter 마크다운 저장/조회 (~/BlogDrafts/)
  publish/
    base.py         Publisher 인터페이스 + 결과 안내 구조
    render.py       마크다운 → 네이버용 HTML (인라인 style 주입)
    clipboard.py    macOS 클립보드에 HTML 서식 플레이버 심기
    naver.py        네이버 블로그 어댑터
  prompts/          plan.md / write.md / polish.md / style-guide.md(기본 템플릿)
```
