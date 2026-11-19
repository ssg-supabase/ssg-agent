"""Gemini로 동영상을 분석하는 도구.

유튜브 링크(공개 영상)나 내 컴퓨터의 동영상 파일 모두 사용할 수 있습니다.
"""
import os
import re
import time

from google import genai
from google.genai import errors, types

# .env 에 GEMINI_MODEL=... 을 적으면 다른 모델로 바꿀 수 있습니다.
DEFAULT_MODEL = "gemini-3.8-flash"
# 기본 모델이 붐비거나(503) 없을 때(404) 차례로 시도할 예비 모델
BACKUP_MODELS = ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]
BUSY_CODES = (429, 500, 503)   # 일시적으로 붐빔 → 잠시 기다렸다 재시도
RETRY_WAITS = [10, 30]         # 같은 모델 재시도 전 기다릴 초


def _normalize_youtube_url(url: str) -> str:
    """youtube.com/shorts/ID, youtu.be/ID 형식을 표준 watch?v=ID 형식으로 바꿉니다."""
    m = re.search(r"(?:shorts/|youtu\.be/|v=)([A-Za-z0-9_-]{11})", url)
    return f"https://www.youtube.com/watch?v={m.group(1)}" if m else url


def _video_part(client: genai.Client, source: str) -> types.Part:
    """유튜브 링크면 그대로, 파일이면 Gemini에 업로드해서 분석 재료로 만듭니다."""
    if source.startswith("http"):
        return types.Part(file_data=types.FileData(file_uri=_normalize_youtube_url(source)))

    print("동영상 업로드 중...")
    uploaded = client.files.upload(file=source)
    while uploaded.state == types.FileState.PROCESSING:
        time.sleep(3)
        uploaded = client.files.get(name=uploaded.name)
    if uploaded.state == types.FileState.FAILED:
        raise RuntimeError("Gemini가 동영상 파일을 처리하지 못했습니다.")
    return types.Part(file_data=types.FileData(file_uri=uploaded.uri, mime_type=uploaded.mime_type))


def analyze_video(source: str, question: str) -> str:
    """동영상을 Gemini로 분석하고 결과 텍스트를 돌려줍니다.

    Args:
        source: 유튜브 링크 또는 동영상 파일 경로
        question: 영상에 대해 알고 싶은 것
    """
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents = types.Content(parts=[_video_part(client, source), types.Part(text=question)])
    models = [os.getenv("GEMINI_MODEL", DEFAULT_MODEL)] + BACKUP_MODELS

    last_error = None
    for model in models:
        for attempt in range(len(RETRY_WAITS) + 1):
            try:
                response = client.models.generate_content(model=model, contents=contents)
                print(f"(사용한 모델: {model})")
                return response.text
            except (errors.ServerError, errors.ClientError) as e:
                last_error = e
                if e.code == 404:  # 이 모델은 사용할 수 없음 → 다음 모델로
                    print(f"{model}: 사용할 수 없는 모델(404) → 다음 모델로")
                    break
                if e.code not in BUSY_CODES:
                    raise
                if attempt < len(RETRY_WAITS):
                    wait = RETRY_WAITS[attempt]
                    print(f"{model}: 붐빔({e.code}) → {wait}초 기다렸다 다시 시도...")
                    time.sleep(wait)
                else:
                    print(f"{model}: 계속 붐빔 → 다음 모델로")
    raise RuntimeError(
        "모든 Gemini 모델이 지금 응답하지 않습니다. 몇 분 뒤 다시 실행해 주세요."
    ) from last_error
