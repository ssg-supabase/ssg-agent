"""역할 슬롯과 AI 어댑터 목록 (설계도 5장).

새 AI를 붙이는 방법:
  1) 아래에 함수 하나(어댑터)를 만들고
  2) PROVIDERS 목록에 Provider(...) 한 줄을 추가합니다.
나머지 코드(단계 실행, 화면)는 역할 이름으로만 AI를 찾으므로 고칠 필요가 없습니다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable

# 역할 목록 (고정, 추가만 함)
ROLES: dict[str, str] = {
    "director": "감독",
    "video_analysis": "영상 분석",
    "planning": "기획(핵심 지침)",
    "script": "대본",
    "character_image": "캐릭터 생성",
    "scene_image": "장면 이미지",
    "video_clip": "영상 클립",
    "tts": "음성",
    "lipsync": "립싱크",
    "music": "음악",
    "sfx": "효과음",
    "transcribe": "자막 시간",
    "qa": "검수",
    "metadata": "제목·설명",
}


@dataclass
class Provider:
    id: str                       # 예: "image.gpt"
    role: str
    label: str
    needs_env: list[str] = field(default_factory=list)
    capabilities: dict = field(default_factory=dict)
    run: Callable | None = None   # None 이면 아직 연결 전(설정만 있음) 또는 직접 업로드

    def ready(self) -> tuple[bool, str]:
        if self.id.endswith(".upload"):
            return True, "직접 업로드"
        missing = [k for k in self.needs_env if not os.getenv(k)]
        if missing:
            return False, f"키 없음: {', '.join(missing)}"
        if self.run is None:
            return False, "어댑터 준비 중"
        return True, "연결됨"


# ── 어댑터: 기존 tools/ 함수를 공통 모양으로 감쌈 (import는 쓸 때만) ──

def _gemini_analyze(source: str, question: str) -> str:
    from tools.gemini_video import analyze_video
    return analyze_video(source, question)


def _gpt_image(prompt: str, size: str = "1024x1536", quality: str = "low", **_) -> str:
    from tools.gpt_image import generate_image
    return generate_image(prompt, size=size, quality=quality)


def _upload(role: str, label: str) -> Provider:
    return Provider(id=f"{role}.upload", role=role, label=label)


PROVIDERS: list[Provider] = [
    Provider("director.claude", "director", "Claude", ["ANTHROPIC_API_KEY"]),
    Provider("video_analysis.gemini", "video_analysis", "Gemini", ["GEMINI_API_KEY"],
             {"inputs": ["youtube_url", "video_file"]}, _gemini_analyze),
    Provider("planning.claude", "planning", "Claude", ["ANTHROPIC_API_KEY"]),
    Provider("script.gemini", "script", "Gemini", ["GEMINI_API_KEY"]),
    Provider("character_image.gpt", "character_image", "GPT 이미지", ["OPENAI_API_KEY"],
             {"sizes": ["1024x1536", "1536x1024", "1024x1024"], "reference_images": True}, _gpt_image),
    _upload("character_image", "직접 업로드"),
    Provider("scene_image.gpt", "scene_image", "GPT 이미지", ["OPENAI_API_KEY"],
             {"sizes": ["1024x1536", "1536x1024", "1024x1024"], "reference_images": True}, _gpt_image),
    _upload("scene_image", "직접 업로드"),
    _upload("video_clip", "직접 업로드"),
    Provider("tts.openai", "tts", "GPT 음성", ["OPENAI_API_KEY"]),
    _upload("tts", "내 녹음 업로드"),
    _upload("music", "라이브러리/직접 업로드"),
    _upload("sfx", "라이브러리/직접 업로드"),
    Provider("transcribe.openai", "transcribe", "Whisper 계열", ["OPENAI_API_KEY"]),
    Provider("qa.gemini", "qa", "Gemini", ["GEMINI_API_KEY"]),
    Provider("metadata.claude", "metadata", "Claude", ["ANTHROPIC_API_KEY"]),
]

# 작업공간 설정에 지정이 없을 때 쓰는 기본 담당
DEFAULTS: dict[str, str] = {
    "director": "director.claude",
    "video_analysis": "video_analysis.gemini",
    "planning": "planning.claude",
    "script": "script.gemini",
    "character_image": "character_image.gpt",
    "scene_image": "scene_image.gpt",
    "video_clip": "video_clip.upload",
    "tts": "tts.openai",
    "music": "music.upload",
    "sfx": "sfx.upload",
    "transcribe": "transcribe.openai",
    "qa": "qa.gemini",
    "metadata": "metadata.claude",
}

_BY_ID = {p.id: p for p in PROVIDERS}


def for_role(role: str) -> list[Provider]:
    return [p for p in PROVIDERS if p.role == role]


def get(role: str, workspace_settings: dict | None = None) -> Provider | None:
    """역할의 담당 AI: 작업공간 설정 > 기본값. (설계도 5-2: 프로젝트 지정·품질등급은 M2에서 추가)"""
    pid = (workspace_settings or {}).get(role) or DEFAULTS.get(role)
    return _BY_ID.get(pid) if pid else None


def assign(workspace_settings: dict, role: str, provider_id: str) -> None:
    if role not in ROLES:
        raise ValueError(f"모르는 역할입니다: {role}")
    p = _BY_ID.get(provider_id)
    if p is None or p.role != role:
        options = ", ".join(x.id for x in for_role(role)) or "없음"
        raise ValueError(f"{role} 역할에 쓸 수 없는 AI입니다. 선택지: {options}")
    workspace_settings[role] = provider_id
