from app import db
from datetime import datetime
from sqlalchemy.orm import relationship
import uuid


class Case(db.Model):
    __tablename__ = "cases"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    number = db.Column(db.String(50), unique=True, nullable=False, index=True)  # internal number
    title = db.Column(db.String(500), nullable=False)
    organization_name = db.Column(db.String(500))
    bin = db.Column(db.String(20), index=True)  # BIN of investigated org
    basis = db.Column(db.Text)  # letter / order reference
    basis_date = db.Column(db.Date)
    requesting_body = db.Column(db.String(500))
    subject = db.Column(db.Text)
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    responsible_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    status = db.Column(db.String(50), default="open", index=True)
    # open | in_progress | review | report_ready | closed | archived
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    responsible = relationship("User", foreign_keys=[responsible_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    members = relationship("CaseMember", back_populates="case", cascade="all, delete-orphan")
    source_files = relationship("SourceFile", back_populates="case", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="case", cascade="all, delete-orphan")
    matches = relationship("ProductMatch", back_populates="case", cascade="all, delete-orphan")
    flags = relationship("AnalyticalFlag", back_populates="case", cascade="all, delete-orphan")
    reports = relationship("ReportVersion", back_populates="case", cascade="all, delete-orphan")
    relations = relationship("EntityRelation", back_populates="case", cascade="all, delete-orphan")
    procurements = relationship("ProcurementContract", back_populates="case", cascade="all, delete-orphan")

    def to_dict(self, include_details=False):
        data = {
            "id": self.id,
            "uuid": self.uuid,
            "number": self.number,
            "title": self.title,
            "organization_name": self.organization_name,
            "bin": self.bin,
            "basis": self.basis,
            "basis_date": self.basis_date.isoformat() if self.basis_date else None,
            "requesting_body": self.requesting_body,
            "subject": self.subject,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "responsible_id": self.responsible_id,
            "responsible_name": self.responsible.full_name if self.responsible else None,
            "status": self.status,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by_id": self.created_by_id,
        }
        if include_details:
            data["members"] = [m.to_dict() for m in self.members]
            data["files_count"] = len(self.source_files)
            data["invoices_count"] = len(self.invoices)
            data["flags_count"] = len(self.flags)
        return data


class CaseMember(db.Model):
    __tablename__ = "case_members"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role_in_case = db.Column(db.String(50), default="analyst")  # analyst, reviewer, viewer
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="members")
    user = relationship("User", back_populates="case_memberships")

    __table_args__ = (db.UniqueConstraint("case_id", "user_id", name="uq_case_user"),)

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else None,
            "role_in_case": self.role_in_case,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }
