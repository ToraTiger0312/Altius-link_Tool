# cato_helper/modules/sample_tool/__init__.py
from flask import Blueprint

bp = Blueprint("sample_tool", __name__)

from . import routes  # noqa: E402,F401
