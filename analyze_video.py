"""2단계: Gemini 동영상 분석 테스트.

실행:  python analyze_video.py 유튜브링크
예)    python analyze_video.py https://www.youtube.com/shorts/QISW1mMdK-0
"""
import sys

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

print("Gemini가 영상을 보는 중... (10~60초)")
print(analyze_video(sys.argv[1], QUESTION))
