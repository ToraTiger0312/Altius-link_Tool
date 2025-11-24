# cato_helper/modules/network/__init__.py
from flask import Blueprint

bp = Blueprint("network", __name__)

from . import routes  # type: ignore[reportUnusedImport]
