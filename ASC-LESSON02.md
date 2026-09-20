# ASC 2강: 카카오톡 안건 판단·검증

1강의 kakao-chat-analysis에서 안건 판단 부분을 별도 Subagent로 나눈 학습용 확장입니다. 실시간 카카오톡 연결 없이 내보내기 텍스트를 사용합니다.

## GitHub에 올리는 범위
- Subagent 정의 2개, 재사용 Skill 1개
- 개인정보 없는 합성 대화(실제 대화가 아님)
- 실제 전달한 프롬프트와 실제 Subagent 응답 원본
- 메인 Agent의 조율 기록, 최종 JSON 및 Markdown 보고서
- 줄 번호·인용·구조 검증 스크립트와 검사 결과
- 실행 방법과 한계

실제 카카오톡 원문, 실명·연락처·계좌, 비밀번호·토큰, 설정 비밀값은 포함하지 않습니다. 기존 1강 파일은 변경하지 않습니다.

## 다운로드

이 저장소의 [asc-lesson02-kakao-review.zip](./asc-lesson02-kakao-review.zip)을 받아 압축을 풀면 아래 파일이 포함됩니다.

## 구성
- .claude/agents/kakao-agenda-analyst.md: 안건 상태 분석자
- .claude/agents/kakao-evidence-reviewer.md: 근거 검토자
- .claude/skills/kakao-agenda-review/SKILL.md: 입력→분석→검토→조율→검증 절차
- examples/: 가상 대화와 원문 줄 번호
- prompts/: 각 Subagent에게 실제 전달한 입력
- results/: 수정하지 않은 Agent 응답, 메인 조율, 최종 결과, 검증 결과
- scripts/core.mjs: 번호 부여·JSON/인용 검사·Markdown 렌더
- scripts/verify.mjs: Node.js에서 결과 검증 및 보고서 재생성
- PROCESS.md: 사람/Skill/Subagent 역할과 실행 순서
- RUN.md: 실제 실행 환경과 검증 범위

## 이번 실제 실행 결과
합성 대화 16개 메시지에서 6개 안건을 분석했습니다. 검토자가 5개를 채택하고 점심 주문 제안 1개에 라벨 완화를 제안했습니다. 메인 Agent는 원문을 다시 확인하고 점심을 판단 보류로 바꿨으며, 참가비 결정과 실제 입금 이행을 구분했습니다. 인용 42개와 구조 검사를 통과했고 잘못된 인용을 넣은 음성 테스트도 오류를 잡았습니다.

## 재실행
### Claude Code에서 판단 단계 재실행
1. 압축을 풀고 이 패키지 폴더를 프로젝트로 엽니다. .claude 폴더가 포함돼 있는지 확인합니다.
2. Claude Code에 '.claude/skills/kakao-agenda-review/SKILL.md 절차대로 examples/synthetic-chat.txt를 분석해줘. kakao-agenda-analyst와 kakao-evidence-reviewer를 별도 Subagent로 순차 호출하고 prompts와 results에 실제 입력·결과를 남겨줘. 외부 게시/발송은 하지 마.'라고 요청합니다.
3. Claude Code의 Subagent 인식 및 실제 실행 여부를 확인하세요. 이 패키지의 이번 실측 환경은 Aside이며 Claude Code 호환 실행은 아직 검증하지 않았습니다.
4. 모델은 로컬 설정을 사용하도록 정의 파일에서 고정하지 않았습니다. 실행 모델에 따라 판단 결과가 달라질 수 있습니다.

### 저장된 결과 검증·보고서 재생성
Node.js 18 이상에서 패키지 루트 기준으로 실행합니다. 외부 패키지는 없습니다.

    node scripts/verify.mjs

이 명령은 LLM을 호출하지 않습니다. 저장된 JSON의 형식·인용을 검증하고 Markdown 보고서만 다시 만듭니다. 의미상 정답을 자동 보증하지 않습니다.

## 기존 1강 스킬과의 관계
기존 스킬: https://github.com/lumin-on/claude-skills/tree/main/skills/kakao-chat-analysis
이번 파일은 1강의 analysis.json 전체 스키마와 별도인 안건 검증 실험입니다. 기존 HTML/PDF 렌더러 자동 연결은 구현하지 않았습니다. 상태가 불확실하면 null/판단 보류를 허용하므로 연결 시 명시적 스키마 매핑이 필요합니다.

## 제출 여부
이 패키지 생성 및 GitHub 공개는 ASC 과제 최종 제출과 별개입니다. 과제의 제출하기 버튼은 사용자가 직접 검토한 뒤 누릅니다.
