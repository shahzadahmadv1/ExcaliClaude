#!/usr/bin/env python3
"""Export compiled diagram views to Mermaid text format.

Consumes the same compiled view data as the Excalidraw builder so that
Mermaid is a secondary export, not a separate planning format.

Usage:
    python export_mermaid.py <spec.json> [--output <path.md>]

Without --output, prints to stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Import compile_spec from the builder so we share exactly the same pipeline
# ---------------------------------------------------------------------------

_BUILDER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BUILDER_DIR))
from build_excalidraw_diagram import compile_spec, EDGE_STYLES  # noqa: E402


# ---------------------------------------------------------------------------
# Edge-kind → Mermaid arrow mapping
# ---------------------------------------------------------------------------

MERMAID_ARROWS = {
    # solid
    "sync": "-->",
    "write": "-->",
    "deploy": "-->",
    "data-flow": "-->",
    "depends-on": "-->",
    "conditional-yes": "-->",
    "conditional-no": "-->",
    # dashed
    "async": "-.->",
    "publish": "-.->",
    "subscribe": "-.->",
    "trust-boundary": "-.->",
    # dotted (Mermaid has no native dotted; use dashed as closest)
    "read": "-.->",
    "imports": "-.->",
}

DEFAULT_ARROW = "-->"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mermaid_id(raw_id: str) -> str:
    """Sanitise an entity id for Mermaid (alphanumeric + underscores)."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw_id)


def _escape_label(text: str) -> str:
    """Escape quotes inside a Mermaid label string."""
    return text.replace('"', '#quot;')


def _node_label(node: dict[str, Any]) -> str:
    """Build a descriptive Mermaid node label from a compiled node dict."""
    parts = [node.get("label", node.get("id", "?"))]
    tech = node.get("technology")
    if tech:
        parts.append(f"[{tech}]")
    desc = node.get("description")
    if desc:
        parts.append(desc)
    return _escape_label(" — ".join(parts) if len(parts) > 1 else parts[0])


def _node_shape(node: dict[str, Any]) -> tuple[str, str]:
    """Return Mermaid open/close bracket pair for the node's shape/role."""
    shape = node.get("shape", "")
    if shape == "decision":
        return "{", "}"
    role = node.get("role", "service")
    if role in ("database", "storage"):
        return "[(", ")]"
    return "[", "]"


# ---------------------------------------------------------------------------
# Single-view export
# ---------------------------------------------------------------------------

def export_view(view_id: str, spec: dict[str, Any]) -> str:
    """Export one compiled view spec to Mermaid text."""
    lines: list[str] = []

    # Title as comment
    title = spec.get("title", view_id)
    lines.append(f"%% {title}")

    # Determine direction
    direction = spec.get("direction", "vertical")
    mermaid_dir = "TD" if direction == "vertical" else "LR"
    lines.append(f"graph {mermaid_dir}")

    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])

    # --- Subgraphs for groups ---
    groups_spec = spec.get("groups", [])
    group_order = [g["id"] for g in groups_spec] if groups_spec else []
    nodes_by_group: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        g = node.get("group", "default")
        nodes_by_group.setdefault(g, []).append(node)

    # Determine which groups to render
    render_groups = group_order if group_order else sorted(nodes_by_group.keys())

    emitted_node_ids: set[str] = set()

    for group_id in render_groups:
        group_nodes = nodes_by_group.get(group_id, [])
        if not group_nodes:
            continue

        # Find group label
        group_label = group_id
        for gs in groups_spec:
            if gs["id"] == group_id:
                group_label = gs.get("label", group_id)
                break

        lines.append(f"    subgraph {_mermaid_id(group_id)}[{_escape_label(group_label)}]")
        for node in group_nodes:
            mid = _mermaid_id(node["id"])
            label = _node_label(node)
            open_b, close_b = _node_shape(node)
            lines.append(f"        {mid}{open_b}\"{label}\"{close_b}")
            emitted_node_ids.add(node["id"])
        lines.append("    end")

    # Emit any ungrouped nodes
    for node in nodes:
        if node["id"] not in emitted_node_ids:
            mid = _mermaid_id(node["id"])
            label = _node_label(node)
            open_b, close_b = _node_shape(node)
            lines.append(f"    {mid}{open_b}\"{label}\"{close_b}")

    # --- Edges ---
    for edge in edges:
        src = _mermaid_id(edge["from"])
        dst = _mermaid_id(edge["to"])
        kind = edge.get("kind", "sync")
        arrow = MERMAID_ARROWS.get(kind, DEFAULT_ARROW)
        label = edge.get("label", "")
        seq = edge.get("sequence")
        if seq is not None and label:
            label = f"{seq}. {label}"
        elif seq is not None:
            label = str(seq)

        if label:
            lines.append(f"    {src} {arrow}|{_escape_label(label)}| {dst}")
        else:
            lines.append(f"    {src} {arrow} {dst}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Multi-view export
# ---------------------------------------------------------------------------

def export_mermaid(spec: dict[str, Any]) -> str:
    """Export a full spec (single or multi-view) to Mermaid text.

    Returns one Mermaid graph block per compiled view, separated by blank lines.
    """
    compiled_views = compile_spec(spec)
    blocks: list[str] = []
    for view_id, view_spec in compiled_views:
        blocks.append(export_view(view_id, view_spec))
    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a diagram spec to Mermaid text format."
    )
    parser.add_argument("spec", help="Path to the diagram spec JSON file.")
    parser.add_argument("--output", help="Output file path. Defaults to stdout.")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"Spec not found: {spec_path}", file=sys.stderr)
        return 1

    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        result = export_mermaid(spec)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result, encoding="utf-8")
        print(out_path)
    else:
        print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
