"""Private file storage for CVs and credentials.

Files live outside the web root (UPLOAD_DIR) under random names and are only
served through an authorised route. Point UPLOAD_DIR at a persistent disk in
production.
"""
import os
import secrets

from flask import current_app

from .i18n import _

# Every document is a PDF: CVs, licences, certificates, passports.
ALLOWED = {
    ".pdf": "application/pdf",
}

# Leading bytes of each allowed type, so a renamed file (Word, image, executable) is rejected.
SIGNATURES = {
    ".pdf": [b"%PDF"],
}


class UploadError(ValueError):
    pass


def save(file_storage):
    """Validate and store an uploaded PDF. Returns (storage_name, original_name, mime, size)."""
    if not file_storage or not file_storage.filename:
        raise UploadError(_("Choose a file to upload."))
    original = os.path.basename(file_storage.filename)[:200]
    ext = os.path.splitext(original)[1].lower()
    if ext not in ALLOWED:
        raise UploadError(_("Documents must be PDFs. In Word or Pages, choose Export or Save As PDF; for a photo or scan, save it as a PDF first. Then upload that file."))
    head = file_storage.stream.read(8)
    file_storage.stream.seek(0)
    if not any(head.startswith(sig) for sig in SIGNATURES[ext]):
        raise UploadError(_("That file doesn't look like a valid %(type)s.", type=ext.lstrip(".").upper()))
    name = secrets.token_hex(16) + ext
    path = os.path.join(current_app.config["UPLOAD_DIR"], name)
    file_storage.save(path)
    size = os.path.getsize(path)
    if size == 0:
        os.remove(path)
        raise UploadError(_("That file is empty."))
    return name, original, ALLOWED[ext], size


def path_for(storage_name):
    return os.path.join(current_app.config["UPLOAD_DIR"], os.path.basename(storage_name))


def delete(storage_name):
    try:
        os.remove(path_for(storage_name))
    except FileNotFoundError:
        pass
