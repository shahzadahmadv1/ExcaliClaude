#!/usr/bin/env python3
"""Validate .excalidraw file structure without rendering."""

import json
import sys
from pathlib import Path

ORDER_KEY_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

MAX_NODE_WARNING_THRESHOLD = 15
EDGE_WARNING_DENSITY = 1.35
MAX_READABLE_EDGE_DEGREE = 5
MAX_READABLE_OVERLOADED_NODES = 3
VALID_OVERVIEW_STYLES = {"auto", "pure-layers", "core-with-sides"}
VALID_GROUP_PLACEMENTS = {"layer", "side-left", "side-right"}
HYBRID_OVERVIEW_KINDS = {"architecture", "container", "context"}

VALID_VIEW_MODES = {"overview", "focused-flow", "drill-down", "scenario-pack"}
VALID_EVIDENCE_SOURCES = {"code", "inferred", "user-specified"}
VALID_CONFIDENCE_LEVELS = {"high", "medium", "low"}


def get_integer_length(head: str) -> int:
    if "a" <= head <= "z":
        return ord(head) - ord("a") + 2
    if "A" <= head <= "Z":
        return ord("Z") - ord(head) + 2
    raise ValueError(f"invalid order key head: {head}")


def get_integer_part(key: str) -> str:
    integer_part_length = get_integer_length(key[0])
    if integer_part_length > len(key):
        raise ValueError(f"invalid order key: {key}")
    return key[:integer_part_length]


def validate_order_key(key: str, digits: str = ORDER_KEY_DIGITS) -> None:
    if not key:
        raise ValueError("invalid order key: <empty>")
    if key == "A" + (digits[0] * 26):
        raise ValueError(f"invalid order key: {key}")

    integer_part = get_integer_part(key)
    fractional_part = key[len(integer_part):]
    if fractional_part.endswith(digits[0]):
        raise ValueError(f"invalid order key: {key}")


def readability_metrics(node_ids: set[str], edges: list[dict]) -> dict[str, float]:
    degree: dict[str, int] = {}
    for edge in edges:
        source_id = edge.get("from")
        target_id = edge.get("to")
        if source_id in node_ids:
            degree[source_id] = degree.get(source_id, 0) + 1
        if target_id in node_ids and target_id != source_id:
            degree[target_id] = degree.get(target_id, 0) + 1

    node_count = len(node_ids)
    edge_count = len(edges)
    max_degree = max(degree.values(), default=0)
    overloaded_nodes = sum(1 for value in degree.values() if value >= MAX_READABLE_EDGE_DEGREE)
    edge_density = edge_count / max(node_count, 1)
    edge_limit = max(int(node_count * 1.5), node_count + 4, MAX_NODE_WARNING_THRESHOLD + 4)
    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "edge_density": edge_density,
        "max_degree": max_degree,
        "overloaded_nodes": overloaded_nodes,
        "edge_limit": edge_limit,
    }


def readability_warnings(scope_label: str, node_ids: set[str], edges: list[dict]) -> list[str]:
    metrics = readability_metrics(node_ids, edges)
    warnings: list[str] = []

    if metrics["edge_count"] > metrics["edge_limit"]:
        warnings.append(
            f"{scope_label}: relationship count ({metrics['edge_count']}) is high for "
            f"{metrics['node_count']} nodes; consider splitting or simplifying the view"
        )
    if metrics["edge_density"] >= EDGE_WARNING_DENSITY:
        warnings.append(
            f"{scope_label}: connector density ({metrics['edge_density']:.2f} edges/node) "
            "may cause overlapping routes"
        )
    if metrics["max_degree"] > MAX_READABLE_EDGE_DEGREE:
        warnings.append(
            f"{scope_label}: max node degree ({metrics['max_degree']}) is high; "
            "consider a drill-down or scenario-pack view"
        )
    if metrics["overloaded_nodes"] > MAX_READABLE_OVERLOADED_NODES:
        warnings.append(
            f"{scope_label}: {metrics['overloaded_nodes']} nodes have degree >= "
            f"{MAX_READABLE_EDGE_DEGREE}; connectors may become unreadable"
        )
    return warnings


def normalize_overview_style(value: str | None) -> str:
    if value is None:
        return "auto"
    return value if value in VALID_OVERVIEW_STYLES else "<invalid>"


def normalize_group_placement(value: str | None) -> str:
    if value is None:
        return "layer"
    return value if value in VALID_GROUP_PLACEMENTS else "<invalid>"


