from integration.topology_selection import edge_indices_json, extract_edges, select_nearest_edge_index


def test_extract_edges_and_select_nearest_index():
    result = {
        "result": {
            "edges": [
                {"index": 0, "kind": "edge", "center": {"x": 0.2, "y": 0.2, "z": 0.2}},
                {"index": 7, "kind": "edge", "center": {"x": 0.0, "y": 0.07, "z": 0.04}},
                {"index": 9, "kind": "edge", "center": {"x": 0.5, "y": 0.5, "z": 0.5}},
            ]
        }
    }
    edges = extract_edges(result)
    assert {edge["index"] for edge in edges} == {0, 7, 9}
    assert select_nearest_edge_index(result, (0.0, 0.07, 0.04)) == 7
    assert edge_indices_json(7) == "[7]"
