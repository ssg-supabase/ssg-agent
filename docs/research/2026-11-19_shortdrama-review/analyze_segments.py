"""드라마 구간만 잘라서 Gemini로 분석 (낮은 해상도, 1초 1장). 결과와 토큰 사용량을 파일로 저장."""
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv(Path("C:/ssg-agent/.env"))
OUT = Path(sys.argv[1])
MODELS = [os.getenv("GEMINI_MODEL", "gemini-3.8-flash"), "gemini-3.7-flash", "gemini-3.5-flash"]

SEGMENTS = [
    ("A1_aion_intro", "https://www.youtube.com/watch?v=r3G_irdPLmk", 0, 66, "AI:ON 영상 도입부 (완성 숏드라마 미리보기)"),
    ("A2_aion_final", "https://www.youtube.com/watch?v=r3G_irdPLmk", 546, 617, "AI:ON 영상의 완성된 1분 숏드라마 공개 구간"),
    ("B1_dakdori_intro", "https://www.youtube.com/watch?v=uG7_MR314ew", 0, 83, "닥또리 영상 도입부 (힉스필드 숏드라마 결과물)"),
    ("B2_dakdori_4people", "https://www.youtube.com/watch?v=uG7_MR314ew", 308, 385, "닥또리 영상의 4명이 나오는 1분 드라마 자동 생성 결과"),
]

QUESTION = """이 구간은 AI(힉스필드 등)로 만든 숏드라마가 나오는 부분입니다. 유튜브 쇼츠 자동화 도구를 설계하려고 합니다.
설명·강의 화면은 빼고, AI로 만든 드라마 장면만 기준으로 아래를 한국어로 짧고 구체적으로 정리해 주세요.

1. 장면 목록: 시작 시간(초) · 화면 크기(클로즈업/미디엄/와이드) · 카메라 움직임 · 무슨 일이 일어나는지 · 대사
2. 편집 리듬: 컷 수, 평균 컷 길이(초), 전환 방식
3. 화면 비율(16:9인지 9:16인지), 세로로 잘라 쇼츠로 쓸 때 문제될 점
4. 캐릭터 일관성: 장면마다 얼굴·옷이 유지되는지, 깨진 부분이 있다면 시간과 내용
5. 화질 문제: 피부·손·눈·배경의 어색함, 움직임 깨짐 (시간 포함)
6. 소리: 대사 목소리가 자연스러운 한국어인지, 입 모양이 맞는지, 효과음·음악·자막 유무와 스타일
7. 첫 3초 훅과 이야기 구조 (반전이 어디 있는지)
8. 이 결과를 "AI 이미지 + AI 음성 + 움직임 효과(줌·패닝) + 자막"만으로 비슷하게 만들 수 있는 부분과, 꼭 영상 생성 AI가 필요한 부분
9. 전체 품질 점수(10점 만점)와 한 줄 평
"""


def run(seg):
    key, url, start, end, label = seg
    part = types.Part(file_data=types.FileData(file_uri=url),
                      video_metadata=types.VideoMetadata(start_offset=f"{start}s", end_offset=f"{end}s", fps=1))
    cfg = types.GenerateContentConfig(media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW)
    contents = types.Content(parts=[part, types.Part(text=f"[구간: {label}]\n" + QUESTION)])
    last = None
    for model in MODELS:
        for wait in (0, 15, 40):
            if wait:
                time.sleep(wait)
            try:
                r = client.models.generate_content(model=model, contents=contents, config=cfg)
                u = r.usage_metadata
                usage = {"model": model, "prompt": u.prompt_token_count, "output": u.candidates_token_count,
                         "total": u.total_token_count}
                return r.text, usage
            except (errors.ServerError, errors.ClientError) as e:
                last = e
                print(f"  {model}: {e.code} {str(e)[:120]}", flush=True)
                if e.code == 404:
                    break
                if e.code not in (429, 500, 503):
                    raise
    raise RuntimeError(f"실패: {last}")


client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
summary = []
for seg in SEGMENTS:
    print(f"▶ {seg[0]} ({seg[3] - seg[2]}초) 분석 중...", flush=True)
    text, usage = run(seg)
    (OUT / f"{seg[0]}.md").write_text(f"# {seg[4]}\n{seg[1]} {seg[2]}s~{seg[3]}s\n\n{text}", encoding="utf-8")
    usage["segment"] = seg[0]
    summary.append(usage)
    print(f"  완료 · 토큰 {usage}", flush=True)
(OUT / "usage.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("합계 토큰:", sum(s["total"] for s in summary))
