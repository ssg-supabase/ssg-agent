"""사용자·로그인·접근 권한 (설계도 10-3).

- 비밀번호는 원문을 저장하지 않고 scrypt 해시(+사용자마다 다른 소금값)만 저장합니다.
- 저장 위치: workspace/users.json (workspace/ 는 .gitignore 라 GitHub에 안 올라감)
- 첫 전체 관리자는 .env 의 ADMIN_EMAIL · ADMIN_PASSWORD 로 만듭니다 (코드에 비밀번호를 적지 않음).

권한 판단 순서: 정지 → 차단 / 전체 관리자 → 모두 허용 / 프로젝트 예외(on·off) → 채널 on·off
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path

from core.models import now
from core.store import _write

ROLES = {"admin": "전체 관리자", "manager": "채널 관리자", "editor": "편집자", "viewer": "보기 전용"}
STATUSES = {"active": "활성", "suspended": "정지"}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PW = 8


def hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def check_password(pw: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(pw, bytes.fromhex(salt_hex)), stored)


def _check_pw_rule(pw: str) -> None:
    if len(pw) < MIN_PW:
        raise ValueError(f"비밀번호는 {MIN_PW}자 이상이어야 합니다.")


class Users:
    def __init__(self, root: Path | str = "workspace"):
        self.file = Path(root) / "users.json"

    # ── 읽기·쓰기 ──
    def all(self) -> list[dict]:
        if not self.file.exists():
            return []
        return json.loads(self.file.read_text(encoding="utf-8"))

    def _save(self, users: list[dict]) -> None:
        _write(self.file, users)

    def _find(self, users: list[dict], uid: str) -> dict:
        for u in users:
            if u["id"].lower() == uid.strip().lower():
                return u
        raise FileNotFoundError(f"사용자가 없습니다: {uid}")

    def get(self, uid: str) -> dict:
        return self._find(self.all(), uid)

    # ── 만들기 ──
    def add(self, uid: str, password: str, role: str = "editor", name: str = "",
            channels: list[str] | None = None, must_change: bool = True) -> dict:
        if not _EMAIL.match(uid):
            raise ValueError("아이디는 이메일 형식이어야 합니다.")
        if role not in ROLES:
            raise ValueError(f"역할은 다음 중 하나: {', '.join(ROLES)}")
        _check_pw_rule(password)
        users = self.all()
        if any(u["id"].lower() == uid.lower() for u in users):
            raise FileExistsError(f"이미 있는 아이디입니다: {uid}")
        user = {"id": uid, "name": name or uid.split("@")[0], "pw": hash_password(password), "role": role,
                "status": "active", "channels": {c: True for c in channels or []}, "projects": {},
                "must_change": must_change, "reset_requested": False, "created_at": now(), "last_login": ""}
        users.append(user)
        self._save(users)
        return user

    def seed_admin_from_env(self) -> dict | None:
        """사용자가 아무도 없을 때만 .env 의 ADMIN_EMAIL · ADMIN_PASSWORD 로 전체 관리자를 만듭니다."""
        if self.all():
            return None
        email, pw = os.getenv("ADMIN_EMAIL", "").strip(), os.getenv("ADMIN_PASSWORD", "")
        if not email or not pw:
            return None
        return self.add(email, pw, role="admin", must_change=False)

    # ── 로그인·비밀번호 ──
    def login(self, uid: str, password: str) -> dict:
        users = self.all()
        try:
            u = self._find(users, uid)
        except FileNotFoundError:
            u = None
        if u is None or not check_password(password, u["pw"]):
            raise ValueError("아이디 또는 비밀번호가 맞지 않습니다.")   # 어느 쪽이 틀렸는지 알려주지 않음
        if u["status"] != "active":
            raise ValueError("정지된 계정입니다. 관리자에게 문의하세요.")
        u["last_login"] = now()
        self._save(users)
        return u

    def change_password(self, uid: str, current: str, new: str) -> None:
        users = self.all()
        u = self._find(users, uid)
        if not check_password(current, u["pw"]):
            raise ValueError("현재 비밀번호가 맞지 않습니다.")
        _check_pw_rule(new)
        u.update(pw=hash_password(new), must_change=False, reset_requested=False)
        self._save(users)

    def request_reset(self, uid: str) -> None:
        users = self.all()
        try:
            self._find(users, uid)["reset_requested"] = True
            self._save(users)
        except FileNotFoundError:
            pass   # 계정이 있는지 없는지 밖으로 알리지 않음

    def issue_temp_password(self, uid: str) -> str:
        users = self.all()
        u = self._find(users, uid)
        temp = "tmp-" + secrets.token_urlsafe(6)
        u.update(pw=hash_password(temp), must_change=True, reset_requested=False)
        self._save(users)
        return temp

    # ── 관리 ──
    def update(self, uid: str, **fields) -> dict:
        users = self.all()
        u = self._find(users, uid)
        if "role" in fields and fields["role"] not in ROLES:
            raise ValueError(f"역할은 다음 중 하나: {', '.join(ROLES)}")
        if "status" in fields and fields["status"] not in STATUSES:
            raise ValueError("상태는 active 또는 suspended")
        demoting = u["role"] == "admin" and (fields.get("role", "admin") != "admin" or fields.get("status") == "suspended")
        if demoting and sum(x["role"] == "admin" and x["status"] == "active" for x in users) == 1:
            raise ValueError("마지막 전체 관리자는 역할을 바꾸거나 정지할 수 없습니다.")
        u.update({k: v for k, v in fields.items() if k in ("name", "role", "status")})
        self._save(users)
        return u

    def set_channel(self, uid: str, channel_id: str, on: bool) -> None:
        users = self.all()
        self._find(users, uid)["channels"][channel_id] = on
        self._save(users)

    def set_project(self, uid: str, project_id: str, mode: str) -> None:
        """mode: on(허용) / off(차단) / inherit(채널 설정 따름)"""
        if mode not in ("on", "off", "inherit"):
            raise ValueError("on / off / inherit 중 하나")
        users = self.all()
        projects = self._find(users, uid)["projects"]
        if mode == "inherit":
            projects.pop(project_id, None)
        else:
            projects[project_id] = mode
        self._save(users)

    def delete(self, uid: str) -> None:
        users = self.all()
        u = self._find(users, uid)
        if u["role"] == "admin" and sum(x["role"] == "admin" for x in users) == 1:
            raise ValueError("마지막 전체 관리자는 삭제할 수 없습니다.")
        users.remove(u)
        self._save(users)


def can_access(user: dict, channel_id: str, project_id: str | None = None) -> bool:
    if user["status"] != "active":
        return False
    if user["role"] == "admin":
        return True
    if project_id and project_id in user.get("projects", {}):
        return user["projects"][project_id] == "on"
    return bool(user.get("channels", {}).get(channel_id))


def can_manage_settings(user: dict) -> bool:
    return user["status"] == "active" and user["role"] == "admin"
