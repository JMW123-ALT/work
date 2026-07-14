from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


class Organization(IdMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    projects: Mapped[list["Project"]] = relationship(back_populates="organization")


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")

    organization: Mapped[Organization] = relationship(back_populates="users")

    __table_args__ = (
        UniqueConstraint("organization_id", "username", name="uq_users_org_username"),
    )


class Project(IdMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")

    organization: Mapped[Organization] = relationship(back_populates="projects")

    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_projects_org_code"),
    )


class ProjectMember(IdMixin, TimestampMixin, Base):
    __tablename__ = "project_members"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", "role", name="uq_project_member_role"),
    )


class ProjectRequirement(IdMixin, TimestampMixin, Base):
    __tablename__ = "project_requirements"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "title",
            "version",
            name="uq_project_requirement_version",
        ),
    )
