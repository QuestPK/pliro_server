import enum
from sqlalchemy import ForeignKey, Enum, Column
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base

from app.models.base import Base


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class MemberRole(enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"

class MemberStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    use: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    product_type: Mapped[str] = mapped_column(String, nullable=False)
    product_category: Mapped[str] = mapped_column(String, nullable=False)

    dimensions: Mapped[str] = mapped_column(String, nullable=True)
    weight: Mapped[str] = mapped_column(String, nullable=True)

    regions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    countries: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)

    technical_details: Mapped[dict] = mapped_column(JSONB, nullable=True)
    standard_mapping: Mapped[dict] = mapped_column(JSONB, nullable=True)

    multi_variant: Mapped[bool] = mapped_column(Boolean, default=False)
    pre_certified_components: Mapped[bool] = mapped_column(Boolean, default=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    invitations = relationship("ProjectInvitations", back_populates="project")
    members = relationship("Members", back_populates="project")


    def __repr__(self) -> str:
        return f"Project(id={self.id}, name={self.name}, description={self.description}, user_id={self.user_id})"


class ProjectInvitations(Base):
    __tablename__ = "project_invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(Enum(InvitationStatus), nullable=False)

    project = relationship("ProjectModel", back_populates="invitations")


class Members(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[MemberRole] = mapped_column(Enum(MemberRole), nullable=False)
    status: Mapped[MemberStatus] = mapped_column(Enum(MemberStatus), nullable=False)

    project = relationship("ProjectModel", back_populates="members")