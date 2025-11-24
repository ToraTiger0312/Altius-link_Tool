# cato_helper/services/cma_account_map.py
"""CMA の accountName から表示用の顧客名を引くためのマッピング。

必要に応じて このファイルの `ACCOUNT_NAME_MAP` を編集してください。

例:
    ACCOUNT_NAME_MAP = {
        "E221100280": "アルティウスリンク株式会社 検証環境（E221100280）",
        "E999999999": "E999999999（別テナント名）",
    }
"""

from __future__ import annotations

from typing import Dict

# accountName -> 表示用の名前
ACCOUNT_NAME_MAP: Dict[str, str] = {
    # "E221100280": "E221100280（Altius Link 検証環境）",
}


def resolve_account_display_name(account_name: str | None) -> str | None:
    """accountName から表示用の名前を返す。

    マップに無い場合は、そのまま account_name を返す。
    None が来た場合は None を返す。
    """
    if account_name is None:
        return None
    return ACCOUNT_NAME_MAP.get(account_name, account_name)
