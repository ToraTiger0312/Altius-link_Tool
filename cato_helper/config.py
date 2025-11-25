# cato_helper/config.py
import os


class Config:
    """アプリ全体の設定。

    Cato API / CMA などの URL やキーを環境変数から読み込む。
    """

    # --- Cato REST API 関連 ---
    CATO_BASE_URL: str = os.environ.get(
        "CATO_BASE_URL", "https://api.catonetworks.com"
    )
    CATO_API_KEY: str = os.environ.get("CATO_API_KEY", "CHANGE_ME")

    # --- CMA / GraphQL 関連 ---
    # CMA の GraphQL エンドポイント。環境に応じて上書きできるようにしておく。
    CMA_GRAPHQL_ENDPOINT: str = os.environ.get(
        "CMA_GRAPHQL_ENDPOINT",
        # デフォルト値は将来調整しやすいように一応プレースホルダにしておく
        "https://cc.catonetworks.com/api/gql",
    )
