import pytest

from devspec.core.schema import ApplyConfig, Artifact, Schema, load_schema, validate_schema


def test_load_schema():
    schema = load_schema()
    assert schema.name == "spec-driven-custom"
    assert schema.version == 1
    assert len(schema.artifacts) == 4
    ids = [a.id for a in schema.artifacts]
    assert ids == ["proposal", "specs", "design", "tasks"]


def test_load_schema_artifacts_have_fields():
    schema = load_schema()
    proposal = schema.artifacts[0]
    assert proposal.id == "proposal"
    assert proposal.generates == "proposal.md"
    assert proposal.template == "proposal.md"
    assert proposal.requires == []
    assert proposal.description != ""
    assert proposal.instruction != ""


def test_load_schema_requires():
    schema = load_schema()
    by_id = {a.id: a for a in schema.artifacts}
    assert by_id["specs"].requires == ["proposal"]
    assert by_id["design"].requires == ["proposal"]
    assert by_id["tasks"].requires == ["specs", "design"]


def test_load_schema_apply():
    schema = load_schema()
    assert schema.apply.requires == ["tasks"]
    assert schema.apply.tracks == "tasks.md"


def test_validate_schema_valid():
    schema = load_schema()
    validate_schema(schema)  # Should not raise


def test_validate_schema_duplicate_id():
    schema = Schema(
        name="test",
        version=1,
        description="test",
        artifacts=[
            Artifact(id="a", generates="a.md", description="", template="", instruction=""),
            Artifact(id="a", generates="b.md", description="", template="", instruction=""),
        ],
        apply=ApplyConfig(requires=[], tracks="", instruction=""),
    )
    with pytest.raises(ValueError, match="Duplicate artifact ID"):
        validate_schema(schema)


def test_validate_schema_invalid_requires():
    schema = Schema(
        name="test",
        version=1,
        description="test",
        artifacts=[
            Artifact(id="a", generates="a.md", description="", template="", instruction="", requires=["nonexistent"]),
        ],
        apply=ApplyConfig(requires=[], tracks="", instruction=""),
    )
    with pytest.raises(ValueError, match="unknown artifact 'nonexistent'"):
        validate_schema(schema)


def test_validate_schema_invalid_apply_requires():
    schema = Schema(
        name="test",
        version=1,
        description="test",
        artifacts=[
            Artifact(id="a", generates="a.md", description="", template="", instruction=""),
        ],
        apply=ApplyConfig(requires=["missing"], tracks="", instruction=""),
    )
    with pytest.raises(ValueError, match="unknown artifact 'missing'"):
        validate_schema(schema)


def test_validate_schema_cycle():
    schema = Schema(
        name="test",
        version=1,
        description="test",
        artifacts=[
            Artifact(id="a", generates="a.md", description="", template="", instruction="", requires=["b"]),
            Artifact(id="b", generates="b.md", description="", template="", instruction="", requires=["a"]),
        ],
        apply=ApplyConfig(requires=[], tracks="", instruction=""),
    )
    with pytest.raises(ValueError, match="Cycle detected"):
        validate_schema(schema)


def test_validate_schema_self_cycle():
    schema = Schema(
        name="test",
        version=1,
        description="test",
        artifacts=[
            Artifact(id="a", generates="a.md", description="", template="", instruction="", requires=["a"]),
        ],
        apply=ApplyConfig(requires=[], tracks="", instruction=""),
    )
    with pytest.raises(ValueError, match="Cycle detected"):
        validate_schema(schema)
