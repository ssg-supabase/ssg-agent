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

## 진행 단계

- [x] 1단계: Claude 연결 테스트 — `python hello_claude.py`
- [ ] 2단계: Gemini 동영상 분석
- [ ] 3단계: GPT 이미지 생성
- [ ] 4단계: Claude 지휘자에 두 도구 연결

## 기록

- 2026-11-18: GitHub 연결 테스트, 1단계 파일 준비, Windows 설치 안내서 작성 (`docs/setup-guide.html`)
