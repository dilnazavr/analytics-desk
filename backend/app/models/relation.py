from app import db
from datetime import datetime
from sqlalchemy.orm import relationship


class EntityRelation(db.Model):
    __tablename__ = "entity_relations"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    relation_type = db.Column(db.String(100), nullable=False)
    # director | founder | relative | same_address | operations | contract | same_ip | other
    from_entity_type = db.Column(db.String(50))  # organization | person | contract | address
    from_entity_id = db.Column(db.Integer)
    from_entity_label = db.Column(db.String(500))
    to_entity_type = db.Column(db.String(50))
    to_entity_id = db.Column(db.Integer)
    to_entity_label = db.Column(db.String(500))
    source = db.Column(db.String(255))
    source_date = db.Column(db.Date)
    valid_from = db.Column(db.Date)
    valid_to = db.Column(db.Date)
    status = db.Column(db.String(30), default="unverified")  # unverified | confirmed | rejected
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="relations")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "relation_type": self.relation_type,
            "from_entity_type": self.from_entity_type,
            "from_entity_id": self.from_entity_id,
            "from_entity_label": self.from_entity_label,
            "to_entity_type": self.to_entity_type,
            "to_entity_id": self.to_entity_id,
            "to_entity_label": self.to_entity_label,
            "source": self.source,
            "source_date": self.source_date.isoformat() if self.source_date else None,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "status": self.status,
            "comment": self.comment,
        }
