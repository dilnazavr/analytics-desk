"""
Product matching service: exact, fuzzy, manual.
Optimized for large ESF datasets (tens of thousands of rows).
"""
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Set, Tuple
from rapidfuzz import fuzz, process
from app import db
from app.models.invoice import Invoice, InvoiceLine
from app.models.match import ProductMatch
from app.models.flag import AnalyticalFlag
from flask import current_app


def _load_lines(case_id: int, op_type: str) -> List[InvoiceLine]:
    return (
        InvoiceLine.query
        .join(Invoice)
        .filter(
            InvoiceLine.case_id == case_id,
            Invoice.operation_type == op_type,
        )
        .all()
    )


def find_matches_for_case(case_id: int, fuzzy_threshold: float = 85.0) -> List[ProductMatch]:
    """
    Auto-match purchase lines to sale lines.

    Strategy (fast → slow):
      1. Exact match by product_code
      2. Exact match by product_name_normalized
      3. Fuzzy match only among remaining lines, blocked by first token
         and limited candidates per purchase line
    """
    purchase_lines = _load_lines(case_id, "purchase")
    sale_lines = _load_lines(case_id, "sale")

    if not purchase_lines or not sale_lines:
        return []

    # Already matched pairs
    existing: Set[Tuple[int, int]] = {
        (m.purchase_line_id, m.sale_line_id)
        for m in ProductMatch.query.filter_by(case_id=case_id).with_entities(
            ProductMatch.purchase_line_id, ProductMatch.sale_line_id
        ).all()
    }

    # Indexes for sales
    by_code: Dict[str, List[InvoiceLine]] = defaultdict(list)
    by_name: Dict[str, List[InvoiceLine]] = defaultdict(list)
    by_token: Dict[str, List[InvoiceLine]] = defaultdict(list)

    for s in sale_lines:
        if s.product_code:
            code = s.product_code.strip().upper()
            if code:
                by_code[code].append(s)
        name = (s.product_name_normalized or "").strip()
        if name:
            by_name[name].append(s)
            token = name.split()[0] if name.split() else ""
            if len(token) >= 3:
                by_token[token].append(s)

    new_matches: List[ProductMatch] = []
    matched_purchase_ids: Set[int] = set()
    matched_sale_ids: Set[int] = set()
    price_threshold = current_app.config.get("PRICE_DEVIATION_THRESHOLD", 50.0)

    def _make_match(p: InvoiceLine, s: InvoiceLine, match_type: str, score: float):
        if (p.id, s.id) in existing:
            return None
        if p.id in matched_purchase_ids or s.id in matched_sale_ids:
            return None  # 1-to-1 greedy for speed

        price_diff = None
        price_diff_pct = None
        if p.unit_price is not None and s.unit_price is not None:
            price_diff = s.unit_price - p.unit_price
            if p.unit_price > 0:
                price_diff_pct = float((price_diff / p.unit_price) * 100)

        qty_diff = None
        if p.quantity is not None and s.quantity is not None:
            qty_diff = s.quantity - p.quantity

        m = ProductMatch(
            case_id=case_id,
            purchase_line_id=p.id,
            sale_line_id=s.id,
            match_type=match_type,
            similarity_score=score,
            price_diff=price_diff,
            price_diff_percent=price_diff_pct,
            quantity_diff=qty_diff,
            status="proposed",
        )
        db.session.add(m)
        new_matches.append(m)
        matched_purchase_ids.add(p.id)
        matched_sale_ids.add(s.id)
        existing.add((p.id, s.id))

        if price_diff_pct is not None and abs(price_diff_pct) >= price_threshold:
            flag = AnalyticalFlag(
                case_id=case_id,
                category="price_deviation",
                title=f"Существенное отклонение цены: {(p.product_name or '')[:80]}",
                description=(
                    f"Цена приобретения: {p.unit_price}, "
                    f"цена реализации: {s.unit_price}, "
                    f"отклонение: {price_diff_pct:.1f}%"
                ),
                severity="high" if abs(price_diff_pct) >= 100 else "medium",
                deviation_value=price_diff_pct,
                rule_applied=f"price_diff_percent >= {price_threshold}%",
                source_entities={
                    "purchase_line_id": p.id,
                    "sale_line_id": s.id,
                },
                status="new",
            )
            db.session.add(flag)
        return m

    # ---- Phase 1: exact by code ----
    for p in purchase_lines:
        if p.id in matched_purchase_ids:
            continue
        code = (p.product_code or "").strip().upper()
        if not code:
            continue
        candidates = by_code.get(code, [])
        for s in candidates:
            if _make_match(p, s, "exact", 100.0):
                break  # one match per purchase line

    # ---- Phase 2: exact by normalized name ----
    for p in purchase_lines:
        if p.id in matched_purchase_ids:
            continue
        name = (p.product_name_normalized or "").strip()
        if not name:
            continue
        candidates = by_name.get(name, [])
        for s in candidates:
            if s.id in matched_sale_ids:
                continue
            if _make_match(p, s, "exact", 100.0):
                break

    # ---- Phase 3: fuzzy (blocked, limited) ----
    # Only for unmatched purchases; candidates = same first token, max 30
    MAX_CANDIDATES = 30
    for p in purchase_lines:
        if p.id in matched_purchase_ids:
            continue
        name = (p.product_name_normalized or "").strip()
        if not name or len(name) < 4:
            continue
        token = name.split()[0] if name.split() else ""
        if len(token) < 3:
            continue

        pool = [s for s in by_token.get(token, []) if s.id not in matched_sale_ids]
        if not pool:
            continue
        if len(pool) > MAX_CANDIDATES:
            # pre-filter with rapidfuzz extract
            choices = {s.id: (s.product_name_normalized or "") for s in pool}
            top = process.extract(
                name,
                choices,
                scorer=fuzz.token_sort_ratio,
                limit=MAX_CANDIDATES,
                score_cutoff=fuzzy_threshold,
            )
            # top items: (choice_value, score, key)
            id_to_s = {s.id: s for s in pool}
            for _val, score, sid in top:
                s = id_to_s.get(sid)
                if s and _make_match(p, s, "fuzzy", float(score)):
                    break
        else:
            best_s = None
            best_score = 0.0
            for s in pool:
                sn = s.product_name_normalized or ""
                score = fuzz.token_sort_ratio(name, sn)
                if score >= fuzzy_threshold and score > best_score:
                    best_score = score
                    best_s = s
            if best_s:
                _make_match(p, best_s, "fuzzy", best_score)

    # Commit in one go
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return new_matches


def confirm_match(match_id: int, user_id: int, comment: str = None) -> ProductMatch:
    m = ProductMatch.query.get_or_404(match_id)
    m.status = "confirmed"
    m.reviewed_by_id = user_id
    m.reviewed_at = datetime.utcnow()
    m.comment = comment
    db.session.commit()
    return m


def reject_match(match_id: int, user_id: int, comment: str = None) -> ProductMatch:
    m = ProductMatch.query.get_or_404(match_id)
    m.status = "rejected"
    m.reviewed_by_id = user_id
    m.reviewed_at = datetime.utcnow()
    m.comment = comment
    db.session.commit()
    return m
