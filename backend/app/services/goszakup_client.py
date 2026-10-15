"""
Official OWS client for goszakup.gov.kz (v3).
Token from env GOSZAKUP_API_TOKEN only — never hardcode.
"""
from __future__ import annotations
import os
import time
from typing import Any, Dict, List, Optional
import requests
from flask import current_app


class GoszakupClient:
    def __init__(self, token: Optional[str] = None, base_url: Optional[str] = None):
        self.token = token or os.getenv("GOSZAKUP_API_TOKEN", "")
        self.base_url = (base_url or os.getenv("GOSZAKUP_BASE_URL", "https://ows.goszakup.gov.kz")).rstrip("/")
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            })

    @property
    def available(self) -> bool:
        return bool(self.token)

    def _get(self, path: str, params: Optional[dict] = None, retries: int = 3) -> Any:
        if not self.token:
            raise RuntimeError("GOSZAKUP_API_TOKEN не задан. Добавьте токен в .env / docker-compose.")
        url = f"{self.base_url}{path}"
        last_err = None
        for attempt in range(retries):
            try:
                r = self.session.get(url, params=params or {}, timeout=60)
                if r.status_code == 401:
                    raise RuntimeError("Токен goszakup отклонён (401). Проверьте GOSZAKUP_API_TOKEN.")
                if r.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:
                last_err = e
                time.sleep(1 + attempt)
        raise RuntimeError(f"Ошибка OWS API: {last_err}")

    def subject_by_bin(self, bin_code: str) -> Optional[dict]:
        bin_code = "".join(c for c in str(bin_code) if c.isdigit())
        if len(bin_code) < 10:
            return None
        try:
            data = self._get(f"/v3/subject/biin/{bin_code}")
            if isinstance(data, list) and data:
                return data[0]
            if isinstance(data, dict):
                return data.get("items", [data])[0] if data.get("items") else data
        except Exception:
            return None
        return None

    def contracts_by_supplier_bin(self, bin_code: str, limit: int = 100) -> List[dict]:
        """Fetch contracts where company is supplier. Endpoint variants differ by OWS version."""
        bin_code = "".join(c for c in str(bin_code) if c.isdigit())
        items: List[dict] = []
        # Try common patterns
        for path, params in [
            ("/v3/contract", {"supplier_biin": bin_code, "limit": limit}),
            ("/v3/contracts", {"supplier_biin": bin_code, "limit": limit}),
            (f"/v3/contract/biin/{bin_code}", {"limit": limit}),
        ]:
            try:
                data = self._get(path, params)
                if isinstance(data, dict):
                    batch = data.get("items") or data.get("data") or []
                elif isinstance(data, list):
                    batch = data
                else:
                    batch = []
                if batch:
                    items.extend(batch)
                    break
            except Exception:
                continue
        return items[:limit]

    def contracts_by_customer_bin(self, bin_code: str, limit: int = 100) -> List[dict]:
        bin_code = "".join(c for c in str(bin_code) if c.isdigit())
        items: List[dict] = []
        for path, params in [
            ("/v3/contract", {"customer_biin": bin_code, "limit": limit}),
            ("/v3/contracts", {"customer_biin": bin_code, "limit": limit}),
        ]:
            try:
                data = self._get(path, params)
                if isinstance(data, dict):
                    batch = data.get("items") or data.get("data") or []
                elif isinstance(data, list):
                    batch = data
                else:
                    batch = []
                if batch:
                    items.extend(batch)
                    break
            except Exception:
                continue
        return items[:limit]


def normalize_contract_row(raw: dict) -> dict:
    """Map heterogeneous OWS fields to our ProcurementContract shape."""
    def g(*keys, default=None):
        for k in keys:
            if k in raw and raw[k] is not None and str(raw[k]).strip() != "":
                return raw[k]
        return default

    return {
        "procurement_number": str(g("number_anno", "trd_buy_number_anno", "anno_number", default="") or ""),
        "contract_number": str(g("contract_number", "number_contract", "sys_number", "id", default="") or ""),
        "contract_date": g("sign_date", "contract_date", "date_sign", "createdate"),
        "customer_name": str(g("customer_name", "customer_name_ru", "customer", default="") or ""),
        "customer_bin": "".join(c for c in str(g("customer_bin", "customer_biin", "customer_iin", default="") or "") if c.isdigit())[:20],
        "supplier_name": str(g("supplier_name", "supplier_name_ru", "supplier", default="") or ""),
        "supplier_bin": "".join(c for c in str(g("supplier_bin", "supplier_biin", "supplier_iin", default="") or "") if c.isdigit())[:20],
        "subject": str(g("contract_name_ru", "name_ru", "subject_name", "description", "name", default="") or "")[:2000],
        "amount": g("contract_sum", "sum", "total_sum", "amount", default=0),
        "status": str(g("ref_contract_status_id", "status_name_ru", "status", default="") or ""),
        "source_url": f"https://goszakup.gov.kz",
        "raw": raw,
    }
