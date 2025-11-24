# cato_helper/modules/sample_tool/routes.py
from flask import redirect, url_for

from . import bp


@bp.route("/")
def index():
    """暫定的に core.index にリダイレクト。

    あとでここに個別ツールの画面を生やしても OK。
    """
    return redirect(url_for("core.index"))
