from app import db
from datetime import datetime
from sqlalchemy.orm import relationship


class ProcurementContract(db.Model):
    __tablename__ = "procurement_contracts"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    procurement_number = db.Column(db.String(100))
    contract_number = db.Column(db.String(100))
    contract_date = db.Column(db.Date)
    customer_name = db.Column(db.String(500))
    customer_bin = db.Column(db.String(12), index=True)
    supplier_name = db.Column(db.String(500))
    supplier_bin = db.Column(db.String(12), index=True)
    subject = db.Column(db.Text)
    amount = db.Column(db.Numeric(18, 2))
    status = db.Column(db.String(50))
    execution_period = db.Column(db.String(255))
    source_url = db.Column(db.String(1000))
    source_file_id = db.Column(db.Integer, db.ForeignKey("source_files.id"))
    data_obtained_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="procurements")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "procurement_number": self.procurement_number,
            "contract_number": self.contract_number,
            "contract_date": self.contract_date.isoformat() if self.contract_date else None,
            "customer_name": self.customer_name,
            "customer_bin": self.customer_bin,
            "supplier_name": self.supplier_name,
            "supplier_bin": self.supplier_bin,
            "subject": self.subject,
            "amount": float(self.amount) if self.amount is not None else None,
            "status": self.status,
            "execution_period": self.execution_period,
            "source_url": self.source_url,
            "data_obtained_at": self.data_obtained_at.isoformat() if self.data_obtained_at else None,
        }
