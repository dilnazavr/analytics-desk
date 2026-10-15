from app import db
from datetime import datetime
from sqlalchemy.orm import relationship


class AnalyticalFlag(db.Model):
    __tablename__ = "analytical_flags"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    flag_number = db.Column(db.String(20))
    category = db.Column(db.String(100))  # price_deviation | quantity_mismatch | missing_purchase | duplicate | other
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    severity = db.Column(db.String(20), default="medium")  # low | medium | high
    deviation_value = db.Column(db.Float)
    rule_applied = db.Column(db.String(255))
    source_entities = db.Column(db.JSON)  # list of related invoice_line ids etc.
    status = db.Column(db.String(30), default="new")  # new | under_review | confirmed | rejected | needs_data | included_in_report
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case = relationship("Case", back_populates="flags")
    reviews = relationship("FlagReview", back_populates="flag", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "flag_number": self.flag_number,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "deviation_value": self.deviation_value,
            "rule_applied": self.rule_applied,
            "source_entities": self.source_entities,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FlagReview(db.Model):
    __tablename__ = "flag_reviews"

    id = db.Column(db.Integer, primary_key=True)
    flag_id = db.Column(db.Integer, db.ForeignKey("analytical_flags.id"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(50))  # confirm | reject | request_data | include_in_report
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    flag = relationship("AnalyticalFlag", back_populates="reviews")
    reviewer = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "flag_id": self.flag_id,
            "reviewer_id": self.reviewer_id,
            "action": self.action,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