def overview_layout_warning(
    scope_label: str,
    view: dict,
    selected_entities: list[dict],
) -> list[str]:
    warnings: list[str] = []
    if view.get("layout") != "layers":
        return warnings
    if view.get("view_mode") != "overview":
        return warnings
    if view.get("diagram_kind") not in HYBRID_OVERVIEW_KINDS:
        return warnings

    overview_style = normalize_overview_style(view.get("overview_style"))
    if overview_style == "<invalid>":
        warnings.append(
            f"{scope_label}: overview_style '{view.get('overview_style')}' is invalid; "
            f"use one of {VALID_OVERVIEW_STYLES}"
        )
        return warnings

    explicit_side_groups = sum(
        1 for group in view.get("groups", [])
        if isinstance(group, dict) and normalize_group_placement(group.get("placement")) in {"side-left", "side-right"}
    )
    external_count = sum(
        1 for entity in selected_entities
        if entity.get("boundary") == "external" or entity.get("role") == "external"
    )
    messaging_count = sum(
        1 for entity in selected_entities
        if entity.get("role") in {"queue", "topic"}
    )

    if overview_style == "pure-layers" and explicit_side_groups:
        warnings.append(
            f"{scope_label}: pure-layers conflicts with side-placed groups; the builder will favor side placement"
        )

    if overview_style in {"auto", "pure-layers"} and (external_count >= 2 or messaging_count >= 1) and explicit_side_groups == 0:
        warnings.append(
            f"{scope_label}: consider overview_style 'core-with-sides' so external systems and messaging do not consume full-width layers"
        )

    return warnings


