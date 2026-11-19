# ssg-agent

Claude가 지휘하고, Gemini(동영상 분석)와 GPT(이미지 생성)를 도구로 쓰는 에이전트 연습 프로젝트.

## 처음 설정 (PC마다 한 번)

```bash
git clone https://github.com/ssg-supabase/ssg-agent.git
cd ssg-agent
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

그다음 `.env` 파일을 열어 API 키 3개를 넣습니다. (`.env`는 GitHub에 올라가지 않음)

## 작업 습관

- 시작할 때: `git pull`
- 끝날 때: `git add .` → `git commit -m "내용"` → `git push`

## 설계도

전체 쇼츠 자동화 설계: [docs/blueprint.md](docs/blueprint.md)

## 진행 단계

- [x] 1단계: Claude 연결 테스트 — `python hello_claude.py`
- [x] 2단계: Gemini 동영상 분석 — `python analyze_video.py 유튜브링크`
- [x] 3단계: GPT 이미지 생성 — `python make_image.py "이미지 설명"`
- [x] 4단계: Claude 지휘자 에이전트 — `python agent.py 유튜브링크` (분석 → 사실 확인 → 썸네일 → 보고서)
- [x] M1 뼈대: 작업공간·채널·프로젝트 기록, 장르 템플릿, AI 역할 슬롯 — `python ssg.py --help`
- [ ] M2 첫 mp4 (내레이션형): 주제 → 지침 → 대본 → 음성 → 이미지 → 타임라인 → mp4, 실제 비용·시간 기록
- [ ] M2b 비교 실험: 같은 주제를 힉스필드 숏드라마 480p로 만들어 품질·비용·9:16 비교
- [ ] M3 스킬로 묶기: M2 과정을 Claude Code 스킬 하나로

방향(v0.4): 영상 생성은 좋은 도구를 빌려 쓰고, ssg-agent는 **채널 운영 감독**(기획·규칙·장면별 제작 방식·비용·이력·업로드)을 맡는다 — [설계도 0-1](docs/blueprint.md)

관리자 화면 시안(테마 3종 전환): `docs/admin-prototype.html` 을 브라우저로 열기 (M8 기준 자료로 동결)

참고 자료: [숏드라마 영상 분석](docs/research/2026-11-19_shortdrama-review/)

## 기록

- 2026-11-18: GitHub 연결 테스트, 1단계 파일 준비, Windows 설치 안내서 작성 (`docs/setup-guide.html`)
- 2026-11-19: 2~4단계 완성. 에이전트 첫 실행 성공 (`results/20261119_1357_QISW1mMdK-0_report.md`)
