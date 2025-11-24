# cato_helper/modules/network/routes.py
from flask import render_template

from . import bp


@bp.route("/static-route")
def static_route_add():
    """Site に Static Route を追加するツール（画面ひな型のみ）。"""
    return render_template("network/static_route.html")
