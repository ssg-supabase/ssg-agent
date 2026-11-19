"""3단계: GPT 이미지 생성 테스트.

실행:  python make_image.py "만들고 싶은 이미지 설명"
예)    python make_image.py "AI 로봇이 영상을 편집하는 귀여운 일러스트, 밝은 색감"
"""
import sys

from dotenv import load_dotenv

from tools.gpt_image import generate_image

load_dotenv()

if len(sys.argv) < 2:
    print('사용법: python make_image.py "만들고 싶은 이미지 설명"')
    sys.exit(1)

print("GPT가 이미지를 그리는 중... (10~60초)")
path = generate_image(sys.argv[1])
print(f"[저장됨] {path}")
