"""기록 저장소: workspace/ 폴더에 JSON으로 저장 (설계도 6장).

나중에 Supabase로 옮길 때는 이 파일만 바꾸면 됩니다. 다른 코드는 이 Store의 함수만 씁니다.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

from core.models import (
    ASPECT_SIZES, STEP_KEYS, UPLOAD_PURPOSES, Channel, Project, Spec, Step, StepStatus,
    Upload, Workspace, now,
)

DEFAULT_ROOT = Path("workspace")
_BAD_CHARS = re.compile(r'[\\/:*?"<>|\s]+')


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(10):   # 쓰는 도중 꺼져도 원래 파일이 깨지지 않게 바꿔치기
        try:
            tmp.replace(path)
            return
        except PermissionError:   # 윈도우: 백신·검색 색인이 잠깐 파일을 잡고 있을 때
            if attempt == 9:
                raise
            time.sleep(0.05 * (attempt + 1))


def _folder_name(title: str, limit: int = 30) -> str:
    return _BAD_CHARS.sub("", title)[:limit] or "untitled"


class Store:
    def __init__(self, root: Path | str = DEFAULT_ROOT, user: str = "me"):
        self.root = Path(root)
        self.user = user   # 나중에 로그인이 생기면 실제 사용자 이름

    # ── 작업공간 ──────────────────────────────────────────
    @property
    def workspace_file(self) -> Path:
        return self.root / "workspace.json"

    def exists(self) -> bool:
        return self.workspace_file.exists()

    def init_workspace(self, name: str) -> Workspace:
        if self.exists():
            raise FileExistsError(f"이미 작업공간이 있습니다: {self.workspace_file}")
        ws = Workspace(id="ws1", name=name, members=[{"name": self.user, "role": "owner"}])
        for sub in ("sfx", "bgm", "prompts", "genres"):
            (self.root / "library" / sub).mkdir(parents=True, exist_ok=True)
        self.save_workspace(ws)
        return ws

    def load_workspace(self) -> Workspace:
        if not self.exists():
            raise FileNotFoundError("작업공간이 없습니다. 먼저 `python ssg.py init` 을 실행하세요.")
        return Workspace.from_dict(_read(self.workspace_file))

    def save_workspace(self, ws: Workspace) -> None:
        _write(self.workspace_file, ws.to_dict())

    # ── 채널 ─────────────────────────────────────────────
    def channel_dir(self, channel_id: str) -> Path:
        return self.root / "channels" / channel_id

    def add_channel(self, channel_id: str, name: str, genres: list[str]) -> Channel:
        if not re.fullmatch(r"[a-z0-9_-]+", channel_id):
            raise ValueError("채널 id는 영어 소문자·숫자·-·_ 만 쓸 수 있습니다 (예: book)")
        if (self.channel_dir(channel_id) / "channel.json").exists():
            raise FileExistsError(f"이미 있는 채널입니다: {channel_id}")
        ws = self.load_workspace()
        ch = Channel(id=channel_id, workspace_id=ws.id, name=name, genres=genres, created_by=self.user)
        if genres:
            ch.defaults["spec"]["genre"] = genres[0]
        for sub in ("characters", "styles", "voices", "brand"):
            (self.channel_dir(channel_id) / "library" / sub).mkdir(parents=True, exist_ok=True)
        (self.channel_dir(channel_id) / "projects").mkdir(parents=True, exist_ok=True)
        self.save_channel(ch)
        return ch

    def load_channel(self, channel_id: str) -> Channel:
        path = self.channel_dir(channel_id) / "channel.json"
        if not path.exists():
            raise FileNotFoundError(f"채널이 없습니다: {channel_id}")
        return Channel.from_dict(_read(path))

    def save_channel(self, ch: Channel) -> None:
        _write(self.channel_dir(ch.id) / "channel.json", ch.to_dict())

    def list_channels(self) -> list[Channel]:
        base = self.root / "channels"
        if not base.exists():
            return []
        return [Channel.from_dict(_read(p)) for p in sorted(base.glob("*/channel.json"))]

    # ── 프로젝트 ──────────────────────────────────────────
    def new_project(self, channel_id: str, topic: str, title: str = "", **spec_overrides) -> Project:
        ws = self.load_workspace()
        ch = self.load_channel(channel_id)
        spec = Spec.from_dict({**ch.defaults["spec"], **{k: v for k, v in spec_overrides.items() if v is not None}})
        if spec.aspect in ASPECT_SIZES:
            spec.width, spec.height = ASPECT_SIZES[spec.aspect]

        pid = f"p{ws.next_project_number:04d}"
        ws.next_project_number += 1
        title = title or topic
        folder = f"{datetime.now():%Y%m%d}_{pid}_{_folder_name(title)}"
        project = Project(
            id=pid, workspace_id=ws.id, channel_id=ch.id, title=title, topic=topic, folder=folder,
            spec=spec.to_dict(), automation_level=ch.defaults.get("automation_level", 1),
            created_by=self.user, updated_by=self.user,
        )
        pdir = self.project_dir(project)
        for sub in ("uploads", "refs", "cast", "scenes", "audio", "renders", "publish"):
            (pdir / sub).mkdir(parents=True, exist_ok=True)
        self.save_workspace(ws)   # 번호를 먼저 확정해서 같은 번호가 두 번 나오지 않게
        self.save_project(project)
        return project

    def project_dir(self, project: Project) -> Path:
        return self.channel_dir(project.channel_id) / "projects" / project.folder

    def save_project(self, project: Project) -> None:
        project.updated_at = now()
        project.updated_by = self.user
        _write(self.project_dir(project) / "project.json", project.to_dict())

    def list_projects(self, channel_id: str | None = None) -> list[Project]:
        pattern = f"channels/{channel_id or '*'}/projects/*/project.json"
        return [Project.from_dict(_read(p)) for p in sorted(self.root.glob(pattern))]

    def load_project(self, project_id: str) -> Project:
        for p in self.root.glob(f"channels/*/projects/*_{project_id}_*/project.json"):
            return Project.from_dict(_read(p))
        raise FileNotFoundError(f"프로젝트가 없습니다: {project_id}")

    # ── 단계 ─────────────────────────────────────────────
    def update_step(self, project: Project, key: str, status: str | StepStatus, **fields) -> Step:
        if key not in STEP_KEYS:
            raise ValueError(f"모르는 단계입니다: {key}")
        status = StepStatus(status).value
        step = Step.from_dict(project.steps[key])
        if status == StepStatus.RUNNING.value:
            step.started_at, step.error = now(), ""
            step.attempts += 1
        if status in (StepStatus.DONE.value, StepStatus.FAILED.value, StepStatus.AWAITING_APPROVAL.value):
            step.finished_at = now()
        step.status = status
        for k, v in fields.items():
            setattr(step, k, v)
        step.updated_by = self.user
        project.steps[key] = step.to_dict()
        project.cost_total_usd = round(sum(s.get("cost_usd", 0) for s in project.steps.values()), 4)
        self.save_project(project)
        return step

    def finish_step(self, project: Project, key: str, **fields) -> Step:
        """단계를 끝낼 때: 승인이 필요한 단계면 '승인 대기', 아니면 '완료'."""
        needs = project.steps[key].get("needs_approval")
        return self.update_step(project, key,
                                StepStatus.AWAITING_APPROVAL if needs else StepStatus.DONE, **fields)

    # ── 업로드 ────────────────────────────────────────────
    def add_upload(self, project: Project, source: str, purpose: str,
                   rights_confirmed: bool = False, note: str = "") -> Upload:
        if purpose not in UPLOAD_PURPOSES:
            raise ValueError(f"용도는 다음 중 하나여야 합니다: {', '.join(UPLOAD_PURPOSES)}")
        uid = f"u{len(project.uploads) + 1:03d}"
        if source.startswith("http"):   # 링크는 복사하지 않고 그대로 기록
            up = Upload(id=uid, purpose=purpose, filename=source, path=source,
                        rights_confirmed=rights_confirmed, note=note, added_by=self.user)
        else:
            src = Path(source)
            if not src.is_file():
                raise FileNotFoundError(f"파일이 없습니다: {source}")
            rel = Path("uploads") / f"{uid}_{src.name}"
            shutil.copy2(src, self.project_dir(project) / rel)
            up = Upload(id=uid, purpose=purpose, filename=src.name, path=rel.as_posix(),
                        rights_confirmed=rights_confirmed, note=note, added_by=self.user)
        project.uploads.append(up.to_dict())
        if purpose == "ref_video":
            project.references.append({"upload_id": uid, "source": up.path, "style_card": None})
        self.save_project(project)
        return up
