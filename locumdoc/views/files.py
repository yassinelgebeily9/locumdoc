import os

from flask import Blueprint, abort, g, send_file

from .. import storage
from ..db import query
from ..security import login_required
from .facility import can_view_doctor, get_facility

bp = Blueprint("files", __name__, url_prefix="/files")


@bp.route("/<int:doc_id>")
@login_required()
def download(doc_id):
    doc = query("SELECT * FROM documents WHERE id = ?", (doc_id,), one=True)
    if not doc:
        abort(404)
    role = g.user["role"]
    allowed = (
        role == "admin"
        or (role == "doctor" and doc["user_id"] == g.user["id"])
        or (role == "facility" and can_view_doctor(get_facility(g.user["id"]), doc["user_id"]))
    )
    if not allowed:
        abort(404)
    path = storage.path_for(doc["storage_name"])
    if not os.path.exists(path):
        abort(404)
    inline = doc["mime_type"] in ("application/pdf", "image/jpeg", "image/png")
    resp = send_file(path, mimetype=doc["mime_type"], as_attachment=not inline,
                     download_name=doc["original_name"], max_age=0)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp
