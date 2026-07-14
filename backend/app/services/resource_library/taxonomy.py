"""Resource category seed tree and traversal helpers.

The Prompt requires categories to become dynamic PostgreSQL rows later.  This
module keeps the first-stage seed tree in one place so migrations, APIs, and
tests can share the same source of truth without hard-coding business enums.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResourceCategorySeed:
    code: str
    name: str
    children: tuple["ResourceCategorySeed", ...] = field(default_factory=tuple)


CATEGORY_SEED: tuple[ResourceCategorySeed, ...] = (
    ResourceCategorySeed(
        code="internal",
        name="公司内部资料",
        children=(
            ResourceCategorySeed("internal.project.completed", "已完成项目资料"),
            ResourceCategorySeed("internal.project.in_progress", "正在进行项目资料"),
            ResourceCategorySeed("internal.operation.feedback", "运营端反馈实施数据"),
        ),
    ),
    ResourceCategorySeed(
        code="external",
        name="外部收集资料",
        children=(
            ResourceCategorySeed("external.project.case", "其他项目资料"),
            ResourceCategorySeed(
                "external.report.comprehensive",
                "文件信息综合报告",
            ),
            ResourceCategorySeed(
                "external.report.professional_analysis",
                "专项专业分析报告",
            ),
        ),
    ),
    ResourceCategorySeed(
        code="confidential",
        name="特殊平台保密资料",
        children=(
            ResourceCategorySeed(
                "confidential.authorized.government",
                "政府授权项目数据",
            ),
            ResourceCategorySeed("confidential.authorized.group", "集团公司授权项目数据"),
            ResourceCategorySeed(
                "confidential.report.project_analysis",
                "项目分析专项报告",
            ),
            ResourceCategorySeed(
                "confidential.report.multi_role_review",
                "多角色复核报告",
            ),
        ),
    ),
    ResourceCategorySeed(
        code="other",
        name="其他资料",
        children=(
            ResourceCategorySeed("other.policy.current", "当前版本政策文件"),
            ResourceCategorySeed("other.cross_industry.creativity", "跨行业前瞻创意"),
            ResourceCategorySeed("other.cross_industry.design", "跨行业设计案例"),
            ResourceCategorySeed("other.cross_industry.story", "跨行业故事案例"),
        ),
    ),
)


class ResourceCategoryService:
    def __init__(
        self,
        roots: tuple[ResourceCategorySeed, ...] = CATEGORY_SEED,
    ) -> None:
        self.roots = roots

    def flatten(self) -> list[dict]:
        rows: list[dict] = []

        def visit(
            node: ResourceCategorySeed,
            parent_code: str | None,
            depth: int,
            sort_order: int,
        ) -> None:
            rows.append(
                {
                    "code": node.code,
                    "name": node.name,
                    "parent_code": parent_code,
                    "depth": depth,
                    "sort_order": sort_order,
                    "is_active": True,
                }
            )
            for child_index, child in enumerate(node.children, start=1):
                visit(child, node.code, depth + 1, child_index)

        for index, root in enumerate(self.roots, start=1):
            visit(root, None, 0, index)
        return rows

    def descendants(self, code: str, include_self: bool = True) -> list[str]:
        codes: list[str] = []

        def visit(node: ResourceCategorySeed) -> bool:
            found = node.code == code
            child_matches = []
            for child in node.children:
                if visit(child):
                    child_matches.append(child.code)
                    found = True
            if node.code == code:
                if include_self:
                    codes.append(node.code)
                self._collect_child_codes(node, codes)
            return found

        for root in self.roots:
            visit(root)
        return codes

    def validate_unique_codes(self) -> None:
        codes = [row["code"] for row in self.flatten()]
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        if duplicates:
            raise ValueError(f"duplicate category codes: {', '.join(duplicates)}")

    def _collect_child_codes(
        self,
        node: ResourceCategorySeed,
        output: list[str],
    ) -> None:
        for child in node.children:
            output.append(child.code)
            self._collect_child_codes(child, output)
