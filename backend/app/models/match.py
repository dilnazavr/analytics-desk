from app import db
from datetime import datetime
from sqlalchemy.orm import relationship


class ProductMatch(db.Model):
    __tablename__ = "product_matches"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    purchase_line_id = db.Column(db.Integer, db.ForeignKey("invoice_lines.id"), nullable=False)
    sale_line_id = db.Column(db.Integer, db.ForeignKey("invoice_lines.id"), nullable=False)
    match_type = db.Column(db.String(20))  # exact | fuzzy | manual
    similarity_score = db.Column(db.Float)
    price_diff = db.Column(db.Numeric(18, 4))
    price_diff_percent = db.Column(db.Float)
    quantity_diff = db.Column(db.Numeric(18, 4))
    status = db.Column(db.String(30), default="proposed")  # proposed | confirmed | rejected | deferred
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="matches")
    purchase_line = relationship("InvoiceLine", foreign_keys=[purchase_line_id])
    sale_line = relationship("InvoiceLine", foreign_keys=[sale_line_id])
    reviewed_by = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "purchase_line_id": self.purchase_line_id,
            "sale_line_id": self.sale_line_id,
            "match_type": self.match_type,
            "similarity_score": self.similarity_score,
            "price_diff": float(self.price_diff) if self.price_diff is not None else None,
            "price_diff_percent": self.price_diff_percent,
            "quantity_diff": float(self.quantity_diff) if self.quantity_diff is not None else None,
            "status": self.status,
            "reviewed_by_id": self.reviewed_by_id,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "comment": self.comment,
            "purchase": self.purchase_line.to_dict() if self.purchase_line else None,
            "sale": self.sale_line.to_dict() if self.sale_line else None,
        }
