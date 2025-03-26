from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

class Standard(db.Model):
    __tablename__ = "standards"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)