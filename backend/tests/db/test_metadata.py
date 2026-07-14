from sqlalchemy import create_engine

from app.db.base import Base
import app.db.models  # noqa: F401


EXPECTED_TABLES = {
    "organizations",
    "users",
    "projects",
    "project_members",
    "project_requirements",
    "resource_categories",
    "resource_category_links",
    "tags",
    "resource_tags",
    "documents",
    "document_versions",
    "document_files",
    "chunks",
    "resource_permissions",
    "document_governance",
    "ingestion_tasks",
    "vector_index_tasks",
    "online_collection_tasks",
    "workflow_runs",
    "agent_runs",
    "agent_run_steps",
    "agent_evidence",
    "reviews",
    "artifacts",
    "artifact_versions",
    "artifact_dependencies",
    "prompt_templates",
    "platform_profiles",
    "intelligence_items",
}


def test_postgres_v2_metadata_declares_required_tables():
    assert EXPECTED_TABLES.issubset(set(Base.metadata.tables))


def test_metadata_can_create_all_on_empty_database():
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    assert len(Base.metadata.tables) >= len(EXPECTED_TABLES)


def test_chunks_keep_required_compatible_fields():
    chunk_columns = set(Base.metadata.tables["chunks"].columns.keys())

    assert {
        "chunk_id",
        "source_id",
        "chunk_index",
        "section_path",
        "content",
        "modality",
        "parser",
        "page_number",
        "asset_path",
        "asset_mime_type",
        "embedding_modality",
        "created_at",
    }.issubset(chunk_columns)


def test_chroma_id_can_use_chunk_primary_key_string():
    chunk_table = Base.metadata.tables["chunks"]

    assert chunk_table.c.id.primary_key
    assert chunk_table.c.id.type.length == 36
