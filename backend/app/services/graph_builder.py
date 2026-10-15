"""
Build graph nodes/edges from ESF, procurement contracts, and entity_relations.
Risk heuristics: K_gos, top customer share, missing MTB keywords.
"""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import func
from app import db
from app.models.case import Case
from app.models.invoice import Invoice, InvoiceLine
from app.models.procurement import ProcurementContract
from app.models.relation import EntityRelation


# Keywords suggesting construction / repair works (need materials / equipment in purchases)
MTB_SUBJECT_KEYWORDS = [
    "строитель", "ремонт", "смр", "монтаж", "реконструк", "капремонт",
    "дорожн", "благоустрой", "отделочн", "кровельн", "фасад",
]
MTB_PURCHASE_KEYWORDS = [
    "цемент", "бетон", "арматур", "кирпич", "песок", "щебень", "краска",
    "труба", "кабель", "провод", "металл", "профиль", "гипсокартон",
    "аренда", "погрузчик", "экскаватор", "кран", "самосвал", "спецтехник",
    "субподряд", "строительн", "материал",
]


def _node_id(kind: str, key: str) -> str:
    return f"{kind}:{key}"


def _money(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def build_graph(
    case_id: int,
    min_amount: float = 0.0,
    edge_types: Optional[List[str]] = None,
    depth: int = 2,
) -> Dict[str, Any]:
    case = Case.query.get(case_id)
    if not case:
        raise ValueError("Case not found")

    root_bin = (case.bin or "").strip()
    allowed = set(edge_types) if edge_types else {
        "esf_purchase", "esf_sale", "gov_contract", "manual", "management", "same_address", "anomaly"
    }

    nodes: Dict[str, dict] = {}
    edges: List[dict] = []
    edge_keys: Set[str] = set()

    def add_node(nid: str, label: str, ntype: str, bin_or_iin: str = None, meta: dict = None):
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "label": (label or bin_or_iin or nid)[:120],
                "type": ntype,
                "bin": bin_or_iin,
                "meta": meta or {},
            }
        else:
            if label and len(label) > len(nodes[nid].get("label") or ""):
                nodes[nid]["label"] = label[:120]
            if meta:
                nodes[nid]["meta"].update(meta)

    def add_edge(source: str, target: str, etype: str, weight: float, meta: dict = None):
        if etype not in allowed:
            return
        if weight < min_amount and etype.startswith("esf"):
            return
        key = f"{source}|{target}|{etype}"
        if key in edge_keys:
            # accumulate weight
            for e in edges:
                if e["id"] == key:
                    e["weight"] = round(e["weight"] + weight, 2)
                    return
        edge_keys.add(key)
        edges.append({
            "id": key,
            "source": source,
            "target": target,
            "type": etype,
            "weight": round(weight, 2),
            "risk": None,
            "meta": meta or {},
        })

    # Root organization
    root_id = _node_id("org", root_bin or f"case-{case_id}")
    add_node(root_id, case.organization_name or "Исследуемая организация", "organization", root_bin, {"root": True})

    # ---- ESF aggregates by counterparty ----
    # Purchases: suppliers → root
    purchase_q = (
        db.session.query(
            Invoice.supplier_bin,
            Invoice.supplier_name,
            func.coalesce(func.sum(InvoiceLine.amount), 0),
            func.count(InvoiceLine.id),
        )
        .join(InvoiceLine, InvoiceLine.invoice_id == Invoice.id)
        .filter(Invoice.case_id == case_id, Invoice.operation_type == "purchase")
        .group_by(Invoice.supplier_bin, Invoice.supplier_name)
        .all()
    )
    for sbin, sname, amount, cnt in purchase_q:
        amount = _money(amount)
        if amount < min_amount:
            continue
        key = (sbin or sname or "unknown").strip() or "unknown"
        nid = _node_id("org", key)
        add_node(nid, sname or key, "organization", sbin)
        add_edge(nid, root_id, "esf_purchase", amount, {"docs": cnt})

    # Sales: root → buyers
    sale_q = (
        db.session.query(
            Invoice.buyer_bin,
            Invoice.buyer_name,
            func.coalesce(func.sum(InvoiceLine.amount), 0),
            func.count(InvoiceLine.id),
        )
        .join(InvoiceLine, InvoiceLine.invoice_id == Invoice.id)
        .filter(Invoice.case_id == case_id, Invoice.operation_type == "sale")
        .group_by(Invoice.buyer_bin, Invoice.buyer_name)
        .all()
    )
    for bbin, bname, amount, cnt in sale_q:
        amount = _money(amount)
        if amount < min_amount:
            continue
        key = (bbin or bname or "unknown").strip() or "unknown"
        nid = _node_id("org", key)
        # mark likely gov if name hints
        ntype = "gov" if bname and any(x in (bname or "").upper() for x in ("ГУ ", "ГК ", "АКИМАТ", "МИНИСТЕР", "ДЕПАРТАМЕНТ", "КГП", "РГП")) else "organization"
        add_node(nid, bname or key, ntype, bbin)
        add_edge(root_id, nid, "esf_sale", amount, {"docs": cnt})

    # ---- Procurement contracts ----
    contracts = ProcurementContract.query.filter_by(case_id=case_id).all()
    gov_sum = 0.0
    customer_totals: Dict[str, float] = defaultdict(float)
    for c in contracts:
        amt = _money(c.amount)
        gov_sum += amt
        cbin = (c.customer_bin or "").strip()
        sbin = (c.supplier_bin or root_bin or "").strip()
        cid_key = c.contract_number or c.procurement_number or str(c.id)
        cnode = _node_id("contract", cid_key)
        add_node(cnode, f"Договор {cid_key}"[:80], "contract", None, {
            "subject": (c.subject or "")[:200],
            "amount": amt,
            "status": c.status,
        })
        cust_id = _node_id("org", cbin or c.customer_name or "customer")
        add_node(cust_id, c.customer_name or cbin or "Заказчик", "gov", cbin)
        sup_id = _node_id("org", sbin or root_bin or "supplier")
        add_node(sup_id, c.supplier_name or case.organization_name or sbin, "organization", sbin)
        if amt >= min_amount or min_amount == 0:
            add_edge(cust_id, cnode, "gov_contract", amt, {"role": "customer"})
            add_edge(cnode, sup_id, "gov_contract", amt, {"role": "supplier"})
        if cbin:
            customer_totals[cbin] += amt

    # ---- Manual / stored relations ----
    for rel in EntityRelation.query.filter_by(case_id=case_id).all():
        et = rel.relation_type or "manual"
        if et not in allowed and "manual" not in allowed:
            continue
        src = _node_id(rel.from_entity_type or "org", str(rel.from_entity_id or rel.from_entity_label or "x"))
        tgt = _node_id(rel.to_entity_type or "org", str(rel.to_entity_id or rel.to_entity_label or "y"))
        add_node(src, rel.from_entity_label or src, rel.from_entity_type or "organization")
        add_node(tgt, rel.to_entity_label or tgt, rel.to_entity_type or "organization")
        add_edge(src, tgt, et if et in allowed else "manual", 0, {
            "relation_id": rel.id,
            "source": rel.source,
            "status": rel.status,
            "comment": rel.comment,
        })

    # ---- Depth filter: keep nodes within N hops from root ----
    if depth and depth > 0:
        keep = {root_id}
        frontier = {root_id}
        for _ in range(depth):
            nxt = set()
            for e in edges:
                if e["source"] in frontier:
                    nxt.add(e["target"])
                if e["target"] in frontier:
                    nxt.add(e["source"])
            keep |= nxt
            frontier = nxt
        nodes = {k: v for k, v in nodes.items() if k in keep}
        edges = [e for e in edges if e["source"] in keep and e["target"] in keep]

    # ---- Risks ----
    sale_total = sum(e["weight"] for e in edges if e["type"] == "esf_sale")
    purchase_total = sum(e["weight"] for e in edges if e["type"] == "esf_purchase")
    k_gos = (gov_sum / sale_total) if sale_total > 0 else (1.0 if gov_sum > 0 else 0.0)
    top_share = 0.0
    if customer_totals and gov_sum > 0:
        top_share = max(customer_totals.values()) / gov_sum

    risks = []
    if k_gos >= 0.5 and gov_sum > 0:
        risks.append({
            "code": "high_k_gos",
            "title": "Высокая доля госзакупок в обороте",
            "description": f"K_gos ≈ {k_gos:.0%}: сумма договоров {gov_sum:,.0f} ₸ при реализации по ЭСФ {sale_total:,.0f} ₸. Требует проверки, не является доказательством нарушения.",
            "severity": "high" if k_gos >= 0.8 else "medium",
            "value": round(k_gos, 4),
        })
    if top_share >= 0.4 and gov_sum > 0:
        risks.append({
            "code": "top_customer",
            "title": "Концентрация на одном госзаказчике",
            "description": f"Доля крупнейшего заказчика ≈ {top_share:.0%} от суммы договоров.",
            "severity": "medium",
            "value": round(top_share, 4),
        })

    # Missing MTB heuristic
    purchase_names = " ".join(
        (r[0] or "").lower()
        for r in db.session.query(InvoiceLine.product_name)
        .join(Invoice)
        .filter(InvoiceLine.case_id == case_id, Invoice.operation_type == "purchase")
        .limit(5000)
        .all()
    )
    has_mtb_purchase = any(k in purchase_names for k in MTB_PURCHASE_KEYWORDS)
    for c in contracts:
        subj = (c.subject or "").lower()
        if any(k in subj for k in MTB_SUBJECT_KEYWORDS) and not has_mtb_purchase:
            risks.append({
                "code": "no_mtb",
                "title": "Возможное отсутствие МТБ под предмет договора",
                "description": (
                    f"Предмет договора содержит признаки СМР/ремонта («{(c.subject or '')[:100]}»), "
                    f"но во входящих ЭСФ не найдено типичных материалов/аренды техники. "
                    f"Требует ручной проверки (возможны закупки вне выборки)."
                ),
                "severity": "high",
                "value": _money(c.amount),
                "contract": c.contract_number,
            })
            # mark related edges
            for e in edges:
                if e["type"] == "gov_contract" and (c.contract_number or "") in e["id"]:
                    e["risk"] = "no_mtb"
            break  # one signal enough at case level

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "risks": risks,
        "stats": {
            "k_gos": round(k_gos, 4),
            "top_customer_share": round(top_share, 4),
            "gov_contracts_sum": round(gov_sum, 2),
            "esf_sale_sum": round(sale_total, 2),
            "esf_purchase_sum": round(purchase_total, 2),
            "nodes_count": len(nodes),
            "edges_count": len(edges),
            "depth": depth,
            "min_amount": min_amount,
        },
    }
