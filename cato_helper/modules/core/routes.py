# cato_helper/modules/core/routes.py
from . import bp
from flask import render_template, jsonify, request

import threading
from ...services.cma_session import (
    get_cma_status,
    has_cma_state,
    load_login_profiles,
    login_via_playwright,
    resolve_login_profile,
    cleanup_cma_state,
)

from ...services.response_store import cleanup_response_store

@bp.route("/")
def index():
    """最初に表示される「業務支援ツール」トップページ。"""
    return render_template("core/index.html")



@bp.route("/cma/login", methods=["POST"])
def cma_login():
    """CMA ログインを Playwright で開始するエンドポイント。"""
    if has_cma_state():
        return jsonify({"status": "already_logged_in"})

    body = request.get_json(silent=True) or {} # type: ignore[reportUnknownMemberType]
    profile_name = body.get("profile") or body.get("profile_name") # type: ignore[reportUnknownMemberType]

    try:
        resolve_login_profile(profile_name) # type: ignore[reportUnknownMemberType]
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    def worker():
        try:
            login_via_playwright(profile_name) # type: ignore[reportUnknownMemberType]
        except Exception as e:  # noqa: BLE001
            print(f"[CMA LOGIN] エラー: {e}")

    threading.Thread(target=worker, daemon=True).start()

    return jsonify({"status": "started"})


@bp.route("/cma/status", methods=["GET"])
def cma_status():
    """CMA ログイン状態とアカウント名を返すエンドポイント。"""
    status = get_cma_status()
    return jsonify(status)


@bp.route("/cma/logout", methods=["POST"])
def cma_logout():
    """CMA からログアウトし、セッション情報と保存済みレスポンスを削除する。"""
    # Playwright の state ファイルを削除
    cleanup_cma_state()
    # loginState など GraphQL のレスポンス保存ディレクトリを削除
    cleanup_response_store()
    return jsonify({"status": "ok"})

@bp.route("/cma/profiles", methods=["GET"])
def cma_profiles():
    """利用可能な CMA ログインプロファイル一覧を返す。"""
    try:
        profiles = load_login_profiles()
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "ok", "profiles": [{"name": name} for name in profiles.keys()]})
