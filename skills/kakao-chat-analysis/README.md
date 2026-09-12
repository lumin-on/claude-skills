# kakao-chat-analysis

카카오톡 대화 내보내기 파일(.txt)을 처음부터 끝까지 읽고 **"이 방에서 어떤 논의가 있었는가"**를 사람이 읽기 좋은 보고서(HTML + PDF)로 정리하는 Claude 스킬입니다.

단톡방·오픈채팅 로그를 넣으면 다음 다섯 가지를 근거와 함께 보여줍니다.

1. 누가 말했고, 각자 이 방에서 어떤 역할인가
2. 날짜별로 어떤 논의가 있었나
3. 주제(스레드)별로 이야기가 어떻게 시작되어 어떻게 발전했나
4. 그 주제를 누가 이어받아 처리했나
5. 어떻게 끝났나 — 해결 / 담당 지정 / 진행 중 / 흐지부지(답 없이 사라짐) / 정보공유

키워드 빈도나 방법론 설명은 넣지 않습니다. "무슨 얘기가 오갔고 무엇이 남았는가"만 다룹니다.

**결과 샘플** (가상의 등산 동호회 대화 39건으로 생성): [웹페이지로 보기](https://amber-on.github.io/claude-skills/samples/kakao-chat-analysis/report.html) · [PDF](../../docs/samples/kakao-chat-analysis/report.pdf) · [HTML 원본](../../docs/samples/kakao-chat-analysis/report.html)

![보고서 미리보기](../../docs/samples/kakao-chat-analysis/preview.png)

웹페이지 링크는 저장소의 GitHub Pages(Settings → Pages → `main` / `/docs`)를 켠 뒤에 동작합니다.

---

## 어떤 AI에서 쓸 수 있나

| 환경 | 사용 가능 여부 | 비고 |
|---|---|---|
| **Claude Code** (터미널, 데스크톱 앱, VS Code 확장) | ✅ 그대로 사용 | 이 스킬의 기본 환경. 긴 대화는 서브에이전트가 구간을 나눠 읽습니다. |
| **Claude 앱** (claude.ai 웹·데스크톱) | ✅ 커스텀 스킬 업로드 | 유료 플랜에서 설정 → 기능(Capabilities) → 스킬에 zip 업로드. 샌드박스에 Chrome이 없어 PDF는 만들지 못하고 HTML만 나옵니다. |
| **ChatGPT, Gemini, Cursor, Codex 등** | ⚠️ 형식은 인식 못 함, 절차는 재현 가능 | `SKILL.md` 형식(Agent Skills)은 Claude 전용입니다. 다만 스크립트는 파이썬 표준 라이브러리만 쓰므로 어디서든 실행되고, `SKILL.md`와 `references/reading-guide.md`를 프롬프트로 붙여 넣으면 다른 에이전트로 같은 절차를 따라 할 수 있습니다. 결과 품질은 그 모델이 원문을 끝까지 읽고 상태 판정표를 지키는지에 달려 있습니다. |
| **AI 없이 수동 실행** | ✅ 부분 | 파싱·검사·렌더링은 스크립트로 되고, 대화를 읽고 `analysis.json`을 쓰는 3단계만 사람이 직접 합니다. |

요구 사항: Python 3.10 이상(추가 패키지 없음). PDF 출력에는 Chrome 또는 Edge가 설치돼 있어야 합니다(헤드리스 인쇄).

---

## 다운로드와 설치

### 1) 받기

```bash
git clone https://github.com/amber-on/claude-skills.git
```

또는 GitHub 페이지의 **Code → Download ZIP**으로 받아 압축을 풉니다.

### 2) Claude Code에 설치

스킬 폴더(`kakao-chat-analysis/`)를 스킬 디렉터리에 복사합니다.

- 특정 프로젝트에서만: `<프로젝트>/.claude/skills/kakao-chat-analysis/`
- 모든 프로젝트에서: `~/.claude/skills/kakao-chat-analysis/` (Windows는 `C:\Users\<이름>\.claude\skills\kakao-chat-analysis\`)

```bash
mkdir -p ~/.claude/skills
cp -r claude-skills/skills/kakao-chat-analysis ~/.claude/skills/
```

Claude Code를 다시 열면 스킬 목록에 `kakao-chat-analysis`가 보입니다.

### 3) Claude 앱에 업로드 (선택)

스킬 폴더를 zip으로 묶어 올립니다. zip 최상위에 `kakao-chat-analysis/SKILL.md`가 있어야 합니다.

```bash
cd claude-skills/skills && zip -r ../../kakao-chat-analysis.zip kakao-chat-analysis -x "*/__pycache__/*"
```

Claude 앱 → 설정 → 기능(Capabilities) → 스킬 → 업로드.

---

## 사용법

### 카카오톡에서 대화 내보내기

- **PC**: 채팅방 오른쪽 위 메뉴 → 대화 내보내기 → 텍스트만 저장 → `KakaoTalk_날짜.txt`
- **모바일**: 채팅방 설정(≡) → 대화 내용 내보내기 → 텍스트만 → 파일로 저장/공유

세 형식 모두 자동 인식됩니다.

```
[이름] [오전 9:12] 본문                      ← PC
2025년 1월 5일 오후 3:12, 이름 : 본문          ← Android
2025. 1. 5. 오후 3:12, 이름 : 본문             ← iOS
```

### Claude Code에서

내보낸 파일이 있는 폴더에서 Claude Code를 열고 이렇게 말하면 됩니다.

```
KakaoTalk_20250105.txt 분석해줘. 누가 있고 무슨 얘기가 오갔는지, 어떻게 끝났는지 정리해줘.
```

또는 "이 단톡방에서 결정된 게 뭐고 누가 하기로 했는데 안 한 게 뭐야", "오픈채팅 로그 주제 흐름 정리해줘"처럼 물어도 스킬이 뜹니다.

스킬은 네 단계로 움직입니다.

| 단계 | 하는 일 | 도구 |
|---|---|---|
| 1. 파싱 | 메시지 단위로 나누고 날짜별 원문·통계를 만든다 | `scripts/parse_kakao.py` |
| 2. 읽기 | 날짜별 원문을 **전부** 읽고 구간 노트를 쓴다(1,500건 초과면 서브에이전트가 나눠 읽음) | `references/reading-guide.md` |
| 3. 통합 | 같은 사안을 날짜 넘어 하나의 스레드로 묶고 상태를 판정해 `analysis.json`을 쓴다 | `scripts/check_analysis.py`가 검사 |
| 4. 렌더 | HTML과 PDF 보고서를 만든다 | `scripts/build_report.py --pdf` |

산출물은 원본 파일 옆에 `<방 이름>_논의분석.html`, `.pdf`로 생기고, 중간 결과(파싱 결과·노트·`analysis.json`)는 `.kakao-analysis/<파일명>/`에 남습니다. `analysis.json`만 고쳐서 다시 렌더할 수 있습니다.

### 수동 실행 (에이전트 없이)

```bash
python skills/kakao-chat-analysis/scripts/parse_kakao.py chat.txt --out work
# work/chunks/*.txt 를 읽고 references/reading-guide.md 의 스키마대로 work/analysis.json 을 작성
python skills/kakao-chat-analysis/scripts/check_analysis.py --data work --analysis work/analysis.json
python skills/kakao-chat-analysis/scripts/build_report.py --data work --analysis work/analysis.json --out report.html --pdf
```

`--anonymize`를 붙이면 화자 이름이 화자A·B·C로 바뀝니다(외부 공유용).

---

## 보고서 구성

1. **한눈에 보기** — 무엇이 논의됐고, 무엇이 닫혔고, 무엇이 남았는지 5~8줄
2. **화자와 역할** — 발화량이 아니라 "무엇을 가져오고 누구에게 어떻게 반응하는가"로 읽은 역할. 오픈채팅은 상위 7명 + 그 외
3. **날짜별 논의** — 일별 메시지 수 막대와 하루 한 줄 다이제스트
4. **주제별 흐름과 결말** — 사업·영역별로 묶은 스레드 카드(기간·주도·흐름·결말·상태 배지)
5. **열려 있거나 사라진 것** — 담당만 정해졌거나, 진행 중이거나, 답 없이 사라진 스레드와 확인 포인트
6. **용어집** — 대화에 나온 사람·조직·제품

상태는 다섯 가지로 고정돼 있습니다.

| 상태 | 뜻 |
|---|---|
| 해결·결정 | 결과물이나 결정이 대화 안에서 확인됨 |
| 담당 지정 | 누가 하겠다고 했지만 이행 확인이 없음 |
| 진행 중 | 마지막 언급이 작업 중이거나 다음 일정이 잡혀 있음 |
| 흐지부지 | 질문·제안·경고 뒤 응답이 없음, 또는 조언이 기각되고 끝남 |
| 정보공유 | 결정을 요구하지 않는 공유·잡담 |

---

## 매번 같은 품질이 나오게 하는 장치

- **원문 전부 읽기** — 샘플링이나 키워드 검색으로는 "답이 없던 자리"를 잡을 수 없습니다.
- **고정된 상태 판정표** — 위 다섯 가지와 판정 기준이 `SKILL.md`에 있습니다.
- **스키마 검사** — `check_analysis.py`가 모든 날짜의 다이제스트, 화자 이름 일치, 스레드 필수 항목, 열린 스레드의 확인 포인트를 검사하고, 오류가 있으면 렌더를 막습니다.
- **고정 렌더러** — 보고서 구성과 스타일은 `build_report.py`가 정합니다.
- **완성 예시** — 합성 대화 39건 → 구간 노트 → `analysis.json` 한 벌이 `assets/example/`에 있어 깊이와 말투의 기준이 됩니다.

---

## 폴더 구조

```
skills/kakao-chat-analysis/
├── SKILL.md                    # 절차, 상태 판정 기준, 쓰기 규칙 (Claude가 읽는 본문)
├── references/reading-guide.md # 구간 노트 양식, 서브에이전트 프롬프트, analysis.json 스키마, 완료 체크리스트
├── assets/example/             # 완성 예시 (합성 데이터)
├── scripts/
│   ├── parse_kakao.py          # 파서 (PC / Android / iOS)
│   ├── check_analysis.py       # analysis.json 검사
│   ├── build_report.py         # HTML + PDF 렌더러 (--pdf, --anonymize)
│   └── export_pdf.py           # Chrome/Edge 헤드리스 인쇄
└── evals/                      # 테스트 프롬프트와 합성 샘플 대화
```

---

## 개인정보에 대해

카톡 대화에는 실명, 연락처, 계약·금전 정보가 들어 있는 경우가 많습니다.

- 스킬은 비밀번호·계좌·전화번호를 보고서에 옮기지 않고, 노출 사실만 각주에 남깁니다.
- 외부 공유용으로 `--anonymize` 옵션이 있습니다.
- 보고서는 파일로만 만들고 공개 URL로 게시하지 않습니다.
- **이 저장소에는 실제 대화 데이터가 포함돼 있지 않습니다.** 예시(`assets/example/`, `evals/`)는 모두 가상의 등산 동호회 대화입니다. `.gitignore`가 `KakaoTalk_*.txt`, 생성된 보고서, 작업 폴더를 제외하도록 돼 있습니다.
