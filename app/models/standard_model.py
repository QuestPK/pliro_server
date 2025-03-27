from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Standard(Base):
    __tablename__ = "standards"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"Standard(id={self.id!r}, name={self.name!r}, description={self.description!r})"