def validate(filepath: str) -> list[str]:
    """Return list of validation errors. Empty list = valid."""
    errors = []
    path = Path(filepath)

    if not path.exists():
        return [f"File not found: {filepath}"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # Top-level structure
    if data.get("type") != "excalidraw":
        errors.append('Missing or wrong "type" (expected "excalidraw")')
    if data.get("version") != 2:
        errors.append('Missing or wrong "version" (expected 2)')
    if not isinstance(data.get("elements"), list):
        errors.append('"elements" must be an array')
    if not isinstance(data.get("appState"), dict):
        errors.append('"appState" must be an object')
    if not isinstance(data.get("files"), dict):
        errors.append('"files" must be an object')

    elements = data.get("elements", [])
    element_ids = set()
    element_map = {e.get("id"): e for e in elements if isinstance(e, dict)}

    required_props = ["id", "type", "x", "y", "width", "height", "version", "seed", "index"]
    seen_indexes = set()
    last_index = None

    for i, elem in enumerate(elements):
        if not isinstance(elem, dict):
            errors.append(f"Element {i}: not an object")
            continue

        eid = elem.get("id", f"<index {i}>")

        # Required properties
        for prop in required_props:
            if prop not in elem:
                errors.append(f"Element {eid}: missing required property '{prop}'")

        # Duplicate IDs
        if elem.get("id") in element_ids:
            errors.append(f"Element {eid}: duplicate ID")
        element_ids.add(elem.get("id"))

        # Excalidraw relies on lexicographically ordered z-indices.
        index = elem.get("index")
        if isinstance(index, str):
            try:
                validate_order_key(index)
            except ValueError as exc:
                errors.append(f"Element {eid}: {exc}")
            if index in seen_indexes:
                errors.append(f"Element {eid}: duplicate index '{index}'")
            seen_indexes.add(index)
            if last_index is not None and index <= last_index:
                errors.append(
                    f"Element {eid}: index '{index}' is not greater than previous index '{last_index}'"
                )
            last_index = index

        # Arrow-specific checks
        if elem.get("type") == "arrow":
            points = elem.get("points")
            if not isinstance(points, list) or len(points) < 2:
                errors.append(f"Arrow {eid}: 'points' must be array with 2+ items")
            elif points:
                for j, pt in enumerate(points):
                    if not isinstance(pt, list) or len(pt) != 2:
                        errors.append(f"Arrow {eid}: point {j} must be [x, y]")

        # Text container binding check
        if elem.get("type") == "text" and elem.get("containerId"):
            cid = elem["containerId"]
            container = element_map.get(cid)
            if not container:
                errors.append(f"Text {eid}: containerId '{cid}' references non-existent element")
            elif container:
                bound = container.get("boundElements", [])
                bound_ids = [b.get("id") for b in bound if isinstance(b, dict)]
                if elem.get("id") not in bound_ids:
                    errors.append(f"Text {eid}: container '{cid}' missing boundElements entry for this text")

    return errors


def validate_spec(filepath: str) -> tuple[list[str], list[str]]:
    """Validate a diagram spec JSON file for multi-view metadata.

    Returns (errors, warnings). Errors indicate malformed structure.
    Warnings indicate advisory issues that should not fail the build.
    """
    errors: list[str] = []
    warnings: list[str] = []
    path = Path(filepath)

    if not path.exists():
        return [f"Spec file not found: {filepath}"], []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"], []

    if not isinstance(data, dict):
        return ["Spec must be a JSON object"], []

    model = data.get("model")
    views = data.get("views")

    # Legacy single-view spec — skip multi-view checks
    if model is None and views is None:
        overview_style = data.get("overview_style")
        if overview_style is not None and normalize_overview_style(overview_style) == "<invalid>":
            warnings.append(
                f"Legacy view: overview_style '{overview_style}' not in {VALID_OVERVIEW_STYLES}"
            )
        for group in data.get("groups", []):
            if not isinstance(group, dict):
                continue
            placement = group.get("placement")
            if placement is not None and normalize_group_placement(placement) == "<invalid>":
                warnings.append(
                    f"Legacy view: group '{group.get('id', '<unknown>')}' uses unsupported placement '{placement}'"
                )
        # Check node count warning for legacy specs
        nodes = data.get("nodes", [])
        if len(nodes) > MAX_NODE_WARNING_THRESHOLD:
            warnings.append(
                f"Node count ({len(nodes)}) exceeds {MAX_NODE_WARNING_THRESHOLD}; "
                "consider splitting into overview + detail views"
            )
        # Check for unlabeled edges
        edges = [edge for edge in data.get("edges", []) if isinstance(edge, dict)]
        for i, edge in enumerate(edges):
            if isinstance(edge, dict) and not edge.get("label"):
                warnings.append(f"Edge at index {i} ({edge.get('from')}->{edge.get('to')}) has no label")
        node_ids = {node.get("id") for node in nodes if isinstance(node, dict) and node.get("id")}
        warnings.extend(readability_warnings("Legacy view", node_ids, edges))
        selected_entities = [node for node in nodes if isinstance(node, dict)]
        legacy_view = {
            "layout": data.get("layout"),
            "view_mode": data.get("view_mode", "overview"),
            "diagram_kind": data.get("diagram_kind"),
            "overview_style": data.get("overview_style"),
            "groups": data.get("groups", []),
        }
        warnings.extend(overview_layout_warning("Legacy view", legacy_view, selected_entities))
        return errors, warnings

    # Multi-view spec validation
    if not isinstance(model, dict):
        errors.append("'model' must be an object")
        return errors, warnings

    if not isinstance(views, list):
        errors.append("'views' must be an array")
        return errors, warnings

    # Validate model entities
    entities = model.get("entities", [])
    if not isinstance(entities, list):
        errors.append("model.entities must be an array")
    else:
        entity_ids = set()
        for i, entity in enumerate(entities):
            if not isinstance(entity, dict):
                errors.append(f"Entity at index {i} must be an object")
                continue
            eid = entity.get("id")
            if not eid:
                errors.append(f"Entity at index {i} must include a non-empty 'id'")
                continue
            if eid in entity_ids:
                errors.append(f"Duplicate entity id '{eid}'")
            entity_ids.add(eid)

            if not entity.get("label"):
                errors.append(f"Entity '{eid}' must include a non-empty 'label'")

            # Evidence metadata warnings
            ev = entity.get("evidence_source")
            if ev is not None and ev not in VALID_EVIDENCE_SOURCES:
                warnings.append(
                    f"Entity '{eid}': evidence_source '{ev}' not in {VALID_EVIDENCE_SOURCES}"
                )
            conf = entity.get("confidence")
            if conf is not None and conf not in VALID_CONFIDENCE_LEVELS:
                warnings.append(
                    f"Entity '{eid}': confidence '{conf}' not in {VALID_CONFIDENCE_LEVELS}"
                )

    # Validate model relationships
    relationships = model.get("relationships", [])
    if not isinstance(relationships, list):
        errors.append("model.relationships must be an array")
    else:
        entity_id_set = {e.get("id") for e in entities if isinstance(e, dict)}
        for i, rel in enumerate(relationships):
            if not isinstance(rel, dict):
                errors.append(f"Relationship at index {i} must be an object")
                continue
            if rel.get("from") not in entity_id_set:
                errors.append(f"Relationship at index {i}: unknown source '{rel.get('from')}'")
            if rel.get("to") not in entity_id_set:
                errors.append(f"Relationship at index {i}: unknown target '{rel.get('to')}'")
            if not rel.get("label"):
                warnings.append(
                    f"Relationship at index {i} ({rel.get('from')}->{rel.get('to')}) has no label"
                )

            ev = rel.get("evidence_source")
            if ev is not None and ev not in VALID_EVIDENCE_SOURCES:
                warnings.append(
                    f"Relationship at index {i}: evidence_source '{ev}' not in {VALID_EVIDENCE_SOURCES}"
                )
            conf = rel.get("confidence")
            if conf is not None and conf not in VALID_CONFIDENCE_LEVELS:
                warnings.append(
                    f"Relationship at index {i}: confidence '{conf}' not in {VALID_CONFIDENCE_LEVELS}"
                )

    # Validate detail_level and audience
    detail = model.get("detail_level")
    if detail is not None and detail not in {"minimal", "standard", "detailed"}:
        warnings.append(f"model.detail_level '{detail}' not in {{minimal, standard, detailed}}")

    audience = model.get("audience")
    if audience is not None and audience not in {"technical", "executive", "mixed"}:
        warnings.append(f"model.audience '{audience}' not in {{technical, executive, mixed}}")

    # Validate views
    view_ids = set()
    for i, view in enumerate(views):
        if not isinstance(view, dict):
            errors.append(f"View at index {i} must be an object")
            continue

        vid = view.get("view_id")
        if not vid:
            errors.append(f"View at index {i} must include a non-empty 'view_id'")
        elif vid in view_ids:
            errors.append(f"Duplicate view_id '{vid}'")
        view_ids.add(vid)

        vm = view.get("view_mode")
        if not vm:
            errors.append(f"View '{vid or i}' must include a 'view_mode'")
        elif vm not in VALID_VIEW_MODES:
            errors.append(
                f"View '{vid or i}': view_mode '{vm}' not in {VALID_VIEW_MODES}"
            )

        overview_style = view.get("overview_style")
        if overview_style is not None and normalize_overview_style(overview_style) == "<invalid>":
            warnings.append(
                f"View '{vid or i}': overview_style '{overview_style}' not in {VALID_OVERVIEW_STYLES}"
            )

        for group in view.get("groups", []):
            if not isinstance(group, dict):
                continue
            placement = group.get("placement")
            if placement is not None and normalize_group_placement(placement) == "<invalid>":
                warnings.append(
                    f"View '{vid or i}': group '{group.get('id', '<unknown>')}' uses unsupported placement '{placement}'"
                )

        # Check entity_ids reference valid entities
        entity_refs = view.get("entity_ids")
        if entity_refs is not None and isinstance(entities, list):
            entity_id_set = {e.get("id") for e in entities if isinstance(e, dict)}
            for ref_id in entity_refs:
                if ref_id not in entity_id_set:
                    warnings.append(
                        f"View '{vid or i}': entity_ids references unknown entity '{ref_id}'"
                    )

        # Node count warning per view
        if entity_refs is not None:
            if len(entity_refs) > MAX_NODE_WARNING_THRESHOLD:
                warnings.append(
                    f"View '{vid or i}': entity count ({len(entity_refs)}) exceeds "
                    f"{MAX_NODE_WARNING_THRESHOLD}; consider splitting"
                )
        elif isinstance(entities, list) and len(entities) > MAX_NODE_WARNING_THRESHOLD:
            warnings.append(
                f"View '{vid or i}': all {len(entities)} entities selected, exceeds "
                f"{MAX_NODE_WARNING_THRESHOLD}; consider using entity_ids to filter"
            )

        if isinstance(relationships, list) and isinstance(entities, list):
            selected_ids = set(entity_refs) if entity_refs is not None else {
                e.get("id") for e in entities if isinstance(e, dict) and e.get("id")
            }
            selected_relationships = [
                rel for rel in relationships
                if isinstance(rel, dict)
                and rel.get("from") in selected_ids
                and rel.get("to") in selected_ids
            ]
            warnings.extend(readability_warnings(f"View '{vid or i}'", selected_ids, selected_relationships))
            selected_entities = [
                entity for entity in entities
                if isinstance(entity, dict) and entity.get("id") in selected_ids
            ]
            warnings.extend(overview_layout_warning(f"View '{vid or i}'", view, selected_entities))

    return errors, warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_excalidraw.py <file.excalidraw> [--spec <file.spec.json>]")
        sys.exit(1)

    # Parse arguments
    excalidraw_file = None
    spec_file = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--spec" and i + 1 < len(args):
            spec_file = args[i + 1]
            i += 2
        elif excalidraw_file is None:
            excalidraw_file = args[i]
            i += 1
        else:
            i += 1

    exit_code = 0

    # Validate .excalidraw file if provided
    if excalidraw_file:
        errors = validate(excalidraw_file)
        if errors:
            print(f"INVALID — {len(errors)} error(s):")
            for e in errors:
                print(f"  - {e}")
            exit_code = 1
        else:
            print("VALID")

    # Validate spec file if provided
    if spec_file:
        spec_errors, spec_warnings = validate_spec(spec_file)
        if spec_errors:
            print(f"SPEC INVALID — {len(spec_errors)} error(s):")
            for e in spec_errors:
                print(f"  - {e}")
            exit_code = 1
        else:
            print("SPEC VALID")
        if spec_warnings:
            print(f"  {len(spec_warnings)} warning(s):")
            for w in spec_warnings:
                print(f"  - WARNING: {w}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
