# cato_helper/config.py
import os


class Config:
    """アプリ全体の設定。

    Cato API の URL や API キーなどを環境変数から読み込む。
    """

    CATO_BASE_URL: str = os.environ.get(
        "CATO_BASE_URL", "https://api.catonetworks.com"
    )
    CATO_API_KEY: str = os.environ.get("CATO_API_KEY", "CHANGE_ME")
