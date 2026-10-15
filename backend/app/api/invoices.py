from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.invoice import Invoice, InvoiceLine
from sqlalchemy import func

invoices_bp = Blueprint("invoices", __name__)


@invoices_bp.route("/cases/<int:case_id>/invoices", methods=["GET"])
@jwt_required()
def list_invoices(case_id):
    op_type = request.args.get("operation_type")
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)

    q = Invoice.query.filter_by(case_id=case_id)
    if op_type:
        q = q.filter_by(operation_type=op_type)
    q = q.order_by(Invoice.document_date.desc().nullslast())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [i.to_dict() for i in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
    })


@invoices_bp.route("/cases/<int:case_id>/lines", methods=["GET"])
@jwt_required()
def list_lines(case_id):
    op_type = request.args.get("operation_type")
    search = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)

    q = InvoiceLine.query.filter_by(case_id=case_id)
    if op_type:
        q = q.join(Invoice).filter(Invoice.operation_type == op_type)
    if search:
        q = q.filter(InvoiceLine.product_name.ilike(f"%{search}%"))
    q = q.order_by(InvoiceLine.id)
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [l.to_dict() for l in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
    })


@invoices_bp.route("/cases/<int:case_id>/summary", methods=["GET"])
@jwt_required()
def summary(case_id):
    def agg(op):
        return db.session.query(
            func.count(InvoiceLine.id),
            func.coalesce(func.sum(InvoiceLine.amount), 0),
            func.coalesce(func.sum(InvoiceLine.quantity), 0),
        ).join(Invoice).filter(
            InvoiceLine.case_id == case_id,
            Invoice.operation_type == op,
        ).one()

    p_cnt, p_sum, p_qty = agg("purchase")
    s_cnt, s_sum, s_qty = agg("sale")

    # By supplier
    by_supplier = db.session.query(
        Invoice.supplier_name,
        Invoice.supplier_bin,
        func.count(InvoiceLine.id),
        func.coalesce(func.sum(InvoiceLine.amount), 0),
    ).join(InvoiceLine).filter(
        Invoice.case_id == case_id,
        Invoice.operation_type == "purchase",
    ).group_by(Invoice.supplier_name, Invoice.supplier_bin).order_by(
        func.sum(InvoiceLine.amount).desc()
    ).limit(50).all()

    by_buyer = db.session.query(
        Invoice.buyer_name,
        Invoice.buyer_bin,
        func.count(InvoiceLine.id),
        func.coalesce(func.sum(InvoiceLine.amount), 0),
    ).join(InvoiceLine).filter(
        Invoice.case_id == case_id,
        Invoice.operation_type == "sale",
    ).group_by(Invoice.buyer_name, Invoice.buyer_bin).order_by(
        func.sum(InvoiceLine.amount).desc()
    ).limit(50).all()

    return jsonify({
        "purchase": {
            "count": p_cnt,
            "amount": float(p_sum),
            "quantity": float(p_qty),
        },
        "sale": {
            "count": s_cnt,
            "amount": float(s_sum),
            "quantity": float(s_qty),
        },
        "by_supplier": [
            {"name": n, "bin": b, "count": c, "amount": float(a)}
            for n, b, c, a in by_supplier
        ],
        "by_buyer": [
            {"name": n, "bin": b, "count": c, "amount": float(a)}
            for n, b, c, a in by_buyer
        ],
    })
