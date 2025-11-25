# cato_helper/__init__.py
from __future__ import annotations

from flask import Flask, jsonify, request

from .config import Config


def create_app(config_class: type[Config] = Config) -> Flask:
    """Flask アプリ本体を生成するファクトリ関数。"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Blueprint 登録 ---
    from .modules.core import bp as core_bp
    from .modules.network import bp as network_bp
    from .modules.sample_tool import bp as sample_tool_bp
    from .modules.api import bp as api_bp

    # 画面系
    app.register_blueprint(core_bp)                # "/" を担当
    app.register_blueprint(network_bp, url_prefix="/network")
    app.register_blueprint(sample_tool_bp, url_prefix="/sample")
    # API 系（/api/* 配下）
    app.register_blueprint(api_bp, url_prefix="/api")

    # --- 終了処理関連 ---
    from .services.cma_session import cleanup_cma_state
    from .services.response_store import cleanup_response_store

    @app.route("/shutdown", methods=["POST"])
    def shutdown() -> tuple[dict, int] | dict:
        """アプリ終了用のエンドポイント。

        PyInstaller 化した実行ファイルから終了させる用途などを想定。
        """
        cleanup_cma_state()
        cleanup_response_store()

        func = request.environ.get("werkzeug.server.shutdown")
        if func is None:
            # Werkzeug 以外の場合はプロセスを直接落とす
            import os
            os._exit(0)
        func()
        return jsonify({"status": "ok"})

    return app
