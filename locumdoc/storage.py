"""Private file storage for CVs and credentials.

In production files go to a private Firebase Storage (Google Cloud Storage) bucket, set by
FIREBASE_STORAGE_BUCKET. Without one they're kept in UPLOAD_DIR on disk. Either way files
are stored under random names and only served through the authorised /files route.
"""
import json
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

PREFIX = "documents/"  # folder inside the bucket


class UploadError(ValueError):
    pass


class LocalFiles:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def _path(self, name):
        return os.path.join(self.folder, os.path.basename(name))

    def put(self, name, data, mime):
        with open(self._path(name), "wb") as fh:
            fh.write(data)

    def read(self, name):
        try:
            with open(self._path(name), "rb") as fh:
                return fh.read()
        except FileNotFoundError:
            return None

    def delete(self, name):
        try:
            os.remove(self._path(name))
        except FileNotFoundError:
            pass


class BucketFiles:
    """Firebase Storage. The bucket stays private: nothing is ever made public."""

    def __init__(self, bucket, project=None, credentials_info=None):
        self.name, self.project, self.credentials_info = bucket, project, credentials_info
        self._bucket, self._pid = None, None

    @property
    def bucket(self):
        if self._bucket is None or self._pid != os.getpid():  # one connection per gunicorn worker
            from google.cloud import storage as gcs
            from google.oauth2 import service_account

            info = self.credentials_info
            creds = service_account.Credentials.from_service_account_info(info) if info else None
            self._bucket = gcs.Client(project=self.project, credentials=creds).bucket(self.name)
            self._pid = os.getpid()
        return self._bucket

    def put(self, name, data, mime):
        self.bucket.blob(PREFIX + os.path.basename(name)).upload_from_string(data, content_type=mime)

    def read(self, name):
        from google.api_core.exceptions import NotFound

        try:
            return self.bucket.blob(PREFIX + os.path.basename(name)).download_as_bytes()
        except NotFound:
            return None

    def delete(self, name):
        from google.api_core.exceptions import NotFound

        try:
            self.bucket.blob(PREFIX + os.path.basename(name)).delete()
        except NotFound:
            pass


def init_app(app):
    bucket = app.config.get("FIREBASE_STORAGE_BUCKET")
    if bucket and app.config.get("DATA_BACKEND", "firestore") != "local":
        info = app.config.get("FIREBASE_CREDENTIALS_JSON")
        app.extensions["files"] = BucketFiles(bucket, app.config.get("FIREBASE_PROJECT_ID"),
                                              json.loads(info) if info else None)
    else:
        app.extensions["files"] = LocalFiles(app.config["UPLOAD_DIR"])


def _files():
    return current_app.extensions["files"]


def save(file_storage):
    """Validate and store an uploaded PDF. Returns (storage_name, original_name, mime, size)."""
    if not file_storage or not file_storage.filename:
        raise UploadError(_("Choose a file to upload."))
    original = os.path.basename(file_storage.filename)[:200]
    ext = os.path.splitext(original)[1].lower()
    if ext not in ALLOWED:
        raise UploadError(_("Documents must be PDFs. In Word or Pages, choose Export or Save As PDF; for a photo or scan, save it as a PDF first. Then upload that file."))
    data = file_storage.stream.read()
    if not data:
        raise UploadError(_("That file is empty."))
    if not any(data.startswith(sig) for sig in SIGNATURES[ext]):
        raise UploadError(_("That file doesn't look like a valid %(type)s.", type=ext.lstrip(".").upper()))
    name = secrets.token_hex(16) + ext
    _files().put(name, data, ALLOWED[ext])
    return name, original, ALLOWED[ext], len(data)


def write_bytes(data, ext=".pdf"):
    """Store bytes the app generated itself (demo CVs). Returns the storage name."""
    name = secrets.token_hex(16) + ext
    _files().put(name, data, ALLOWED[ext])
    return name


def read(storage_name):
    return _files().read(storage_name)


def delete(storage_name):
    _files().delete(storage_name)
