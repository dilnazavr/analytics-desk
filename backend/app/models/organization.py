from app import db
from datetime import datetime
from sqlalchemy.orm import relationship


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    bin = db.Column(db.String(20), unique=True, index=True)
    name = db.Column(db.String(500), nullable=False)
    short_name = db.Column(db.String(255))
    address = db.Column(db.Text)
    status = db.Column(db.String(50))
    source = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "bin": self.bin,
            "name": self.name,
            "short_name": self.short_name,
            "address": self.address,
            "status": self.status,
            "source": self.source,
        }


class Person(db.Model):
    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True)
    iin = db.Column(db.String(20), unique=True, index=True)
    full_name = db.Column(db.String(500), nullable=False)
    birth_date = db.Column(db.Date)
    source = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "iin": self.iin,
            "full_name": self.full_name,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "source": self.source,
        }
