# cato_helper/services/cato_client.py
from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class CatoClient:
    """Cato API を叩くための薄いラッパークラス。

    実際のエンドポイントやレスポンス形式は公式ドキュメントに合わせて
    get/post などのメソッドを追加していく想定。
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.api_key}",
            "Content-Type": "application/json",
        }

    def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Any:
        """GET リクエスト用の共通メソッド。"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = self._session.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=timeout or self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # 将来的に:
    # def post(...), def put(...), def delete(...)
    # みたいなメソッドを追加していく
