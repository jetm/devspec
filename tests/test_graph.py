from devspec.core.graph import ArtifactGraph
from devspec.core.schema import ApplyConfig, Artifact, Schema, load_schema


def _make_schema(artifacts: list[Artifact]) -> Schema:
    return Schema(
        name="test",
        version=1,
        description="test",
        artifacts=artifacts,
        apply=ApplyConfig(requires=[], tracks="", instruction=""),
    )


class TestBuildOrder:
    def test_real_schema(self):
        graph = ArtifactGraph(load_schema())
        order = graph.get_build_order()
        idx = {aid: i for i, aid in enumerate(order)}
        # proposal must come before specs and design
        assert idx["proposal"] < idx["specs"]
        assert idx["proposal"] < idx["design"]
        # specs and design must come before tasks
        assert idx["specs"] < idx["tasks"]
        assert idx["design"] < idx["tasks"]

    def test_linear_chain(self):
        schema = _make_schema(
            [
                Artifact(id="a", generates="", description="", template="", instruction=""),
                Artifact(id="b", generates="", description="", template="", instruction="", requires=["a"]),
                Artifact(id="c", generates="", description="", template="", instruction="", requires=["b"]),
            ]
        )
        order = ArtifactGraph(schema).get_build_order()
        assert order == ["a", "b", "c"]

    def test_independent(self):
        schema = _make_schema(
            [
                Artifact(id="a", generates="", description="", template="", instruction=""),
                Artifact(id="b", generates="", description="", template="", instruction=""),
            ]
        )
        order = ArtifactGraph(schema).get_build_order()
        assert set(order) == {"a", "b"}


class TestNextArtifacts:
    def test_initial_state(self):
        graph = ArtifactGraph(load_schema())
        ready = graph.get_next_artifacts(set())
        assert ready == ["proposal"]

    def test_after_proposal(self):
        graph = ArtifactGraph(load_schema())
        ready = graph.get_next_artifacts({"proposal"})
        assert set(ready) == {"specs", "design"}

    def test_after_specs_and_design(self):
        graph = ArtifactGraph(load_schema())
        ready = graph.get_next_artifacts({"proposal", "specs", "design"})
        assert ready == ["tasks"]

    def test_all_done(self):
        graph = ArtifactGraph(load_schema())
        ready = graph.get_next_artifacts({"proposal", "specs", "design", "tasks"})
        assert ready == []


class TestBlocked:
    def test_initial_state(self):
        graph = ArtifactGraph(load_schema())
        blocked = graph.get_blocked(set())
        assert set(blocked) == {"specs", "design", "tasks"}

    def test_after_proposal(self):
        graph = ArtifactGraph(load_schema())
        blocked = graph.get_blocked({"proposal"})
        assert blocked == ["tasks"]


class TestStatus:
    def test_initial(self):
        graph = ArtifactGraph(load_schema())
        status = graph.get_status(set())
        assert status == {
            "proposal": "ready",
            "specs": "blocked",
            "design": "blocked",
            "tasks": "blocked",
        }

    def test_partial(self):
        graph = ArtifactGraph(load_schema())
        status = graph.get_status({"proposal", "specs"})
        assert status == {
            "proposal": "done",
            "specs": "done",
            "design": "ready",
            "tasks": "blocked",
        }

    def test_all_done(self):
        graph = ArtifactGraph(load_schema())
        status = graph.get_status({"proposal", "specs", "design", "tasks"})
        assert all(v == "done" for v in status.values())


class TestIsComplete:
    def test_not_complete(self):
        graph = ArtifactGraph(load_schema())
        assert not graph.is_complete(set())
        assert not graph.is_complete({"proposal", "specs", "design"})

    def test_complete(self):
        graph = ArtifactGraph(load_schema())
        assert graph.is_complete({"proposal", "specs", "design", "tasks"})
