from app.services.resource_library.governance import governance_snapshot
from app.services.resource_library.taxonomy import ResourceCategoryService


def test_resource_category_seed_codes_are_unique():
    service = ResourceCategoryService()

    service.validate_unique_codes()
    rows = service.flatten()

    assert len(rows) == len({row["code"] for row in rows})
    assert rows[0]["code"] == "internal"


def test_resource_category_descendants_include_nested_children():
    service = ResourceCategoryService()

    descendants = service.descendants("external")

    assert "external" in descendants
    assert "external.project.case" in descendants
    assert "external.report.professional_analysis" in descendants


def test_resource_governance_dimensions_are_separate():
    options = governance_snapshot()

    assert "confidentiality" in options
    assert "copyright" in options
    assert "risk" in options
    assert "lifecycle" in options
    assert "public_domain" in options["copyright"]
    assert "public_domain" not in options["confidentiality"]
