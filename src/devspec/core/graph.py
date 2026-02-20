from collections import deque

from devspec.core.schema import Schema


class ArtifactGraph:
    def __init__(self, schema: Schema) -> None:
        self._ids = [a.id for a in schema.artifacts]
        self._deps: dict[str, list[str]] = {a.id: list(a.requires) for a in schema.artifacts}
        self._rdeps: dict[str, list[str]] = {aid: [] for aid in self._ids}
        for a in schema.artifacts:
            for req in a.requires:
                self._rdeps[req].append(a.id)

    def get_build_order(self) -> list[str]:
        """Kahn's algorithm topological sort. Returns artifact IDs in valid build order."""
        in_degree = {aid: len(self._deps[aid]) for aid in self._ids}
        queue = deque(aid for aid in self._ids if in_degree[aid] == 0)
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for dependent in self._rdeps[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        if len(order) != len(self._ids):
            raise ValueError("Cycle detected in artifact graph")
        return order

    def get_next_artifacts(self, completed: set[str]) -> list[str]:
        """Return artifact IDs that are ready (all deps satisfied, not yet completed)."""
        return [aid for aid in self._ids if aid not in completed and all(dep in completed for dep in self._deps[aid])]

    def get_blocked(self, completed: set[str]) -> list[str]:
        """Return artifact IDs that have unsatisfied deps and are not completed."""
        return [
            aid for aid in self._ids if aid not in completed and not all(dep in completed for dep in self._deps[aid])
        ]

    def get_status(self, completed: set[str]) -> dict[str, str]:
        """Return {artifact_id: "done"|"ready"|"blocked"} for all artifacts."""
        status: dict[str, str] = {}
        for aid in self._ids:
            if aid in completed:
                status[aid] = "done"
            elif all(dep in completed for dep in self._deps[aid]):
                status[aid] = "ready"
            else:
                status[aid] = "blocked"
        return status

    def is_complete(self, completed: set[str]) -> bool:
        """True if all artifacts are done."""
        return all(aid in completed for aid in self._ids)
