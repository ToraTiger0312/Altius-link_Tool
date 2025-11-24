# cato_helper/modules/core/__init__.py
from flask import Blueprint

bp = Blueprint("core", __name__)

from . import routes  # type: ignore[reportUnusedImport]
