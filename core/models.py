"""기록의 모양(데이터 구조)과 고정 값들. 설계도 2장, 3장, 7장, 16장.

여기 정의된 이름(단계 키, 상태 값, 업로드 용도)은 화면·알림·DB가 모두 같이 쓰므로
함부로 바꾸지 않습니다. 새 값은 추가만 합니다.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from enum import Enum


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class StepStatus(str, Enum):
    PENDING = "pending"                       # 대기
    RUNNING = "running"                       # 실행 중
    AWAITING_APPROVAL = "awaiting_approval"   # 승인 대기
    DONE = "done"                             # 완료
    FAILED = "failed"                         # 실패
    SKIPPED = "skipped"                       # 건너뜀


STATUS_LABELS = {
    "pending": "대기", "running": "실행 중", "awaiting_approval": "승인 대기",
    "done": "완료", "failed": "실패", "skipped": "건너뜀",
}

# 제작 단계 (설계도 7장). 순서 = 실행 순서.
STEPS: list[tuple[str, str]] = [
    ("spec", "규격 정하기"),
    ("brief", "핵심 지침"),
    ("style", "참고 영상 분석"),
    ("cast", "캐릭터 준비"),
    ("script", "대본과 장면 콘티"),
    ("voice", "음성"),
    ("captions", "자막 시간"),
    ("visuals", "장면 이미지·클립"),
    ("sound", "음악·효과음"),
    ("timeline", "타임라인"),
    ("render", "렌더링"),
    ("qa", "검수"),
    ("metadata", "제목·설명·썸네일"),
    ("publish", "업로드"),
    ("metrics", "성과 수집"),
]
STEP_KEYS = [k for k, _ in STEPS]
STEP_LABELS = dict(STEPS)

# 자동화 수준 (설계도 7-1): 레벨별로 "승인 대기"에서 멈추는 단계
AUTOMATION_LEVELS: dict[int, set[str]] = {
    0: set(STEP_KEYS),
    1: {"brief", "cast", "script", "qa"},
    2: {"qa"},
    3: set(),
}

# 업로드 용도 태그 (설계도 2-1)
UPLOAD_PURPOSES = {
    "ref_video": "참고 영상",
    "ref_image": "참고 이미지",
    "character": "캐릭터",
    "prop": "소품",
    "background": "배경",
    "scene_asset": "완성 장면",
    "voice": "내 녹음",
    "music": "음악",
    "sfx": "효과음",
    "brand": "브랜드",
    "doc": "문서",
}

UPLOAD_MODES = ["files_only", "private", "scheduled", "public"]  # 설계도 7-2
QUALITY_LEVELS = ["practice", "normal", "high"]                   # 연습/보통/고급

# 유튜브 시작 도우미 체크리스트 (설계도 16장)
YOUTUBE_SETUP_ITEMS: list[tuple[str, str]] = [
    ("create_channel", "채널 만들기 (브랜드 계정 권장)"),
    ("name_handle", "채널 이름·핸들(@) 정하기"),
    ("phone_verify", "휴대폰 인증"),
    ("profile_banner", "프로필 사진·배너"),
    ("description", "채널 설명·키워드"),
    ("upload_defaults", "업로드 기본 설정"),
    ("audience", "시청자층(아동용 여부)"),
    ("ai_disclosure", "AI 콘텐츠 표시 이해"),
    ("monetization", "수익화 조건 확인"),
    ("studio_app", "유튜브 스튜디오 앱 설치"),
    ("api_connect", "업로드 자동화 연결"),
    ("team_roles", "팀원 권한"),
]


class _Record:
    """dict ↔ 데이터클래스 변환. 모르는 키는 무시해서, 나중에 필드가 늘어도 옛 파일을 읽을 수 있음."""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})


@dataclass
class Spec(_Record):
    """출력 규격 (설계도 3장)."""
    aspect: str = "9:16"
    width: int = 1080
    height: int = 1920
    fps: int = 30
    length_sec: int = 45
    language: str = "ko"
    platforms: list[str] = field(default_factory=lambda: ["youtube"])
    genre: str = ""
    art_style: str = ""            # 기본값 없음 — 매번 선택
    visual_mode: str = "stills_motion"   # stills_motion / ai_clips / mixed
    voice_mode: str = "ai"         # ai / my_recording / mixed
    captions: str = "word_highlight"
    quality: str = "normal"


ASPECT_SIZES = {"9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350), "16:9": (1920, 1080)}


@dataclass
class Step(_Record):
    key: str
    status: str = StepStatus.PENDING.value
    needs_approval: bool = False
    provider: str = ""
    model: str = ""
    started_at: str = ""
    finished_at: str = ""
    attempts: int = 0
    cost_usd: float = 0.0
    error: str = ""
    output: dict = field(default_factory=dict)
    updated_by: str = ""


@dataclass
class Upload(_Record):
    id: str
    purpose: str
    filename: str
    path: str                    # 프로젝트 폴더 기준 상대 경로, 또는 링크
    scope: str = "project"       # project / library
    rights_confirmed: bool = False
    note: str = ""
    added_at: str = field(default_factory=now)
    added_by: str = ""


@dataclass
class Project(_Record):
    id: str
    workspace_id: str
    channel_id: str
    title: str
    topic: str
    folder: str                  # 채널 projects/ 아래 폴더 이름
    spec: dict = field(default_factory=lambda: Spec().to_dict())
    automation_level: int = 1
    brief: dict = field(default_factory=lambda: {"candidates": [], "selected": [], "custom": ""})
    uploads: list[dict] = field(default_factory=list)
    references: list[dict] = field(default_factory=list)
    cast: list[str] = field(default_factory=list)
    steps: dict = field(default_factory=dict)
    cost_total_usd: float = 0.0
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    created_by: str = ""
    updated_by: str = ""

    def __post_init__(self):
        if not self.steps:
            self.apply_automation_level(self.automation_level)

    def apply_automation_level(self, level: int) -> None:
        """레벨에 맞춰 각 단계의 승인 필요 여부를 다시 설정 (상태는 유지)."""
        self.automation_level = level
        stop_at = AUTOMATION_LEVELS[level]
        for key in STEP_KEYS:
            step = Step.from_dict(self.steps.get(key, {"key": key}))
            step.needs_approval = key in stop_at
            self.steps[key] = step.to_dict()


@dataclass
class Channel(_Record):
    id: str                      # 슬러그 (폴더 이름)
    workspace_id: str
    name: str
    genres: list[str] = field(default_factory=list)
    defaults: dict = field(default_factory=lambda: {
        "spec": Spec().to_dict(),
        "automation_level": 1,
        "upload_mode": "files_only",
        "monthly_budget_krw": 0,       # 0 = 작업공간 한도만 적용
    })
    brand: dict = field(default_factory=dict)
    youtube_setup: dict = field(default_factory=lambda: {k: False for k, _ in YOUTUBE_SETUP_ITEMS})
    upload_accounts: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=now)
    created_by: str = ""


@dataclass
class Workspace(_Record):
    id: str
    name: str
    members: list[dict] = field(default_factory=list)   # {"name", "role": owner/editor/approver/viewer}
    providers: dict = field(default_factory=dict)       # 역할 → 담당 AI id (비어 있으면 기본값)
    budget: dict = field(default_factory=lambda: {"monthly_krw": 100_000, "daily_krw": 7_000,
                                                  "warn_ratio": 0.8})
    notifications: dict = field(default_factory=lambda: {"channel": "telegram", "enabled": False})
    next_project_number: int = 1
    created_at: str = field(default_factory=now)
