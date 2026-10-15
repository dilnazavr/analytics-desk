from app import db
from datetime import datetime
from sqlalchemy.orm import relationship


class Counterparty(db.Model):
    __tablename__ = "counterparties"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    name = db.Column(db.String(500), nullable=False)
    bin_or_iin = db.Column(db.String(12), index=True)
    role = db.Column(db.String(50))  # supplier | buyer | both
    documents_count = db.Column(db.Integer, default=0)
    purchase_amount = db.Column(db.Numeric(18, 2), default=0)
    sale_amount = db.Column(db.Numeric(18, 2), default=0)
    share_percent = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case = relationship("Case")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "name": self.name,
            "bin_or_iin": self.bin_or_iin,
            "role": self.role,
            "documents_count": self.documents_count,
            "purchase_amount": float(self.purchase_amount) if self.purchase_amount else 0,
            "sale_amount": float(self.sale_amount) if self.sale_amount else 0,
            "share_percent": self.share_percent,
        }
