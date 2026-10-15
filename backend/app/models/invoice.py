from app import db
from datetime import datetime
from sqlalchemy.orm import relationship
from decimal import Decimal


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    source_file_id = db.Column(db.Integer, db.ForeignKey("source_files.id"))
    import_job_id = db.Column(db.Integer, db.ForeignKey("import_jobs.id"))
    document_number = db.Column(db.String(100), index=True)
    document_date = db.Column(db.Date, index=True)
    operation_type = db.Column(db.String(20), index=True)  # purchase | sale
    supplier_name = db.Column(db.String(500))
    supplier_bin = db.Column(db.String(20), index=True)
    buyer_name = db.Column(db.String(500))
    buyer_bin = db.Column(db.String(20), index=True)
    total_amount = db.Column(db.Numeric(18, 2))
    currency = db.Column(db.String(10), default="KZT")
    original_row = db.Column(db.Integer)  # row number in source file
    raw_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")

    def to_dict(self, include_lines=False):
        data = {
            "id": self.id,
            "case_id": self.case_id,
            "document_number": self.document_number,
            "document_date": self.document_date.isoformat() if self.document_date else None,
            "operation_type": self.operation_type,
            "supplier_name": self.supplier_name,
            "supplier_bin": self.supplier_bin,
            "buyer_name": self.buyer_name,
            "buyer_bin": self.buyer_bin,
            "total_amount": float(self.total_amount) if self.total_amount is not None else None,
            "currency": self.currency,
            "original_row": self.original_row,
        }
        if include_lines:
            data["lines"] = [l.to_dict() for l in self.lines]
        return data


class InvoiceLine(db.Model):
    __tablename__ = "invoice_lines"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    product_name = db.Column(db.String(1000), nullable=False)
    product_name_normalized = db.Column(db.String(1000), index=True)
    product_code = db.Column(db.String(100), index=True)
    quantity = db.Column(db.Numeric(18, 4))
    unit = db.Column(db.String(50))
    unit_price = db.Column(db.Numeric(18, 4))
    amount = db.Column(db.Numeric(18, 2))
    vat_amount = db.Column(db.Numeric(18, 2))
    original_row = db.Column(db.Integer)
    source_file_id = db.Column(db.Integer, db.ForeignKey("source_files.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="lines")
    case = relationship("Case")

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "case_id": self.case_id,
            "product_name": self.product_name,
            "product_name_normalized": self.product_name_normalized,
            "product_code": self.product_code,
            "quantity": float(self.quantity) if self.quantity is not None else None,
            "unit": self.unit,
            "unit_price": float(self.unit_price) if self.unit_price is not None else None,
            "amount": float(self.amount) if self.amount is not None else None,
            "vat_amount": float(self.vat_amount) if self.vat_amount is not None else None,
            "original_row": self.original_row,
            "operation_type": self.invoice.operation_type if self.invoice else None,
            "document_number": self.invoice.document_number if self.invoice else None,
            "document_date": self.invoice.document_date.isoformat() if self.invoice and self.invoice.document_date else None,
            "supplier_name": self.invoice.supplier_name if self.invoice else None,
            "supplier_bin": self.invoice.supplier_bin if self.invoice else None,
            "buyer_name": self.invoice.buyer_name if self.invoice else None,
            "buyer_bin": self.invoice.buyer_bin if self.invoice else None,
        }
