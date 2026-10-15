import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app import db
from app.models.source_file import SourceFile, ImportJob
from app.models.case import Case
from app.models.audit import AuditLog
from app.services.file_processor import suggest_column_mapping, run_import
import pandas as pd

files_bp = Blueprint("files", __name__)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


@files_bp.route("/cases/<int:case_id>/upload", methods=["POST"])
@jwt_required()
def upload_file(case_id):
    user_id = int(get_jwt_identity())
    case = Case.query.get_or_404(case_id)

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    data_type = request.form.get("data_type", "esf")
    original = secure_filename(file.filename)
    ext = original.rsplit(".", 1)[1].lower()
    stored = f"{uuid.uuid4().hex}.{ext}"
    case_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(case_id))
    os.makedirs(case_dir, exist_ok=True)
    path = os.path.join(case_dir, stored)
    content = file.read()
    with open(path, "wb") as f:
        f.write(content)

    sf = SourceFile(
        case_id=case_id,
        original_filename=original,
        stored_filename=stored,
        file_path=path,
        file_size=len(content),
        mime_type=file.content_type,
        data_type=data_type,
        uploaded_by_id=user_id,
        status="uploaded",
    )
    sf.compute_hash(content)
    db.session.add(sf)
    db.session.flush()

    job = ImportJob(source_file_id=sf.id, case_id=case_id, status="pending")
    db.session.add(job)

    log = AuditLog(
        user_id=user_id,
        case_id=case_id,
        action="file_uploaded",
        entity_type="source_file",
        entity_id=sf.id,
        details={"filename": original, "size": len(content)},
    )
    db.session.add(log)
    db.session.commit()

    # Preview first rows + suggest mapping
    preview = []
    columns = []
    mapping = {}
    try:
        if ext in ("xlsx", "xls"):
            df = pd.read_excel(path, dtype=str, nrows=20)
        else:
            df = pd.read_csv(path, dtype=str, sep=None, engine="python", nrows=20)
        columns = [str(c) for c in df.columns]
        mapping = suggest_column_mapping(columns)
        preview = df.fillna("").to_dict(orient="records")
    except Exception as e:
        preview = [{"error": str(e)}]

    return jsonify({
        "file": sf.to_dict(),
        "import_job_id": job.id,
        "columns": columns,
        "suggested_mapping": mapping,
        "preview": preview,
    }), 201


@files_bp.route("/import-jobs/<int:job_id>/run", methods=["POST"])
@jwt_required()
def run_import_job(job_id):
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    mapping = data.get("column_mapping") or {}
    default_op = data.get("default_operation_type", "purchase")

    try:
        job = run_import(job_id, mapping, default_op)
        log = AuditLog(
            user_id=user_id,
            case_id=job.case_id,
            action="import_completed",
            entity_type="import_job",
            entity_id=job.id,
            details=job.result_summary,
        )
        db.session.add(log)
        db.session.commit()
        return jsonify(job.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@files_bp.route("/cases/<int:case_id>/files", methods=["GET"])
@jwt_required()
def list_files(case_id):
    files = SourceFile.query.filter_by(case_id=case_id).order_by(SourceFile.uploaded_at.desc()).all()
    return jsonify([f.to_dict() for f in files])


@files_bp.route("/cases/<int:case_id>/imports", methods=["GET"])
@jwt_required()
def list_imports(case_id):
    jobs = ImportJob.query.filter_by(case_id=case_id).order_by(ImportJob.created_at.desc()).all()
    return jsonify([j.to_dict() for j in jobs])


@files_bp.route("/files/<int:file_id>", methods=["DELETE"])
@jwt_required()
def delete_file(file_id):
    """Delete uploaded source file and its import jobs."""
    import os
    from app.models.audit import AuditLog

    user_id = int(get_jwt_identity())
    sf = SourceFile.query.get_or_404(file_id)
    case_id = sf.case_id
    path = sf.file_path
    name = getattr(sf, "original_name", None) or getattr(sf, "filename", None)
    ImportJob.query.filter_by(source_file_id=file_id).delete()
    db.session.delete(sf)
    db.session.add(AuditLog(
        user_id=user_id,
        case_id=case_id,
        action="file_deleted",
        entity_type="source_file",
        entity_id=file_id,
        details={"name": name},
    ))
    db.session.commit()
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
    return jsonify({"ok": True})
