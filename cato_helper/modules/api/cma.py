# cato_helper/modules/api/cma.py
from __future__ import annotations

from flask import jsonify, request

from . import bp
from ...services.cma_session import (
    has_cma_state,
    _build_requests_session_from_state,  # 内部ヘルパーだが、ここでは割り切って利用する
    CMA_GRAPHQL_URL,
)
from ...services.cma_queries import LOGIN_STATE_QUERY
from ...services.response_store import save_response


@bp.route("/cma/query", methods=["POST"])
def execute_cma_query():
    """CMA 向け GraphQL クエリを実行する汎用エンドポイント。

    ひとまず PoC として loginState 専用に近い形ですが、
    後続でクエリ名を指定して切り替えられるように拡張しやすい構造にしてあります。

    リクエストボディ例:
    {
        "name": "loginState",
        "variables": { ... }  # 省略可
    }
    """

    if not has_cma_state():
        return jsonify({"status": "error", "message": "CMA にログインしていません。"}), 401

    body = request.get_json(force=True, silent=True) or {}
    query_name = body.get("name") or "loginState"
    variables = body.get("variables") or {}

    # まずは loginState のみサポート
    if query_name != "loginState":
        return jsonify({"status": "error", "message": f"unsupported query: {query_name}"}), 400

    sess = _build_requests_session_from_state()

    payload = {
        "operationName": "loginState",
        "variables": variables or {"authcode": None, "authstate": None},
        "query": LOGIN_STATE_QUERY,
    }

    try:
        resp = sess.post(CMA_GRAPHQL_URL, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:  # noqa: BLE001
        return jsonify({"status": "error", "message": str(e)}), 500

    # デバッグ / 解析用にレスポンスを保存
    save_response(query_name, result)

    return jsonify({"status": "ok", "data": result})
