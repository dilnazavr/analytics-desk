from app import db
from datetime import datetime
from sqlalchemy.orm import relationship
import uuid


class ReportVersion(db.Model):
    __tablename__ = "report_versions"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    version = db.Column(db.Integer, default=1)
    title = db.Column(db.String(500))
    status = db.Column(db.String(30), default="draft")  # draft | review | approved | exported
    content_json = db.Column(db.JSON)  # structured sections
    file_path = db.Column(db.String(1000))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    comment = db.Column(db.Text)

    case = relationship("Case", back_populates="reports")
    created_by = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "case_id": self.case_id,
            "version": self.version,
            "title": self.title,
            "status": self.status,
            "content_json": self.content_json,
            "file_path": self.file_path,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "comment": self.comment,
        }
