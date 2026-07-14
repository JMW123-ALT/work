"""002 resource taxonomy

Revision ID: 002_resource_taxonomy
Revises: 001_organizations_projects
Create Date: 2026-07-14
"""

from alembic import context, op
from sqlalchemy import select

from app.db.base import Base
import app.db.models  # noqa: F401

revision = "002_resource_taxonomy"
down_revision = "001_organizations_projects"
branch_labels = None
depends_on = None

TABLES = ["resource_categories", "tags"]

CATEGORY_ROWS = [
    ("00000000-0000-4000-8000-000000000001", None, "internal", "公司内部资料", 1),
    (
        "00000000-0000-4000-8000-000000000002",
        "00000000-0000-4000-8000-000000000001",
        "internal.project.completed",
        "已完成项目资料",
        1,
    ),
    (
        "00000000-0000-4000-8000-000000000003",
        "00000000-0000-4000-8000-000000000001",
        "internal.project.in_progress",
        "正在进行项目资料",
        2,
    ),
    (
        "00000000-0000-4000-8000-000000000004",
        "00000000-0000-4000-8000-000000000001",
        "internal.operation.feedback",
        "运营端反馈实施数据",
        3,
    ),
    ("00000000-0000-4000-8000-000000000005", None, "external", "外部收集资料", 2),
    (
        "00000000-0000-4000-8000-000000000006",
        "00000000-0000-4000-8000-000000000005",
        "external.project.case",
        "其他项目资料",
        1,
    ),
    (
        "00000000-0000-4000-8000-000000000007",
        "00000000-0000-4000-8000-000000000005",
        "external.report.comprehensive",
        "文件信息综合报告",
        2,
    ),
    (
        "00000000-0000-4000-8000-000000000008",
        "00000000-0000-4000-8000-000000000005",
        "external.report.professional_analysis",
        "专项专业分析报告",
        3,
    ),
    (
        "00000000-0000-4000-8000-000000000009",
        None,
        "confidential",
        "特殊平台保密资料",
        3,
    ),
    (
        "00000000-0000-4000-8000-000000000010",
        "00000000-0000-4000-8000-000000000009",
        "confidential.authorized.government",
        "政府授权项目数据",
        1,
    ),
    (
        "00000000-0000-4000-8000-000000000011",
        "00000000-0000-4000-8000-000000000009",
        "confidential.authorized.group",
        "集团公司授权项目数据",
        2,
    ),
    (
        "00000000-0000-4000-8000-000000000012",
        "00000000-0000-4000-8000-000000000009",
        "confidential.report.project_analysis",
        "项目分析专项报告",
        3,
    ),
    (
        "00000000-0000-4000-8000-000000000013",
        "00000000-0000-4000-8000-000000000009",
        "confidential.report.multi_role_review",
        "多角色复核报告",
        4,
    ),
    ("00000000-0000-4000-8000-000000000014", None, "other", "其他资料", 4),
    (
        "00000000-0000-4000-8000-000000000015",
        "00000000-0000-4000-8000-000000000014",
        "other.policy.current",
        "当前版本政策文件",
        1,
    ),
    (
        "00000000-0000-4000-8000-000000000016",
        "00000000-0000-4000-8000-000000000014",
        "other.cross_industry.creativity",
        "跨行业前瞻创意",
        2,
    ),
    (
        "00000000-0000-4000-8000-000000000017",
        "00000000-0000-4000-8000-000000000014",
        "other.cross_industry.design",
        "跨行业设计案例",
        3,
    ),
    (
        "00000000-0000-4000-8000-000000000018",
        "00000000-0000-4000-8000-000000000014",
        "other.cross_industry.story",
        "跨行业故事案例",
        4,
    ),
]


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in TABLES:
        Base.metadata.tables[table_name].create(bind, checkfirst=True)

    categories = Base.metadata.tables["resource_categories"]
    existing_codes = set()
    if not context.is_offline_mode():
        existing_codes = set(bind.execute(select(categories.c.code)).scalars().all())
    rows = [
        {
            "id": row_id,
            "parent_id": parent_id,
            "code": code,
            "name": name,
            "description": "",
            "sort_order": sort_order,
            "is_active": True,
        }
        for row_id, parent_id, code, name, sort_order in CATEGORY_ROWS
        if code not in existing_codes
    ]
    if rows:
        op.bulk_insert(categories, rows)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(TABLES):
        Base.metadata.tables[table_name].drop(bind, checkfirst=True)
