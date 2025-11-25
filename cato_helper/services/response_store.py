from __future__ import annotations

import atexit
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _get_base_dir() -> Path:
    """
    レスポンスを保存するベースディレクトリを返す。

    - 通常の Python 実行時: プロジェクトルート（このファイルの親の親の親）
        ROOT/
          cato_helper/
            services/
              response_store.py  ← ここ
    - PyInstaller --onefile 実行時:
        実行ファイルと同じディレクトリ
    """
    # PyInstaller などで「凍結」している場合
    if getattr(sys, "frozen", False):
        # 実行ファイルのある場所
        return Path(sys.executable).resolve().parent

    # 通常のスクリプト実行時: プロジェクトルートを推定
    # response_store.py -> services -> cato_helper -> ROOT
    return Path(__file__).resolve().parents[2]


# 例: <プロジェクトルート>/cma_responses
RESPONSE_DIR = _get_base_dir() / "cma_responses"


def _ensure_dir() -> Path:
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
    return RESPONSE_DIR


def save_response(name: str, data: Any) -> Path:
    dir_path = _ensure_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{name}_{ts}.json"
    path = dir_path / filename

    print(f"=== SAVE_RESPONSE CALLED ===")
    print(f"Saving to: {path}")

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def cleanup_response_store() -> None:
    """ツール終了時にレスポンス保存ディレクトリを削除する。"""
    if RESPONSE_DIR.exists():
        print(f"[response_store] cleanup: removing {RESPONSE_DIR}")
        shutil.rmtree(RESPONSE_DIR, ignore_errors=True)


# このモジュールが import された時点で、終了時クリーンアップを登録
atexit.register(cleanup_response_store)
