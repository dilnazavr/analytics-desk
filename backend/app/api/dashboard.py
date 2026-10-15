from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.case import Case, CaseMember
from app.models.source_file import SourceFile
from app.models.audit import AuditLog
from sqlalchemy import or_, func

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    user_id = int(get_jwt_identity())

    base = Case.query.outerjoin(CaseMember).filter(
        or_(
            Case.responsible_id == user_id,
            Case.created_by_id == user_id,
            CaseMember.user_id == user_id,
        )
    ).distinct()

    open_count = base.filter(Case.status.in_(["open", "in_progress"])).count()
    review_count = base.filter(Case.status == "review").count()
    report_count = base.filter(Case.status == "report_ready").count()

    files_count = (
        db.session.query(func.count(SourceFile.id))
        .join(Case)
        .outerjoin(CaseMember)
        .filter(
            or_(
                Case.responsible_id == user_id,
                Case.created_by_id == user_id,
                CaseMember.user_id == user_id,
            )
        )
        .scalar()
    )

    recent_cases = base.order_by(Case.updated_at.desc()).limit(5).all()
    recent_logs = (
        AuditLog.query.filter(
            or_(
                AuditLog.user_id == user_id,
                AuditLog.case_id.in_([c.id for c in recent_cases]),
            )
        )
        .order_by(AuditLog.created_at.desc())
        .limit(10)
        .all()
    )

    return jsonify({
        "open_cases": open_count,
        "review_cases": review_count,
        "report_ready": report_count,
        "files_processed": files_count or 0,
        "recent_cases": [c.to_dict() for c in recent_cases],
        "recent_actions": [l.to_dict() for l in recent_logs],
    })
