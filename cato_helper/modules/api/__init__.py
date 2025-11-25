# cato_helper/modules/api/__init__.py
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("api", __name__)

from . import cma  # noqa: E402,F401
from . import network_static  # noqa: E402,F401
