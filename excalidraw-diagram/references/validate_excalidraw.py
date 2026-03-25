#!/usr/bin/env python3
"""Validate .excalidraw file structure without rendering."""

import json
import sys
from pathlib import Path

ORDER_KEY_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


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


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_excalidraw.py <file.excalidraw>")
        sys.exit(1)

    errors = validate(sys.argv[1])
    if errors:
        print(f"INVALID — {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("VALID")
        sys.exit(0)


if __name__ == "__main__":
    main()
