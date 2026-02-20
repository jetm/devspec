import importlib.resources
from dataclasses import dataclass, field

import yaml


@dataclass
class Artifact:
    id: str
    generates: str
    description: str
    template: str
    instruction: str
    requires: list[str] = field(default_factory=list)


@dataclass
class ApplyConfig:
    requires: list[str]
    tracks: str
    instruction: str


@dataclass
class Schema:
    name: str
    version: int
    description: str
    artifacts: list[Artifact]
    apply: ApplyConfig


def load_schema() -> Schema:
    """Load the bundled schema.yaml from the data directory."""
    data_dir = importlib.resources.files("devspec.data")
    schema_text = (data_dir / "schema.yaml").read_text(encoding="utf-8")
    raw = yaml.safe_load(schema_text)
    return _parse_schema(raw)


def _parse_schema(raw: dict) -> Schema:
    artifacts = [
        Artifact(
            id=a["id"],
            generates=a["generates"],
            description=a["description"],
            template=a["template"],
            instruction=a["instruction"],
            requires=a.get("requires") or [],
        )
        for a in raw["artifacts"]
    ]
    apply_cfg = ApplyConfig(
        requires=raw["apply"]["requires"],
        tracks=raw["apply"]["tracks"],
        instruction=raw["apply"]["instruction"],
    )
    return Schema(
        name=raw["name"],
        version=raw["version"],
        description=raw["description"],
        artifacts=artifacts,
        apply=apply_cfg,
    )


def validate_schema(schema: Schema) -> None:
    """Validate artifact IDs are unique, requires references are valid, and no cycles exist."""
    ids = {a.id for a in schema.artifacts}

    # Check uniqueness
    if len(ids) != len(schema.artifacts):
        seen: set[str] = set()
        for a in schema.artifacts:
            if a.id in seen:
                raise ValueError(f"Duplicate artifact ID: {a.id}")
            seen.add(a.id)

    # Check all requires references are valid
    for a in schema.artifacts:
        for req in a.requires:
            if req not in ids:
                raise ValueError(f"Artifact '{a.id}' requires unknown artifact '{req}'")

    # Check apply requires
    for req in schema.apply.requires:
        if req not in ids:
            raise ValueError(f"Apply config requires unknown artifact '{req}'")

    # Check for cycles using DFS
    adj: dict[str, list[str]] = {a.id: a.requires for a in schema.artifacts}
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {aid: WHITE for aid in ids}

    def dfs(node: str) -> None:
        color[node] = GRAY
        for dep in adj[node]:
            if color[dep] == GRAY:
                raise ValueError(f"Cycle detected involving artifact '{dep}'")
            if color[dep] == WHITE:
                dfs(dep)
        color[node] = BLACK

    for aid in ids:
        if color[aid] == WHITE:
            dfs(aid)
