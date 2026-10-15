from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.match import ProductMatch
from app.models.flag import AnalyticalFlag
from app.services.matching import find_matches_for_case, confirm_match, reject_match
from app.models.audit import AuditLog

matches_bp = Blueprint("matches", __name__)


@matches_bp.route("/cases/<int:case_id>/matches", methods=["GET"])
@jwt_required()
def list_matches(case_id):
    status = request.args.get("status")
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)

    q = ProductMatch.query.filter_by(case_id=case_id)
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(ProductMatch.similarity_score.desc().nullslast())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [m.to_dict() for m in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
    })


@matches_bp.route("/cases/<int:case_id>/matches/run", methods=["POST"])
@jwt_required()
def run_matching(case_id):
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    threshold = float(data.get("fuzzy_threshold", 85))
    matches = find_matches_for_case(case_id, threshold)
    log = AuditLog(
        user_id=user_id,
        case_id=case_id,
        action="matching_run",
        entity_type="case",
        entity_id=case_id,
        details={"new_matches": len(matches)},
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"created": len(matches), "matches": [m.to_dict() for m in matches[:50]]})


@matches_bp.route("/<int:match_id>", methods=["PATCH"])
@jwt_required()
def update_match(match_id):
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    action = data.get("status")  # confirmed | rejected | deferred
    comment = data.get("comment")

    if action == "confirmed":
        m = confirm_match(match_id, user_id, comment)
    elif action == "rejected":
        m = reject_match(match_id, user_id, comment)
    else:
        m = ProductMatch.query.get_or_404(match_id)
        m.status = action or m.status
        m.comment = comment
        m.reviewed_by_id = user_id
        from datetime import datetime
        m.reviewed_at = datetime.utcnow()
        db.session.commit()

    return jsonify(m.to_dict())


@matches_bp.route("/cases/<int:case_id>/flags", methods=["GET"])
@jwt_required()
def list_flags(case_id):
    flags = AnalyticalFlag.query.filter_by(case_id=case_id).order_by(AnalyticalFlag.created_at.desc()).all()
    return jsonify([f.to_dict() for f in flags])


@matches_bp.route("/flags/<int:flag_id>", methods=["PATCH"])
@jwt_required()
def update_flag(flag_id):
    data = request.get_json() or {}
    flag = AnalyticalFlag.query.get_or_404(flag_id)
    if "status" in data:
        flag.status = data["status"]
    if "comment" in data:
        # store via review if needed
        pass
    db.session.commit()
    return jsonify(flag.to_dict())
