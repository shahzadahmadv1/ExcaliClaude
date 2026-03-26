#!/usr/bin/env python3
"""Validate .excalidraw file structure without rendering."""

import json
import sys
from pathlib import Path

ORDER_KEY_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

MAX_NODE_WARNING_THRESHOLD = 15

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
        # Check node count warning for legacy specs
        nodes = data.get("nodes", [])
        if len(nodes) > MAX_NODE_WARNING_THRESHOLD:
            warnings.append(
                f"Node count ({len(nodes)}) exceeds {MAX_NODE_WARNING_THRESHOLD}; "
                "consider splitting into overview + detail views"
            )
        # Check for unlabeled edges
        for i, edge in enumerate(data.get("edges", [])):
            if isinstance(edge, dict) and not edge.get("label"):
                warnings.append(f"Edge at index {i} ({edge.get('from')}->{edge.get('to')}) has no label")
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
