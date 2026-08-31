from pathlib import Path

from integration.capability_census_v1 import census_from_repository, discover_legacy_server


def test_capability_census_is_static_and_discovers_backend_discriminators():
    root = Path(__file__).resolve().parents[1]
    report = census_from_repository(root)
    assert report["schema"] == "solid-ai.capability-census.v1"
    assert report["policy"]["discovery_is_not_proof"] is True
    assert report["policy"]["promotion_requires_live_evidence"] is True
    assert report["counts"]["total_discovered"] > 0

    ids = {item["capability_id"] for item in report["records"]}
    assert "part.extrude_boss" in ids
    assert "edge.fillet" in ids
    assert "sketch.circle" in ids


def test_discovery_does_not_execute_server_code(tmp_path):
    source = tmp_path / "server.py"
    source.write_text(
        "from typing import Literal\n"
        "def explode(value: Literal['danger']):\n"
        "    raise RuntimeError('must not execute')\n",
        encoding="utf-8",
    )
    records = discover_legacy_server(source)
    assert len(records) == 1
    assert records[0].status == "candidate"
    assert records[0].backend_tools == ("explode",)
