"""
File import and processing service for ESF / Excel / CSV.
"""
import os
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from rapidfuzz import fuzz
from app import db
from app.models.source_file import SourceFile, ImportJob
from app.models.invoice import Invoice, InvoiceLine
from app.models.flag import AnalyticalFlag
from flask import current_app


# Common column name variants (Russian + English)
COLUMN_ALIASES = {
    "product_name": [
        "наименование тру",
        "наименование товара", "товар", "описание товара", "наименование",
        "product", "product name", "description", "наименование продукции",
        "наименование товара/работы/услуги", "товар/работа/услуга", "tru name",
    ],
    "product_code": [
        "тн вэд",
        "код тн вэд", "код товара", "код", "артикул", "product code", "sku", "tn ved", "tnved",
    ],
    "quantity": [
        "кол-во (объем)",
        "кол-во", "количество", "кол во", "qty", "quantity", "объем",
    ],
    "unit": [
        "единица измерения",
        "ед. изм.", "ед.изм", "unit", "единица",
    ],
    "unit_price": [
        "цена без ндс",
        "цена за единицу", "цена", "цена за ед.", "unit price", "price",
        "стоимость единицы", "цена с ндс",
    ],
    "amount": [
        "стоимость",
        "общая сумма", "сумма", "итого", "сумма без ндс", "total", "amount",
    ],
    "document_number": [
        "invoice_number",
        "registration_number", "номер документа", "номер эсф",
        "номер счета", "invoice number", "document number", "№",
    ],
    "document_date": [
        "invoice_date",
        "turnover_date", "дата", "дата оборота", "дата документа",
        "date", "invoice date", "дата выписки",
    ],
    "supplier_name": [
        "поставщик",
        "наименование поставщика", "продавец", "supplier", "seller",
    ],
    "supplier_bin": [
        "iin_seller",
        "иин/бин", "бин поставщика", "иин/бин продавца", "бин продавца",
        "supplier bin", "seller bin",
    ],
    "buyer_name": [
        "покупатель",
        "наименование покупателя", "получатель", "buyer", "customer",
    ],
    "buyer_bin": [
        "iin_customer",
        "иин/бин2", "бин покупателя", "иин/бин получателя", "бин получателя",
        "buyer bin", "customer bin",
    ],
    "operation_type": [
        "тип операции", "направление", "operation type", "тип", "invoice_type",
    ],
    "vat_amount": [
        "сумма ндс",
        "ндс", "vat", "vat amount",
    ],
    "registration_number": [
        "registration_number", "регистрационный номер",
    ],
}

# Fixed mapping for standard Kazakhstan ESF export (exact header names)
ESF_FIXED_MAPPING = {
    "Наименование ТРУ": "product_name",
    "ТН ВЭД": "product_code",
    "Единица измерения": "unit",
    "Кол-во (объем)": "quantity",
    "Цена без НДС": "unit_price",
    "Стоимость": "amount",
    "Сумма НДС": "vat_amount",
    "IIN_SELLER": "supplier_bin",
    "Поставщик": "supplier_name",
    "IIN_CUSTOMER": "buyer_bin",
    "Покупатель": "buyer_name",
    "INVOICE_NUMBER": "document_number",
    "INVOICE_DATE": "document_date",
    "REGISTRATION_NUMBER": "registration_number",
    "TURNOVER_DATE": "document_date",  # fallback only if INVOICE_DATE missing
}



def normalize_header(h: str) -> str:
    if not isinstance(h, str):
        return ""
    h = h.strip().lower()
    h = re.sub(r"\s+", " ", h)
    return h


