# blogwriter (블로그 자동 작성 CLI)

정보(URL·텍스트·메모)를 던져주면 내 말투로 쓰인 블로그 글 초안을 만들어 주는 터미널 도구.

- 기획 배경: [Concept.md](Concept.md)
- 개발 계획·체크리스트: [ToDo.md](ToDo.md)

현재 상태: **Phase 0 완료 — 프로그램 뼈대(명령어 골격)까지 동작합니다.**
글을 실제로 써 주는 기능은 Phase 1에서 만듭니다.

---

## 처음 실행해 보기 (비개발자용 안내)

### 1. 터미널 열기
`Command(⌘) + 스페이스` → `터미널` 입력 → 엔터.

### 2. 프로젝트 폴더로 이동
아래 한 줄을 복사해서 터미널에 붙여넣고 엔터를 누르세요.

```bash
cd ~/프로젝트/블로그-자동작성/Auto-writing-blog
```

### 3. 셋업 스크립트 한 번 실행
필요한 것(파이썬, 라이브러리, 설정 파일)을 알아서 준비합니다. 처음 한 번만 하면 됩니다.

```bash
./setup.sh
```

마지막에 `[완료] 셋업이 끝났습니다.` 가 나오면 성공입니다.
(중간에 `ANTHROPIC_API_KEY가 설정되어 있지 않습니다`라는 안내가 나올 수 있는데,
지금 단계에서는 무시해도 됩니다. 글 작성 기능을 만들 때 필요합니다.)

### 4. 잘 설치됐는지 확인
```bash
uv run blog --help
```

아래처럼 명령어 목록이 나오면 정상입니다.

```
Commands
  version   설치된 blogwriter 버전을 출력한다.
  config    설정 파일 위치와 현재 설정값을 보여준다.
  write     자료를 받아 블로그 글 초안을 작성한다.
  list      지금까지 생성한 글 이력을 보여준다.
  plan      글의 각도와 목차(기획안)까지만 만든다.
  resume    저장된 기획안으로 본문 작성을 이어서 한다.
  publish   완성된 글을 발행(또는 클립보드 복사)한다.
```

버전도 확인해 보세요.

```bash
uv run blog version
```

> `write`, `plan` 같은 명령은 지금 실행하면
> `아직 만들지 않은 기능입니다` 라고 나옵니다. **정상입니다.** 다음 단계에서 채웁니다.

---

## 자주 나오는 문제

| 증상 | 해결 |
|------|------|
| `zsh: command not found: uv` | 터미널을 껐다 켜세요. 그래도 안 되면 `export PATH="$HOME/.local/bin:$PATH"` 를 실행 |
| `permission denied: ./setup.sh` | `chmod +x setup.sh` 실행 후 다시 `./setup.sh` |
| `no such file or directory` | 2번 폴더 이동 명령을 건너뛰지 않았는지 확인 |

---

## 개발자용 메모

```bash
uv sync --dev        # 의존성 설치
uv run blog --help   # 실행
uv run pytest -q     # 테스트
uv run ruff check .  # 린트
```

- 파이프라인 본체는 `src/blogwriter/core/`에 두고, `cli.py`는 그것을 터미널에 연결만 한다.
  (나중에 웹 UI가 필요해져도 `core/`를 그대로 재사용하기 위한 경계)
