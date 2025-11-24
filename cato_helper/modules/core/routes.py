# cato_helper/modules/core/routes.py
from . import bp
from flask import render_template, jsonify

import threading
from ...services.cma_session import login_via_playwright, has_cma_state, get_cma_status


@bp.route("/")
def index():
    """最初に表示される「業務支援ツール」トップページ。"""
    return render_template("core/index.html")



@bp.route("/cma/login", methods=["POST"])
def cma_login():
    """CMA ログインを Playwright で開始するエンドポイント。"""
    if has_cma_state():
        return jsonify({"status": "already_logged_in"})

    def worker():
        try:
            login_via_playwright()
        except Exception as e:  # noqa: BLE001
            print(f"[CMA LOGIN] エラー: {e}")

    threading.Thread(target=worker, daemon=True).start()

    return jsonify({"status": "started"})


@bp.route("/cma/status", methods=["GET"])
def cma_status():
    """CMA ログイン状態とアカウント名を返すエンドポイント。"""
    status = get_cma_status()
    return jsonify(status)
