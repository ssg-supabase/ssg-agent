"""장르 템플릿 읽기 (설계도 3-1). 기본은 templates/genres/, 작업공간에 같은 이름이 있으면 그걸 우선."""
from __future__ import annotations

import json
from pathlib import Path

BUILTIN = Path(__file__).resolve().parent.parent / "templates" / "genres"


def _dirs(workspace_root: Path | None) -> list[Path]:
    dirs = []
    if workspace_root:
        dirs.append(Path(workspace_root) / "library" / "genres")
    dirs.append(BUILTIN)
    return dirs


def list_genres(workspace_root: Path | None = None) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for d in reversed(_dirs(workspace_root)):   # 기본 먼저 읽고, 작업공간 것으로 덮어씀
        for p in sorted(d.glob("*.json")):
            found[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return found


def load(genre_id: str, workspace_root: Path | None = None) -> dict:
    genres = list_genres(workspace_root)
    if genre_id not in genres:
        raise ValueError(f"모르는 장르입니다: {genre_id} (선택지: {', '.join(genres)})")
    return genres[genre_id]
