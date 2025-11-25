# cato_helper/services/cma_graphql_client.py
from __future__ import annotations

from typing import Any, Mapping

import requests


class CmaGraphQLClient:
    """CMA 向け GraphQL クライアントの薄いラッパ。

    - エンドポイント URL
    - 認証済みセッションの Cookie

    を受け取り、GraphQL クエリを実行するだけの小さなクラスです。
    例外処理やエラー整形はここの責務にまとめておきます。
    """

    def __init__(self, endpoint: str, cookies: Mapping[str, str] | None = None) -> None:
        self.endpoint = endpoint
        self.session = requests.Session()
        if cookies:
            self.session.cookies.update(cookies)

    def execute(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": query,
            "variables": variables or {},
        }
        resp = self.session.post(self.endpoint, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # GraphQL の errors フィールドがあれば、例外にして呼び出し元で拾ってもらう
        errors = data.get("errors")
        if errors:
            # 単純に最初のエラーだけまとめる
            msg = errors[0].get("message", "GraphQL error")
            raise RuntimeError(f"GraphQL error: {msg}")

        return data
