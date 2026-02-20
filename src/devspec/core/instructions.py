import importlib.resources
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from devspec.core.schema import load_schema


@dataclass
class InstructionBundle:
    artifact_id: str
    template: str
    instruction: str
    output_path: str
    dependencies: dict[str, str] = field(default_factory=dict)
    context: str = ""
    rules: list[str] = field(default_factory=list)


def generate_instructions(
    project_root: Path,
    artifact_id: str,
    change_name: str,
) -> InstructionBundle:
    """Generate enriched instructions for creating an artifact."""
    schema = load_schema()

    # Find artifact by id
    artifact = None
    for a in schema.artifacts:
        if a.id == artifact_id:
            artifact = a
            break
    if artifact is None:
        raise ValueError(f"Unknown artifact: {artifact_id}")

    # Read template from bundled data
    data_dir = importlib.resources.files("devspec.data")
    template = (data_dir / "templates" / artifact.template).read_text(encoding="utf-8")

    # Determine output path
    generates = artifact.generates
    if "*" in generates:
        # For glob patterns like specs/**/*.md, output path is the base directory
        output_path = generates.split("*")[0]
    else:
        output_path = generates

    # Load config.yaml for context and rules
    context = ""
    rules: list[str] = []
    config_path = project_root / "openspec" / "config.yaml"
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        context = raw.get("context", "")
        artifact_rules = raw.get("rules", {})
        if artifact_id in artifact_rules:
            rules = artifact_rules[artifact_id]

    # Read dependency content from change directory
    change_dir = project_root / "openspec" / "changes" / change_name
    dependencies: dict[str, str] = {}
    for req_id in artifact.requires:
        # Find the required artifact to get its generates path
        for a in schema.artifacts:
            if a.id == req_id:
                dep_path = change_dir / a.generates
                if "*" not in a.generates and dep_path.exists():
                    dependencies[req_id] = dep_path.read_text(encoding="utf-8")
                elif "*" in a.generates:
                    # For glob patterns, concatenate all matching files
                    parts = []
                    for f in sorted(change_dir.glob(a.generates)):
                        parts.append(f.read_text(encoding="utf-8"))
                    if parts:
                        dependencies[req_id] = "\n---\n".join(parts)
                break

    return InstructionBundle(
        artifact_id=artifact_id,
        template=template,
        instruction=artifact.instruction,
        output_path=output_path,
        dependencies=dependencies,
        context=context,
        rules=rules,
    )
