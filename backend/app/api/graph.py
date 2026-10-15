from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.case import Case
from app.models.procurement import ProcurementContract
from app.models.relation import EntityRelation
from app.models.audit import AuditLog
from app.services.graph_builder import build_graph
from app.services.goszakup_client import GoszakupClient, normalize_contract_row
from decimal import Decimal, InvalidOperation

graph_bp = Blueprint("graph", __name__)


def _parse_date(v):
    if not v:
        return None
    if isinstance(v, date):
        return v
    s = str(v)[:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def _parse_amount(v):
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v).replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


@graph_bp.route("/cases/<int:case_id>/graph", methods=["GET"])
@jwt_required()
def get_graph(case_id):
    Case.query.get_or_404(case_id)
    min_amount = float(request.args.get("min_amount", 0) or 0)
    depth = int(request.args.get("depth", 2) or 2)
    depth = max(1, min(depth, 3))
    types_raw = request.args.get("edge_types", "")
    edge_types = [t.strip() for t in types_raw.split(",") if t.strip()] or None
    data = build_graph(case_id, min_amount=min_amount, edge_types=edge_types, depth=depth)
    return jsonify(data)


@graph_bp.route("/cases/<int:case_id>/procurement", methods=["GET"])
@jwt_required()
def list_procurement(case_id):
    Case.query.get_or_404(case_id)
    rows = ProcurementContract.query.filter_by(case_id=case_id).order_by(
        ProcurementContract.contract_date.desc().nullslast()
    ).all()
    return jsonify([r.to_dict() for r in rows])


@graph_bp.route("/cases/<int:case_id>/procurement", methods=["POST"])
@jwt_required()
def create_procurement(case_id):
    """Manual add or bulk from normalized JSON."""
    user_id = int(get_jwt_identity())
    Case.query.get_or_404(case_id)
    data = request.get_json() or {}
    items = data if isinstance(data, list) else [data]
    created = []
    for item in items:
        pc = ProcurementContract(
            case_id=case_id,
            procurement_number=item.get("procurement_number"),
            contract_number=item.get("contract_number"),
            contract_date=_parse_date(item.get("contract_date")),
            customer_name=item.get("customer_name"),
            customer_bin=item.get("customer_bin"),
            supplier_name=item.get("supplier_name"),
            supplier_bin=item.get("supplier_bin"),
            subject=item.get("subject"),
            amount=_parse_amount(item.get("amount")),
            status=item.get("status"),
            source_url=item.get("source_url"),
            data_obtained_at=datetime.utcnow(),
        )
        db.session.add(pc)
        created.append(pc)
    db.session.add(AuditLog(
        user_id=user_id, case_id=case_id, action="procurement_created",
        entity_type="procurement", details={"count": len(created)},
    ))
    db.session.commit()
    return jsonify([c.to_dict() for c in created]), 201


@graph_bp.route("/cases/<int:case_id>/procurement/sync", methods=["POST"])
@jwt_required()
def sync_procurement(case_id):
    """Pull contracts from OWS goszakup by case BIN (supplier and/or customer)."""
    user_id = int(get_jwt_identity())
    case = Case.query.get_or_404(case_id)
    body = request.get_json() or {}
    bin_code = body.get("bin") or case.bin
    if not bin_code:
        return jsonify({"error": "БИН дела не указан"}), 400

    client = GoszakupClient()
    if not client.available:
        return jsonify({
            "error": "GOSZAKUP_API_TOKEN не настроен",
            "hint": "Добавьте GOSZAKUP_API_TOKEN в environment backend (docker-compose / .env)",
        }), 503

    as_supplier = client.contracts_by_supplier_bin(bin_code, limit=int(body.get("limit", 100)))
    as_customer = client.contracts_by_customer_bin(bin_code, limit=int(body.get("limit", 50)))
    raw_list = as_supplier + as_customer

    created = 0
    skipped = 0
    errors = []
    for raw in raw_list:
        try:
            norm = normalize_contract_row(raw if isinstance(raw, dict) else {})
            # dedupe by contract_number + case
            exists = None
            if norm.get("contract_number"):
                exists = ProcurementContract.query.filter_by(
                    case_id=case_id, contract_number=str(norm["contract_number"])
                ).first()
            if exists:
                skipped += 1
                continue
            pc = ProcurementContract(
                case_id=case_id,
                procurement_number=norm.get("procurement_number") or None,
                contract_number=norm.get("contract_number") or None,
                contract_date=_parse_date(norm.get("contract_date")),
                customer_name=norm.get("customer_name") or None,
                customer_bin=norm.get("customer_bin") or None,
                supplier_name=norm.get("supplier_name") or None,
                supplier_bin=norm.get("supplier_bin") or None,
                subject=norm.get("subject") or None,
                amount=_parse_amount(norm.get("amount")),
                status=str(norm.get("status") or "")[:50] or None,
                source_url=norm.get("source_url"),
                data_obtained_at=datetime.utcnow(),
            )
            db.session.add(pc)
            created += 1
        except Exception as e:
            errors.append(str(e)[:200])

    db.session.add(AuditLog(
        user_id=user_id, case_id=case_id, action="procurement_sync",
        entity_type="procurement",
        details={"created": created, "skipped": skipped, "fetched": len(raw_list)},
    ))
    db.session.commit()
    return jsonify({
        "fetched": len(raw_list),
        "created": created,
        "skipped": skipped,
        "errors": errors[:10],
        "token_ok": True,
    })


