# cato_helper/services/response_store.py
from __future__ import annotations

import atexit
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

# 例: /tmp/cato_helper_responses みたいな場所になる
RESPONSE_DIR = Path(tempfile.gettempdir()) / "cato_helper_responses"


def _ensure_dir() -> Path:
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
    return RESPONSE_DIR


def save_response(name: str, data: Any) -> Path:
    """API / GraphQL のレスポンスを JSON で保存する。

    name: "login_state" などの論理名
    data: dict や list など JSON に変換できるオブジェクト
    """
    dir_path = _ensure_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{name}_{ts}.json"
    path = dir_path / filename

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def cleanup_response_store() -> None:
    """ツール終了時にレスポンス保存ディレクトリを削除する。"""
    if RESPONSE_DIR.exists():
        shutil.rmtree(RESPONSE_DIR, ignore_errors=True)


# このモジュールが import された時点で、終了時クリーンアップを登録
atexit.register(cleanup_response_store)
