import io

from flask import Blueprint, abort, g, send_file

from .. import storage, store
from ..db import get_facility
from ..security import login_required
from .facility import can_view_doctor

bp = Blueprint("files", __name__, url_prefix="/files")


@bp.route("/<doc_id>")
@login_required()
def download(doc_id):
    doc = store.get("documents", doc_id)
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
    data = storage.read(doc["storage_name"])
    if data is None:
        abort(404)
    inline = doc["mime_type"] in ("application/pdf", "image/jpeg", "image/png")
    resp = send_file(io.BytesIO(data), mimetype=doc["mime_type"], as_attachment=not inline,
                     download_name=doc["original_name"], max_age=0)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp
