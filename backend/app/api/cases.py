from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.case import Case, CaseMember
from app.models.user import User
from app.models.audit import AuditLog
from datetime import datetime, date
from sqlalchemy import or_

cases_bp = Blueprint("cases", __name__)


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


@cases_bp.route("", methods=["GET"])
@jwt_required()
def list_cases():
    user_id = int(get_jwt_identity())
    q = request.args.get("q", "").strip()
    status = request.args.get("status")
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)

    # Access: cases where user is member or responsible or creator
    query = Case.query.outerjoin(CaseMember).filter(
        or_(
            Case.responsible_id == user_id,
            Case.created_by_id == user_id,
            CaseMember.user_id == user_id,
        )
    ).distinct()

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Case.number.ilike(like),
                Case.title.ilike(like),
                Case.organization_name.ilike(like),
                Case.bin.ilike(like),
            )
        )
    if status:
        query = query.filter(Case.status == status)

    query = query.order_by(Case.updated_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [c.to_dict() for c in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@cases_bp.route("", methods=["POST"])
@jwt_required()
def create_case():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    # Generate number
    year = datetime.utcnow().year
    last = Case.query.filter(Case.number.like(f"AD-{year}-%")).order_by(Case.id.desc()).first()
    seq = 1
    if last:
        try:
            seq = int(last.number.split("-")[-1]) + 1
        except Exception:
            pass
    number = f"AD-{year}-{seq:04d}"

    case = Case(
        number=number,
        title=title,
        organization_name=data.get("organization_name"),
        bin=data.get("bin"),
        basis=data.get("basis"),
        basis_date=_parse_date(data.get("basis_date")),
        requesting_body=data.get("requesting_body"),
        subject=data.get("subject"),
        period_start=_parse_date(data.get("period_start")),
        period_end=_parse_date(data.get("period_end")),
        responsible_id=data.get("responsible_id") or user_id,
        status="open",
        comment=data.get("comment"),
        created_by_id=user_id,
    )
    db.session.add(case)
    db.session.flush()

    # Add creator as member
    member = CaseMember(case_id=case.id, user_id=user_id, role_in_case="analyst")
    db.session.add(member)

    log = AuditLog(
        user_id=user_id,
        case_id=case.id,
        action="case_created",
        entity_type="case",
        entity_id=case.id,
        details={"number": number, "title": title},
    )
    db.session.add(log)
    db.session.commit()
    return jsonify(case.to_dict(include_details=True)), 201


@cases_bp.route("/<int:case_id>", methods=["GET"])
@jwt_required()
def get_case(case_id):
    case = Case.query.get_or_404(case_id)
    return jsonify(case.to_dict(include_details=True))


@cases_bp.route("/<int:case_id>", methods=["PATCH"])
@jwt_required()
def update_case(case_id):
    user_id = int(get_jwt_identity())
    case = Case.query.get_or_404(case_id)
    data = request.get_json() or {}

    for field in ["title", "organization_name", "bin", "basis", "requesting_body", "subject", "comment", "status"]:
        if field in data:
            setattr(case, field, data[field])
    if "basis_date" in data:
        case.basis_date = _parse_date(data["basis_date"])
    if "period_start" in data:
        case.period_start = _parse_date(data["period_start"])
    if "period_end" in data:
        case.period_end = _parse_date(data["period_end"])
    if "responsible_id" in data:
        case.responsible_id = data["responsible_id"]

    case.updated_at = datetime.utcnow()
    log = AuditLog(
        user_id=user_id,
        case_id=case.id,
        action="case_updated",
        entity_type="case",
        entity_id=case.id,
        details=data,
    )
    db.session.add(log)
    db.session.commit()
    return jsonify(case.to_dict(include_details=True))


@cases_bp.route("/<int:case_id>", methods=["DELETE"])
@jwt_required()
def delete_case(case_id):
    """Delete case and related data (cascade where configured)."""
    from app.models.invoice import Invoice, InvoiceLine
    from app.models.source_file import SourceFile, ImportJob
    from app.models.match import ProductMatch
    from app.models.flag import AnalyticalFlag
    from app.models.procurement import ProcurementContract
    from app.models.relation import EntityRelation
    from app.models.report import ReportVersion
    from app.models.counterparty import Counterparty

    user_id = int(get_jwt_identity())
    case = Case.query.get_or_404(case_id)
    user = User.query.get(user_id)
    role_name = (user.role.name if user and user.role else "") or ""
    # Allow creator, responsible, or admin
    if role_name not in ("admin",) and case.created_by_id != user_id and case.responsible_id != user_id:
        return jsonify({"error": "Недостаточно прав для удаления дела"}), 403

    case_number = case.number
    # Manual cascade for safety
    ProductMatch.query.filter_by(case_id=case_id).delete()
    AnalyticalFlag.query.filter_by(case_id=case_id).delete()
    InvoiceLine.query.filter_by(case_id=case_id).delete()
    Invoice.query.filter_by(case_id=case_id).delete()
    ImportJob.query.filter_by(case_id=case_id).delete()
    SourceFile.query.filter_by(case_id=case_id).delete()
    ProcurementContract.query.filter_by(case_id=case_id).delete()
    EntityRelation.query.filter_by(case_id=case_id).delete()
    ReportVersion.query.filter_by(case_id=case_id).delete()
    Counterparty.query.filter_by(case_id=case_id).delete()
    CaseMember.query.filter_by(case_id=case_id).delete()
    AuditLog.query.filter_by(case_id=case_id).delete()

    db.session.delete(case)
    db.session.add(AuditLog(
        user_id=user_id,
        action="case_deleted",
        entity_type="case",
        entity_id=case_id,
        details={"number": case_number},
    ))
    db.session.commit()
    return jsonify({"ok": True, "deleted_id": case_id})
