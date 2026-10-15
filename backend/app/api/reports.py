from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.report import ReportVersion
from app.services.report_generator import generate_draft_report
from app.models.audit import AuditLog
import os

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/cases/<int:case_id>/reports", methods=["GET"])
@jwt_required()
def list_reports(case_id):
    reports = ReportVersion.query.filter_by(case_id=case_id).order_by(ReportVersion.version.desc()).all()
    return jsonify([r.to_dict() for r in reports])


@reports_bp.route("/cases/<int:case_id>/reports", methods=["POST"])
@jwt_required()
def create_report(case_id):
    user_id = int(get_jwt_identity())
    rv = generate_draft_report(case_id, user_id)
    log = AuditLog(
        user_id=user_id,
        case_id=case_id,
        action="report_generated",
        entity_type="report",
        entity_id=rv.id,
        details={"version": rv.version},
    )
    db.session.add(log)
    db.session.commit()
    return jsonify(rv.to_dict()), 201


@reports_bp.route("/<int:report_id>/download", methods=["GET"])
@jwt_required()
def download_report(report_id):
    rv = ReportVersion.query.get_or_404(report_id)
    if not rv.file_path or not os.path.exists(rv.file_path):
        return jsonify({"error": "File not found"}), 404
    return send_file(
        rv.file_path,
        as_attachment=True,
        download_name=os.path.basename(rv.file_path),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
