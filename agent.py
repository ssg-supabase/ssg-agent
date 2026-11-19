"""4단계: Claude 지휘자 에이전트.

유튜브 링크를 주면 Claude가 스스로 순서를 정해 도구를 씁니다.
  ① Gemini로 영상 분석
  ② 웹 검색으로 영상 속 주장 사실 확인
  ③ GPT로 썸네일 이미지 생성
  ④ 결과를 results 폴더에 보고서(.md)로 저장

실행:  python agent.py 유튜브링크
예)    python agent.py https://www.youtube.com/shorts/QISW1mMdK-0
"""
import re
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from anthropic import beta_tool
from dotenv import load_dotenv

from tools.gemini_video import analyze_video as gemini_analyze_video
from tools.gpt_image import generate_image as gpt_generate_image

load_dotenv()


# ---------------------------------------------------------------------------
# Claude에게 줄 도구들
# (도구 안에서 에러가 나도 프로그램을 멈추지 않고, 에러 내용을 Claude에게 알려
#  Claude가 다른 방법을 찾거나 보고서에 적도록 합니다.)
# ---------------------------------------------------------------------------
@beta_tool
def analyze_video(video_url: str, question: str) -> str:
    """Gemini로 유튜브 영상(또는 동영상 파일)을 보고 분석 결과를 텍스트로 돌려줍니다.
    영상의 요약, 받아쓰기, 주장 목록, 화면 내용이 필요할 때 사용하세요.

    Args:
        video_url: 유튜브 링크 또는 동영상 파일 경로
        question: 영상에 대해 알고 싶은 것 (구체적으로)
    """
    print("  → [Gemini] 영상 분석 중... (재시도 포함 최대 몇 분)")
    try:
        return gemini_analyze_video(video_url, question)
    except Exception as e:  # noqa: BLE001
        return f"영상 분석 실패: {e}"


@beta_tool
def generate_image(prompt: str, size: str = "1024x1536") -> str:
    """GPT로 이미지를 만들어 저장하고, 저장된 파일 경로를 돌려줍니다.

    Args:
        prompt: 만들 이미지에 대한 자세한 설명 (영어로 쓰면 품질이 더 좋습니다)
        size: 1024x1536(세로, 쇼츠 썸네일) / 1536x1024(가로, 일반 썸네일) / 1024x1024
    """
    print("  → [GPT] 썸네일 그리는 중...")
    try:
        return f"이미지 저장 완료: {gpt_generate_image(prompt, size=size)}"
    except Exception as e:  # noqa: BLE001
        return f"이미지 생성 실패: {e}"


# Anthropic 서버에서 실행되는 웹 검색 도구 (따로 구현할 필요 없음)
WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}


SYSTEM = """당신은 유튜브 영상을 검증하고 썸네일을 만드는 에이전트입니다.
사용자가 영상 링크를 주면 아래 순서로 일하세요.

1. analyze_video 로 영상을 분석합니다. 한 줄 요약, 받아쓰기, 영상 속 사실 주장 목록,
   화면에 보이는 숫자와 자막을 요청하세요.
2. 영상 속 주장 하나하나를 web_search 로 확인합니다.
   - 광고·홍보 영상이면 그 사실도 밝히세요.
   - 말과 화면의 숫자가 서로 다르면 짚어 주세요.
   - 근거를 찾지 못한 주장은 '근거 없음'으로 솔직하게 적으세요.
3. generate_image 로 영상 내용에 어울리는 썸네일을 한 장 만듭니다.
   글자는 넣지 말고, 그림만 영어 프롬프트로 요청하세요.
4. 마지막 답변은 아래 형식의 한국어 마크다운 보고서 하나로만 작성하세요.

# 영상 검증 보고서
## 한 줄 요약
## 영상 정보 (채널, 광고 여부)
## 사실 확인
| 영상 속 주장 | 판정 | 근거 |
판정은 ✅ 사실 / ⚠️ 조건부·과장 / ❓ 근거 없음 / ❌ 거짓 중 하나.
## 종합 결론 (2~3문장)
## 썸네일 (저장 경로, 사용한 프롬프트)
## 출처 (마크다운 링크 목록)

도구가 실패하면 한 번은 다른 방법을 시도하고, 그래도 안 되면 보고서에 실패 사실을 적으세요.
"""


def main() -> None:
    if len(sys.argv) < 2:
        print("사용법: python agent.py 유튜브링크")
        sys.exit(1)
    url = sys.argv[1]

    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model="claude-opus-5-5",
        max_tokens=16000,
        system=SYSTEM,
        tools=[analyze_video, generate_image, WEB_SEARCH],
        messages=[{"role": "user", "content": f"이 영상을 검증하고 썸네일을 만들어줘: {url}"}],
        output_config={"effort": "high"},
        # 안전 필터에 걸리면 서버가 자동으로 다른 모델로 재시도
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        max_iterations=20,
    )

    print("Claude 에이전트 시작...")
    final = None
    total_in = total_out = 0
    for message in runner:
        final = message
        total_in += message.usage.input_tokens
        total_out += message.usage.output_tokens
        for block in message.content:
            if block.type == "server_tool_use" and block.name == "web_search":
                print(f"  → [웹 검색] {block.input.get('query', '')}")

    if final is None:
        sys.exit("Claude에게서 응답을 받지 못했습니다.")
    if final.stop_reason == "refusal":
        sys.exit(f"요청이 거절되었습니다: {final.stop_details}")

    report = "".join(b.text for b in final.content if b.type == "text").strip()
    if final.stop_reason in ("max_tokens", "pause_turn"):
        report += f"\n\n> ⚠️ 작업이 끝까지 완료되지 않았습니다 (stop_reason: {final.stop_reason})."

    m = re.search(r"(?:shorts/|youtu\.be/|v=)([A-Za-z0-9_-]{11})", url)
    name = m.group(1) if m else Path(url).stem
    out = Path("results") / f"{datetime.now():%Y%m%d_%H%M}_{name}_report.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(f"> 원본 영상: {url}\n\n{report}\n", encoding="utf-8")

    print("\n" + report)
    print(f"\n[저장됨] {out}")
    print(f"[Claude 사용 토큰] 입력 {total_in:,} / 출력 {total_out:,}")


if __name__ == "__main__":
    main()
