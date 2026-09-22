# ASC 3강: 오픈소스로 에이전트 업데이트

2강에서 만든 `kakao-agenda-review`(Skill 1개 + Subagent 2개)를 오픈소스 3개로 업데이트했습니다.
2강 폴더를 그대로 이어서 고쳤고, 2강 제출 시점의 상태는 [원본 ZIP](./asc-lesson02-kakao-review.zip)에 남아 있습니다.

## 왜 바꿨나

2강 파이프라인을 **실제 카카오톡 대화 11,341줄**로 돌려 보고 나온 실패가 근거입니다.
그 실행 결과는 실명·연락처·인증번호가 있어 저장소에 넣지 않았고, 숫자만 옮겼습니다 →
[runs/test-03/00-baseline.md](./asc-lesson02-kakao-review/runs/test-03/00-baseline.md)

| 터진 문제 | 실측 | 원인 |
|---|---|---|
| 원문 마지막 줄이 어느 청크에도 안 들어감 | 11,341줄 중 1줄 | 파일 끝 개행이 없어 `wc -l`이 11,340을 반환 |
| 인용 줄 번호 어긋남 | 1,214건 중 **16건**(1.3%) | Subagent가 긴 파일을 `offset`/`limit`으로 나눠 읽으며 오프셋이 밀림 |
| 올바른 줄 찾기 | 16건을 사람이 ±50줄 훑고 grep | 자동 탐색 수단 없음 |
| 상태값 오타(`해결·정`) | 2건 | 검증 규칙이 JS에 하드코딩돼 위반 위치를 짚기 어려움 |
| 청크 분할 | 7청크를 글자 수 눈대중 | 토큰을 세지 않음 |

## 무엇을 붙였나

| 오픈소스 | 블록 | 역할 |
|---|---|---|
| [openai/tiktoken](https://github.com/openai/tiktoken) | 줄 번호·청크 분할 | 토큰 예산으로 분할, 커버리지 검사로 줄 누락 차단 |
| [rapidfuzz/RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | 인용 검증 | 어긋난 인용의 올바른 줄을 자동 탐색 |
| [ajv-validator/ajv](https://github.com/ajv-validator/ajv) | 구조 검증 | 규칙을 JSON Schema 선언으로 분리, 위반 위치를 JSON Pointer로 표시 |

도구를 만든 뒤 **이전 실행 결과에 먼저 돌려 사람이 손으로 찾았던 것을 재현하는지 확인**했습니다.
RapidFuzz는 16건을 그대로 찾아 15건의 올바른 줄 ID까지 제시했고(1건은 짧은 문구라 후보가 여러 개여서 자동 교정 불가로 표시), ajv는 status 오타 2건을 `/topics/5/status` 형태로 짚어냈습니다.

## 어떤 파일을 고쳤나

| 대상 | 파일 | 바뀐 내용 |
|---|---|---|
| Skill | [SKILL.md](./asc-lesson02-kakao-review/.claude/skills/kakao-agenda-review/SKILL.md) | 2단계를 `chunk_by_tokens.py` 호출로 교체(+`coverage.complete` 확인 전 진행 금지). 6단계를 ajv·RapidFuzz 2단 관문으로. 청크가 여러 개일 때 메인이 청크 간 연결을 책임진다는 규칙 추가. 공개 범위 절 추가 |
| Subagent A | [kakao-agenda-analyst.md](./asc-lesson02-kakao-review/.claude/agents/kakao-agenda-analyst.md) | "offset·limit으로 나눠 읽지 말 것" 읽기 규칙 추가. 줄 ID는 파일 접두어를 그대로 복사. 허용 상태값 밖 신규 값 금지 |
| Subagent B | [kakao-evidence-reviewer.md](./asc-lesson02-kakao-review/.claude/agents/kakao-evidence-reviewer.md) | 같은 읽기 규칙. RapidFuzz 결과를 먼저 확인해 `auto_fix`를 수정 제안에 반영. revise·hold 시 `proposed_change` 필수 |
| 신규 | [scripts/](./asc-lesson02-kakao-review/scripts/) `chunk_by_tokens.py` · `check_citations.py` · `validate_schema.mjs` | 각 도구 호출부 |
| 신규 | [schemas/](./asc-lesson02-kakao-review/schemas/) | 하드코딩 규칙을 JSON Schema로 |

변경 전후 diff: [runs/test-03/00-diff.txt](./asc-lesson02-kakao-review/runs/test-03/00-diff.txt)
2강 스크립트 `scripts/core.mjs`·`verify.mjs`는 그대로 두었습니다.

## 실행 결과

합성 대화 132줄로 파이프라인 전체를 돌렸습니다 → [runs/test-03/](./asc-lesson02-kakao-review/runs/test-03/)

tiktoken 청킹 4청크(커버리지 완전) → 분석 Subagent 4회(안건 29개) → ajv·RapidFuzz 관문 → 검토 Subagent 4회(accept 22 / revise 7 / hold 0) → 관문 → 메인 조율 34건 → 최종 검증

| 항목 | 업데이트 전 | 업데이트 후 |
|---|---|---|
| 인용 줄 번호 드리프트 | 1,214건 중 16건 (1.3%) | 101건 중 **0건** |
| 청크 커버리지 | 마지막 1줄 누락 | 완전 |
| Subagent 파일 읽기 | offset 분할 | 전원 `tool_uses` 1회 |
| 스키마 위반 | 사람이 수동 발견 | ajv 자동, 위치 표시 |
| 검증 시점 | 보고서 작성 후 1회 | 분석 직후·검토 직후·최종 **3회** |

- [최종 보고서](./asc-lesson02-kakao-review/runs/test-03/06-final-report.md)
- [조율 기록](./asc-lesson02-kakao-review/runs/test-03/03-coordination.md)

### 검토 Subagent가 잡아낸 것

합성 대화를 만들 때 실수로 넣은 **날짜·요일 불일치**(10월 24일이 토요일이면 10월 17일도 토요일인데 "10월 17일 금요일"로 표기)를 검토 Subagent가 찾아냈습니다. 실제 단톡방에도 흔한 오류라 고치지 않고 사람 확인 사항으로 남겼습니다. 그 밖에 "반영하겠습니다"를 완료로 분류한 건, 무기한 보류를 해결로 분류한 건도 지적해 둘 다 반영했습니다.

## 직접 돌려보기

```bash
cd asc-lesson02-kakao-review
pip install -r requirements.txt     # tiktoken, rapidfuzz
npm install                         # ajv

python scripts/chunk_by_tokens.py examples/synthetic-chat-long.txt --out work --budget 2000
node scripts/validate_schema.mjs --schema schemas/analyst-output.schema.json --json <분석결과.json>
python scripts/check_citations.py --indexed work/indexed.txt --json <결과.json>
```

Claude 앱 **Code 탭 → Local → Select folder** 에서 `asc-lesson02-kakao-review` 폴더를 열면 Skill과 Subagent가 인식됩니다.

## 포함하지 않은 것

실제 카카오톡 원문과 그 실행 결과(`runs/test-02/`)는 실명·연락처·법인 인증번호가 있어 커밋하지 않았습니다. `.gitignore`로 막아두었고, 근거가 되는 숫자만 `runs/test-03/00-baseline.md`에 옮겼습니다.

[다운로드용 ZIP](./asc-lesson03-update.zip)은 과제 제출본과 같은 내용입니다.