def suggest_column_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    """Suggest mapping from system fields to actual column names.

    For standard Kazakhstan ESF exports uses a fixed mapping (no manual work).
    Falls back to alias matching for other file formats.
    """
    mapping: Dict[str, Optional[str]] = {field: None for field in COLUMN_ALIASES}

    # 1) Exact fixed ESF mapping (priority)
    col_set = set(columns)
    fixed_hits = 0
    for col_name, field in ESF_FIXED_MAPPING.items():
        if col_name in col_set and mapping.get(field) is None:
            mapping[field] = col_name
            fixed_hits += 1

    # Prefer INVOICE_DATE over TURNOVER_DATE
    if "INVOICE_DATE" in col_set:
        mapping["document_date"] = "INVOICE_DATE"
    elif "TURNOVER_DATE" in col_set and mapping.get("document_date") is None:
        mapping["document_date"] = "TURNOVER_DATE"

    # Prefer IIN_SELLER / IIN_CUSTOMER over ИИН/БИН variants
    if "IIN_SELLER" in col_set:
        mapping["supplier_bin"] = "IIN_SELLER"
    if "IIN_CUSTOMER" in col_set:
        mapping["buyer_bin"] = "IIN_CUSTOMER"

    # If we matched most ESF columns — done
    if fixed_hits >= 8:
        return mapping

    # 2) Fallback: alias matching for non-standard files
    normalized = {normalize_header(c): c for c in columns}
    used_cols = {v for v in mapping.values() if v}
    for field, aliases in COLUMN_ALIASES.items():
        if mapping.get(field):
            continue
        found = None
        for alias in aliases:
            if alias in normalized and normalized[alias] not in used_cols:
                found = normalized[alias]
                break
        if not found:
            for alias in aliases:
                for norm, orig in normalized.items():
                    if orig in used_cols:
                        continue
                    if alias in norm or norm in alias:
                        found = orig
                        break
                if found:
                    break
        mapping[field] = found
        if found:
            used_cols.add(found)
    return mapping



