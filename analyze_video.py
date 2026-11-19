"""2단계: Gemini 동영상 분석 테스트.

실행:  python analyze_video.py 유튜브링크
예)    python analyze_video.py https://www.youtube.com/shorts/QISW1mMdK-0
"""
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from tools.gemini_video import analyze_video

load_dotenv()

QUESTION = """이 영상을 한국어로 분석해 주세요.

1. 한 줄 요약
2. 영상에서 하는 말 (들리는 대로 받아쓰기)
3. 영상이 사실이라고 주장하는 내용을 하나씩 목록으로 정리
   (나중에 사실 확인을 할 수 있도록, 각 주장을 짧고 구체적인 문장으로)
4. 화면에 보이는 것 (자막, 장면, 인물 등)
"""

if len(sys.argv) < 2:
    print("사용법: python analyze_video.py 유튜브링크_또는_파일경로")
    sys.exit(1)

source = sys.argv[1]
print("Gemini가 영상을 보는 중... (10~60초)")
result = analyze_video(source, QUESTION)
print(result)

# 결과를 results 폴더에 파일로 저장 (git push 하면 Claude도 볼 수 있음)
m = re.search(r"(?:shorts/|youtu\.be/|v=)([A-Za-z0-9_-]{11})", source)
name = m.group(1) if m else Path(source).stem
out = Path("results") / f"{datetime.now():%Y%m%d}_{name}.md"
out.parent.mkdir(exist_ok=True)
out.write_text(f"# 영상 분석: {source}\n\n{result}\n", encoding="utf-8")
print(f"\n[저장됨] {out}")
