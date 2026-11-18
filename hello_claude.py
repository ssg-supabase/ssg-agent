"""1단계: Claude API 연결 테스트.

실행:  python hello_claude.py
"""
import anthropic
from dotenv import load_dotenv

load_dotenv()  # .env 파일의 키를 환경변수로 불러옴

client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 자동 사용

response = client.beta.messages.create(
    model="claude-opus-5-5",
    max_tokens=1024,
    output_config={"effort": "low"},
    # 안전 필터에 걸리면 서버가 자동으로 다른 모델로 재시도
    betas=["server-side-fallback-2026-07-01"],
    fallbacks="default",
    messages=[{"role": "user", "content": "안녕! 한 문장으로 자기소개 해줘."}],
)

if response.stop_reason == "refusal":
    print("요청이 거절되었습니다:", response.stop_details)
else:
    for block in response.content:
        if block.type == "text":
            print(block.text)
    print(f"\n[사용 토큰] 입력 {response.usage.input_tokens} / 출력 {response.usage.output_tokens}")