def normalize_product_name(name: str) -> str:
    if not name or not isinstance(name, str):
        return ""
    name = name.strip().lower()
    name = re.sub(r"[^\w\sа-яёa-z0-9]", " ", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def parse_date(val) -> Optional[date]:
    if pd.isna(val) or val is None or val == "":
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    if isinstance(val, str):
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y.%m.%d"):
            try:
                return datetime.strptime(val.strip(), fmt).date()
            except ValueError:
                continue
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


def parse_decimal(val) -> Optional[Decimal]:
    if pd.isna(val) or val is None or val == "":
        return None
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val))
    s = str(val).strip().replace(" ", "").replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def sanitize_bin(val) -> Optional[str]:
    """Extract digits only from BIN/IIN; return None if empty or too long name-like."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", ""):
        return None
    digits = re.sub(r"\D", "", s)
    # Valid BIN=12 digits, IIN=12 digits in KZ
    if len(digits) == 12:
        return digits
    if 10 <= len(digits) <= 14:
        return digits[:12]
    return None  # reject names or garbage


def detect_operation_type(row: dict, mapping: dict, investigated_bin: str = None) -> str:
    """Determine purchase/sale by investigated org BIN or explicit type column."""
    if investigated_bin:
        inv = str(investigated_bin).strip()
        s_col = mapping.get("supplier_bin")
        b_col = mapping.get("buyer_bin")
        supplier = str(row.get(s_col, "")).strip() if s_col else ""
        buyer = str(row.get(b_col, "")).strip() if b_col else ""
        # clean non-digits for comparison
        inv_d = "".join(c for c in inv if c.isdigit())
        sup_d = "".join(c for c in supplier if c.isdigit())
        buy_d = "".join(c for c in buyer if c.isdigit())
        if inv_d and inv_d == buy_d and inv_d != sup_d:
            return "purchase"
        if inv_d and inv_d == sup_d and inv_d != buy_d:
            return "sale"
    ot_col = mapping.get("operation_type")
    if ot_col and ot_col in row:
        val = str(row[ot_col]).lower().strip()
        if any(x in val for x in ["приобр", "покуп", "purchase", "in"]):
            return "purchase"
        if any(x in val for x in ["реал", "прода", "sale", "out"]):
            return "sale"
    return "unknown"


def process_dataframe(
    df: pd.DataFrame,
    mapping: Dict[str, str],
    case_id: int,
    source_file_id: int,
    import_job_id: int,
    default_operation_type: str = "unknown",
    investigated_bin: str = None,
) -> Tuple[int, int, int, List[dict]]:
    """
    Process rows into Invoice + InvoiceLine.
    Returns: success_count, error_count, duplicate_count, error_report
    """
    success = 0
    errors = 0
    duplicates = 0
    error_report = []

    # Group by document if possible
    inv_cache = {}  # (doc_num, date, supplier_bin) -> Invoice

    for idx, row in df.iterrows():
        row_num = int(idx) + 2  # 1-based + header
        try:
            product_name = None
            if mapping.get("product_name") and mapping["product_name"] in row:
                product_name = str(row[mapping["product_name"]]).strip() if not pd.isna(row[mapping["product_name"]]) else None
            if not product_name:
                errors += 1
                error_report.append({"row": row_num, "error": "Отсутствует наименование товара"})
                continue

            doc_num = None
            if mapping.get("document_number") and mapping["document_number"] in row:
                doc_num = str(row[mapping["document_number"]]).strip() if not pd.isna(row[mapping["document_number"]]) else None

            doc_date = None
            if mapping.get("document_date") and mapping["document_date"] in row:
                doc_date = parse_date(row[mapping["document_date"]])

            supplier_name = None
            supplier_bin = None
            if mapping.get("supplier_name") and mapping["supplier_name"] in row:
                v = row[mapping["supplier_name"]]
                supplier_name = str(v).strip() if not pd.isna(v) and str(v).strip() else None
            if mapping.get("supplier_bin") and mapping["supplier_bin"] in row:
                supplier_bin = sanitize_bin(row[mapping["supplier_bin"]])
            # fallback: try to extract BIN from name field if bin empty (should not happen)

            buyer_name = None
            buyer_bin = None
            if mapping.get("buyer_name") and mapping["buyer_name"] in row:
                v = row[mapping["buyer_name"]]
                buyer_name = str(v).strip() if not pd.isna(v) and str(v).strip() else None
            if mapping.get("buyer_bin") and mapping["buyer_bin"] in row:
                buyer_bin = sanitize_bin(row[mapping["buyer_bin"]])

            op_type = detect_operation_type(row.to_dict(), mapping, investigated_bin)
            if op_type == "unknown":
                op_type = default_operation_type

            qty = parse_decimal(row[mapping["quantity"]]) if mapping.get("quantity") and mapping["quantity"] in row else None
            unit = str(row[mapping["unit"]]).strip() if mapping.get("unit") and mapping["unit"] in row and not pd.isna(row[mapping["unit"]]) else None
            unit_price = parse_decimal(row[mapping["unit_price"]]) if mapping.get("unit_price") and mapping["unit_price"] in row else None
            amount = parse_decimal(row[mapping["amount"]]) if mapping.get("amount") and mapping["amount"] in row else None
            product_code = str(row[mapping["product_code"]]).strip() if mapping.get("product_code") and mapping["product_code"] in row and not pd.isna(row[mapping["product_code"]]) else None

            # Basic validations (flag, do not drop)
            warnings = []
            if qty is not None and qty < 0:
                warnings.append("Отрицательное количество")
            if amount is not None and amount < 0:
                warnings.append("Отрицательная сумма")
            if unit_price is not None and unit_price < 0:
                warnings.append("Отрицательная цена")
            if supplier_bin and not re.match(r"^\d{10,14}$", supplier_bin):
                warnings.append("Некорректный формат БИН поставщика")
            if buyer_bin and not re.match(r"^\d{10,14}$", buyer_bin):
                warnings.append("Некорректный формат БИН покупателя")

            key = (doc_num or f"row-{row_num}", doc_date, supplier_bin or "")
            if key not in inv_cache:
                inv = Invoice(
                    case_id=case_id,
                    source_file_id=source_file_id,
                    import_job_id=import_job_id,
                    document_number=doc_num,
                    document_date=doc_date,
                    operation_type=op_type,
                    supplier_name=supplier_name,
                    supplier_bin=supplier_bin,
                    buyer_name=buyer_name,
                    buyer_bin=buyer_bin,
                    total_amount=amount,
                    original_row=row_num,
                    raw_data={k: (str(v) if not pd.isna(v) else None) for k, v in row.items()},
                )
                db.session.add(inv)
                db.session.flush()
                inv_cache[key] = inv
            else:
                inv = inv_cache[key]

            line = InvoiceLine(
                invoice_id=inv.id,
                case_id=case_id,
                product_name=product_name,
                product_name_normalized=normalize_product_name(product_name),
                product_code=product_code,
                quantity=qty,
                unit=unit,
                unit_price=unit_price,
                amount=amount,
                original_row=row_num,
                source_file_id=source_file_id,
            )
            db.session.add(line)
            success += 1

            if warnings:
                error_report.append({"row": row_num, "warnings": warnings})

        except Exception as e:
            errors += 1
            error_report.append({"row": row_num, "error": str(e)})

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        error_report.append({"error": f"DB commit failed: {e}"})
        raise
    return success, errors, duplicates, error_report


def run_import(job_id: int, column_mapping: Dict[str, str], default_op_type: str = "purchase"):
    from app.models.case import Case
    job = ImportJob.query.get(job_id)
    if not job:
        raise ValueError("Import job not found")
    sf = job.source_file
    case = Case.query.get(job.case_id)
    investigated_bin = case.bin if case else None
    job.status = "running"
    job.started_at = datetime.utcnow()
    job.column_mapping = column_mapping
    db.session.commit()

    try:
        path = sf.file_path
        ext = path.rsplit(".", 1)[-1].lower()
        if ext in ("xlsx", "xls"):
            df = pd.read_excel(path, dtype=str)
        elif ext == "csv":
            df = pd.read_csv(path, dtype=str, sep=None, engine="python")
        else:
            raise ValueError(f"Unsupported format: {ext}")

        df.columns = [str(c).strip() for c in df.columns]
        # Drop summary/total rows often present in ESF exports
        name_col = column_mapping.get("product_name")
        if name_col and name_col in df.columns:
            mask = ~df[name_col].astype(str).str.strip().str.upper().isin(["ИТОГ", "ИТОГО", "TOTAL", "NAN", ""])
            # also drop rows where seller name is ИТОГ
            for col in df.columns:
                if normalize_header(col) in ("поставщик", "покупатель"):
                    mask = mask & ~df[col].astype(str).str.strip().str.upper().isin(["ИТОГ", "ИТОГО", "TOTAL"])
            df = df[mask]
        job.total_rows = len(df)

        success, errors, dups, report = process_dataframe(
            df, column_mapping, job.case_id, sf.id, job.id, default_op_type, investigated_bin
        )
        job.success_rows = success
        job.error_rows = errors
        job.duplicate_rows = dups
        job.error_report = report
        job.result_summary = {
            "total": job.total_rows,
            "success": success,
            "errors": errors,
            "duplicates": dups,
        }
        job.status = "completed"
        job.finished_at = datetime.utcnow()
        sf.status = "processed"
        db.session.commit()
        return job
    except Exception as e:
        db.session.rollback()
        try:
            job = ImportJob.query.get(job_id)
            sf = job.source_file if job else None
            if job:
                job.status = "failed"
                job.error_report = [{"error": str(e)[:2000]}]
                job.finished_at = datetime.utcnow()
            if sf:
                sf.status = "error"
            db.session.commit()
        except Exception:
            db.session.rollback()
        raise
