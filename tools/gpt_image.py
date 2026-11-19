"""GPT(OpenAI)로 이미지를 만드는 도구."""
import base64
import os
from datetime import datetime
from pathlib import Path

from openai import NotFoundError, OpenAI

# .env 에 OPENAI_IMAGE_MODEL=... 을 적으면 다른 모델로 바꿀 수 있습니다.
DEFAULT_MODEL = "gpt-image-2"
BACKUP_MODELS = ["gpt-image-1.5"]


def generate_image(prompt: str, size: str = "1024x1536", quality: str = "low") -> str:
    """이미지를 만들어 results 폴더에 저장하고, 저장한 파일 경로를 돌려줍니다.

    Args:
        prompt: 만들 이미지 설명
        size: 1024x1536(세로, 쇼츠용) / 1536x1024(가로, 썸네일용) / 1024x1024(정사각형)
        quality: low(싸고 빠름, 연습용) / medium / high(비싸고 선명)
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    models = [os.getenv("OPENAI_IMAGE_MODEL", DEFAULT_MODEL)] + BACKUP_MODELS

    for i, model in enumerate(models):
        try:
            result = client.images.generate(model=model, prompt=prompt, size=size, quality=quality)
            break
        except NotFoundError:
            if i == len(models) - 1:
                raise
            print(f"{model}: 사용할 수 없는 모델 → {models[i + 1]} 로 다시 시도...")

    out = Path("results") / f"{datetime.now():%Y%m%d_%H%M%S}_image.png"
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(base64.b64decode(result.data[0].b64_json))
    print(f"(사용한 모델: {model})")
    return str(out)
