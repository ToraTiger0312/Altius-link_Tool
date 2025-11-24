# cato_helper/__init__.py
from __future__ import annotations

from flask import Flask, jsonify, request   # ← ここを修正（jsonify, requestを追加）

from .config import Config


def create_app(config_class: type[Config] = Config) -> Flask:
    """Flask アプリ本体を生成するファクトリ関数。"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Blueprint 登録 ---
    from .modules.core import bp as core_bp
    app.register_blueprint(core_bp)  # "/" を担当

    # Network 関連ツール（Site への Network/Static Route 追加など）
    from .modules.network import bp as network_bp
    app.register_blueprint(network_bp, url_prefix="/network")

    # 将来的にツールを増やしたらここに追加
    from .modules.sample_tool import bp as sample_tool_bp
    app.register_blueprint(sample_tool_bp, url_prefix="/sample")

    # アプリ終了時に CMA セッションなどの一時ファイルを削除
    from .services.cma_session import cleanup_cma_state
    from .services.response_store import cleanup_response_store
    import atexit
    atexit.register(cleanup_cma_state)
    atexit.register(cleanup_response_store)

    # ==== 終了用エンドポイント ====
    @app.route("/shutdown", methods=["POST"])
    def shutdown():
        cleanup_cma_state()
        cleanup_response_store()
        func = request.environ.get("werkzeug.server.shutdown")
        if func is None:
            # Werkzeug以外の場合は強制終了
            import os
            os._exit(0)
        func()
        return jsonify({"status": "ok"})

    return app
