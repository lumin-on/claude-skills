# kakao-chat-analysis

카카오톡 대화 내보내기(.txt)를 처음부터 끝까지 읽고 **"이 방에서 어떤 논의가 있었는가"**를 정리한 보고서를 HTML과 PDF로 만드는 Claude Code 스킬입니다.

보고서가 답하는 다섯 가지:

1. 누가 말했고, 각자 이 방에서 어떤 역할인가
2. 날짜별로 어떤 논의가 있었나
3. 주제(스레드)별로 이야기가 어떻게 시작되어 어떻게 발전했나
4. 그 주제를 누가 이어받아 처리했나
5. 어떻게 끝났나 — 해결 / 담당 지정 / 진행 중 / 흐지부지 / 정보공유

## 설치

프로젝트 스킬로 쓰려면 `kakao-chat-analysis/` 폴더를 프로젝트의 `.claude/skills/` 아래에 두고, 개인 스킬로 쓰려면 `~/.claude/skills/` 아래에 둡니다.

```bash
git clone https://github.com/kyungminiyang/kakao-chat-analysis.git
cp -r kakao-chat-analysis/kakao-chat-analysis  <프로젝트>/.claude/skills/
```

요구 사항: Python 3.10 이상(표준 라이브러리만 사용), PDF 출력에는 Chrome 또는 Edge(헤드리스 인쇄).

## 사용

Claude Code에서 카톡 내보내기 파일을 주고 "이 대화 분석해줘", "무슨 얘기 했는지 정리해줘", "누가 뭘 맡았는지 알려줘"라고 하면 스킬이 뜹니다. 파일명이 `KakaoTalk_*.txt`이거나 `[이름] [오전 h:mm]` 형식이면 자동 인식됩니다.

절차는 네 단계입니다.

| 단계 | 무엇을 | 도구 |
|---|---|---|
| 1. 파싱 | PC·안드로이드·iOS 내보내기를 메시지 단위로 나누고 날짜별 원문·통계를 만든다 | `scripts/parse_kakao.py` |
| 2. 읽기 | 날짜별 원문을 **전부** 읽고 구간 노트를 쓴다 (1,500건 초과면 서브에이전트가 구간별로) | `references/reading-guide.md` |
| 3. 통합 | 스레드를 날짜 넘어 병합하고 상태를 판정해 `analysis.json`을 쓴다 | `scripts/check_analysis.py`로 검사 |
| 4. 렌더 | HTML과 PDF를 만든다 | `scripts/build_report.py --pdf` |

작업 폴더는 원본 옆 `.kakao-analysis/<파일명>/`에 남으므로 `analysis.json`만 고쳐 다시 렌더할 수 있습니다.

## 같은 결과가 나오게 하는 장치

- **원문 전부 읽기** — 샘플링·키워드 검색으로는 "답이 없던 자리"를 잡을 수 없습니다.
- **고정된 상태 판정표** — `done / assigned / open / drop / info`와 판정 기준이 SKILL.md에 있습니다.
- **스키마 검사** — `check_analysis.py`가 모든 날짜의 다이제스트, 화자 이름 일치, 스레드 필수 항목, 열린 스레드의 확인 포인트를 검사합니다. 오류가 있으면 렌더가 막힙니다.
- **고정 렌더러** — 보고서 구성(한눈에 보기 → 화자와 역할 → 날짜별 논의 → 주제별 흐름과 결말 → 열려 있거나 사라진 것 → 용어집)은 `build_report.py`가 정합니다.

완성 예시 한 벌(합성 대화 39건 → 구간 노트 → analysis.json)이 `kakao-chat-analysis/assets/example/`에 있습니다.

## 구조

```
kakao-chat-analysis/
├── SKILL.md                    # 절차, 상태 판정 기준, 쓰기 규칙
├── references/reading-guide.md # 구간 노트 양식, 서브에이전트 프롬프트, analysis.json 스키마, 완료 체크리스트
├── assets/example/             # 완성 예시 (합성 데이터)
├── scripts/
│   ├── parse_kakao.py          # 파서 (PC / Android / iOS)
│   ├── check_analysis.py       # analysis.json 검사
│   ├── build_report.py         # HTML + PDF 렌더러 (--pdf, --anonymize)
│   └── export_pdf.py           # Chrome/Edge 헤드리스 인쇄
└── evals/                      # 테스트 프롬프트와 합성 샘플 대화
```

## 주의

대화에는 실명·연락처·계약 같은 민감정보가 들어 있는 경우가 많습니다. 스킬은 비밀번호·계좌·전화번호를 보고서에 옮기지 않으며, 외부 공유용으로 `--anonymize`(이름을 화자A·B·C로) 옵션을 제공합니다. 이 저장소에는 실제 대화 데이터가 포함돼 있지 않습니다.
