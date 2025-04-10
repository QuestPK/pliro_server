from datetime import date
from typing import List

from sqlalchemy import String, Date, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    generalCategories: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True)
    itCategories: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=True)
    additionalNotes: Mapped[str] = mapped_column(String, nullable=True)
    regions: Mapped[str] = mapped_column(ARRAY(String), nullable=True)
    countries: Mapped[str] = mapped_column(ARRAY(String), nullable=True)
    file_path: Mapped[str] = mapped_column(String, nullable=True)
    approval_status: Mapped[str] = mapped_column(String, default="approved")

    revisions: Mapped[List["Revision"]] = relationship(
        "Revision",
        back_populates="standard",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"Standard(id={self.id!r}, name={self.name!r}, standardNumber={self.standardNumber!r})"

class Revision(Base):
    __tablename__ = "revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    standard_id: Mapped[int] = mapped_column(ForeignKey("standards.id", ondelete="CASCADE"), nullable=False)
    revision_number: Mapped[str] = mapped_column(String, nullable=False)
    revision_date: Mapped[str] = mapped_column(String, nullable=False)
    revision_description: Mapped[str] = mapped_column(Text, nullable=False)

    standard: Mapped["Standard"] = relationship("Standard", back_populates="revisions")

    def __repr__(self) -> str:
        return f"Revision(id={self.id!r}, standard_id={self.standard_id!r}, revision_number={self.revision_number!r})"