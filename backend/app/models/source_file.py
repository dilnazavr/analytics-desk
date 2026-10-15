from app import db
from datetime import datetime
from sqlalchemy.orm import relationship
import uuid
import hashlib


class SourceFile(db.Model):
    __tablename__ = "source_files"

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    original_filename = db.Column(db.String(500), nullable=False)
    stored_filename = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(1000), nullable=False)
    file_size = db.Column(db.BigInteger)
    mime_type = db.Column(db.String(100))
    file_hash = db.Column(db.String(64))  # SHA-256
    data_type = db.Column(db.String(50), default="esf")  # esf, company, procurement, other
    source_description = db.Column(db.String(500))
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="uploaded")  # uploaded, processing, processed, error

    case = relationship("Case", back_populates="source_files")
    uploaded_by = relationship("User")
    import_jobs = relationship("ImportJob", back_populates="source_file", cascade="all, delete-orphan")

    def compute_hash(self, file_content: bytes):
        self.file_hash = hashlib.sha256(file_content).hexdigest()

    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "case_id": self.case_id,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "file_hash": self.file_hash,
            "data_type": self.data_type,
            "source_description": self.source_description,
            "uploaded_by_id": self.uploaded_by_id,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "status": self.status,
        }


class ImportJob(db.Model):
    __tablename__ = "import_jobs"

    id = db.Column(db.Integer, primary_key=True)
    source_file_id = db.Column(db.Integer, db.ForeignKey("source_files.id"), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    status = db.Column(db.String(50), default="pending")  # pending, running, completed, failed
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    total_rows = db.Column(db.Integer, default=0)
    success_rows = db.Column(db.Integer, default=0)
    error_rows = db.Column(db.Integer, default=0)
    duplicate_rows = db.Column(db.Integer, default=0)
    column_mapping = db.Column(db.JSON)
    error_report = db.Column(db.JSON)
    result_summary = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    source_file = relationship("SourceFile", back_populates="import_jobs")
    case = relationship("Case")

    def to_dict(self):
        return {
            "id": self.id,
            "source_file_id": self.source_file_id,
            "case_id": self.case_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "total_rows": self.total_rows,
            "success_rows": self.success_rows,
            "error_rows": self.error_rows,
            "duplicate_rows": self.duplicate_rows,
            "column_mapping": self.column_mapping,
            "error_report": self.error_report,
            "result_summary": self.result_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