@graph_bp.route("/cases/<int:case_id>/relations", methods=["GET"])
@jwt_required()
def list_relations(case_id):
    Case.query.get_or_404(case_id)
    rows = EntityRelation.query.filter_by(case_id=case_id).order_by(EntityRelation.id.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@graph_bp.route("/cases/<int:case_id>/relations", methods=["POST"])
@jwt_required()
def create_relation(case_id):
    user_id = int(get_jwt_identity())
    Case.query.get_or_404(case_id)
    data = request.get_json() or {}
    rel = EntityRelation(
        case_id=case_id,
        relation_type=data.get("relation_type") or "manual",
        from_entity_type=data.get("from_entity_type") or "organization",
        from_entity_id=data.get("from_entity_id"),
        from_entity_label=data.get("from_entity_label"),
        to_entity_type=data.get("to_entity_type") or "organization",
        to_entity_id=data.get("to_entity_id"),
        to_entity_label=data.get("to_entity_label"),
        source=data.get("source") or "ручной ввод",
        source_date=_parse_date(data.get("source_date")),
        status=data.get("status") or "unverified",
        comment=data.get("comment"),
    )
    db.session.add(rel)
    db.session.add(AuditLog(
        user_id=user_id, case_id=case_id, action="relation_created",
        entity_type="relation", entity_id=None, details=data,
    ))
    db.session.commit()
    return jsonify(rel.to_dict()), 201


@graph_bp.route("/relations/<int:rel_id>", methods=["PATCH"])
@jwt_required()
def update_relation(rel_id):
    user_id = int(get_jwt_identity())
    rel = EntityRelation.query.get_or_404(rel_id)
    data = request.get_json() or {}
    for f in ("relation_type", "from_entity_type", "from_entity_label", "to_entity_type",
              "to_entity_label", "source", "status", "comment"):
        if f in data:
            setattr(rel, f, data[f])
    if "source_date" in data:
        rel.source_date = _parse_date(data["source_date"])
    db.session.add(AuditLog(
        user_id=user_id, case_id=rel.case_id, action="relation_updated",
        entity_type="relation", entity_id=rel.id, details=data,
    ))
    db.session.commit()
    return jsonify(rel.to_dict())


@graph_bp.route("/relations/<int:rel_id>", methods=["DELETE"])
@jwt_required()
def delete_relation(rel_id):
    user_id = int(get_jwt_identity())
    rel = EntityRelation.query.get_or_404(rel_id)
    case_id = rel.case_id
    db.session.delete(rel)
    db.session.add(AuditLog(
        user_id=user_id, case_id=case_id, action="relation_deleted",
        entity_type="relation", entity_id=rel_id,
    ))
    db.session.commit()
    return jsonify({"ok": True})


@graph_bp.route("/goszakup/status", methods=["GET"])
@jwt_required()
def goszakup_status():
    client = GoszakupClient()
    return jsonify({"configured": client.available, "base_url": client.base_url})
