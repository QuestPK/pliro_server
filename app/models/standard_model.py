from datetime import date
from typing import List

from sqlalchemy import String, Date, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Standard(Base):
    __tablename__ = "standards"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    issuingOrganization: Mapped[str] = mapped_column(String, nullable=True)
    standardNumber: Mapped[str] = mapped_column(String, nullable=True)
    version: Mapped[str] = mapped_column(String, nullable=True)
    standardOwner: Mapped[str] = mapped_column(String, nullable=True)
    standardWebsite: Mapped[str] = mapped_column(String, nullable=True)
    issueDate: Mapped[date] = mapped_column(Date, nullable=True)
    effectiveDate: Mapped[date] = mapped_column(Date, nullable=True)
    revisions: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True)
    generalCategories: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True)
    itCategories: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True)
    additionalNotes: Mapped[str] = mapped_column(String, nullable=True)
    file_path: Mapped[str] = mapped_column(String, nullable=True)
    approval_status: Mapped[str] = mapped_column(String, default="approved")

    def __repr__(self) -> str:
        return f"Standard(id={self.id!r}, name={self.name!r}, standardNumber={self.standardNumber!r})"