#!/usr/bin/env python3
"""Build a polished .excalidraw scene from a structured diagram spec."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import textwrap
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROLE_STYLES = {
    "client": {"fill": "#e3f2fd", "stroke": "#1e88e5", "label": "Client / Frontend"},
    "api": {"fill": "#fff3e0", "stroke": "#ef6c00", "label": "API / Gateway"},
    "service": {"fill": "#e8f5e9", "stroke": "#43a047", "label": "Service / Backend"},
    "database": {"fill": "#fce4ec", "stroke": "#e53935", "label": "Database / Storage"},
    "external": {"fill": "#f3e5f5", "stroke": "#8e24aa", "label": "External / 3rd Party"},
    "infrastructure": {"fill": "#eceff1", "stroke": "#546e7a", "label": "Infrastructure"},
    "decision": {"fill": "#FFF3BF", "stroke": "#F59F00", "label": "Decision / Branch"},
    "host": {"fill": "#e0f2f1", "stroke": "#00897b", "label": "Host / VM / Node"},
    "container-runtime": {"fill": "#e8eaf6", "stroke": "#3949ab", "label": "Container Runtime"},
    "network": {"fill": "#fff8e1", "stroke": "#f9a825", "label": "Network / Zone"},
    "queue": {"fill": "#fce4ec", "stroke": "#ad1457", "label": "Queue / Stream"},
    "topic": {"fill": "#f3e5f5", "stroke": "#7b1fa2", "label": "Topic / Channel"},
    "trust-zone": {"fill": "#e8f5e9", "stroke": "#2e7d32", "label": "Trusted Zone"},
    "untrusted-zone": {"fill": "#ffebee", "stroke": "#c62828", "label": "Untrusted Zone"},
    "dmz": {"fill": "#fff3e0", "stroke": "#e65100", "label": "DMZ / Semi-trusted"},
    "library": {"fill": "#e3f2fd", "stroke": "#1565c0", "label": "Library / Package"},
}

EDGE_STYLES = {
    "sync": {"strokeStyle": "solid", "strokeColor": "#495057", "label": "Sync / request"},
    "async": {"strokeStyle": "dashed", "strokeColor": "#495057", "label": "Async / event"},
    "read": {"strokeStyle": "dotted", "strokeColor": "#495057", "label": "Read / query"},
    "write": {"strokeStyle": "solid", "strokeColor": "#495057", "label": "Write / command"},
    "conditional-yes": {"strokeStyle": "solid", "strokeColor": "#2b8a3e", "label": "Yes branch"},
    "conditional-no": {"strokeStyle": "solid", "strokeColor": "#c92a2a", "label": "No branch"},
    "publish": {"strokeStyle": "dashed", "strokeColor": "#7b1fa2", "label": "Publish / emit"},
    "subscribe": {"strokeStyle": "dashed", "strokeColor": "#1565c0", "label": "Subscribe / consume"},
    "deploy": {"strokeStyle": "solid", "strokeColor": "#00897b", "label": "Deploys to"},
    "data-flow": {"strokeStyle": "solid", "strokeColor": "#e65100", "label": "Data flow"},
    "depends-on": {"strokeStyle": "solid", "strokeColor": "#1565c0", "label": "Depends on"},
    "imports": {"strokeStyle": "dotted", "strokeColor": "#1565c0", "label": "Imports / uses"},
    "trust-boundary": {"strokeStyle": "dashed", "strokeColor": "#c62828", "label": "Trust boundary"},
}

EVIDENCE_STYLES = {
    "code": {"marker": "\u25cf", "color": "#2b8a3e", "label": "Code-derived"},
    "inferred": {"marker": "\u25cb", "color": "#e67700", "label": "Inferred"},
    "user-specified": {"marker": "\u25a0", "color": "#1971c2", "label": "User-specified"},
}

CONFIDENCE_STYLES = {
    "high": {"label": "High confidence"},
    "medium": {"label": "Medium confidence"},
    "low": {"label": "Low confidence"},
}

ROLE_ORDER = [
    "client", "api", "service", "database", "external", "infrastructure", "decision",
    "host", "container-runtime", "network", "queue", "topic",
    "trust-zone", "untrusted-zone", "dmz", "library",
]
DEFAULT_GROUP_STROKE = "#adb5bd"

TITLE_FONT_SIZE = 28
SUBTITLE_FONT_SIZE = 18
NODE_FONT_SIZE = 18
LABEL_FONT_SIZE = 16
DECISION_FONT_SIZE = 16
LEGEND_FONT_SIZE = 15
TEXT_LINE_HEIGHT = 1.25

CANVAS_MARGIN = 100
TOP_SECTION_GAP = 40
GROUP_GAP = 72
ROW_GAP = 120
COLUMN_GAP = 40
GROUP_PADDING_X = 28
GROUP_PADDING_Y = 36
NODE_PADDING_X = 22
NODE_PADDING_Y = 18
LEGEND_WIDTH = 300
LEGEND_ITEM_HEIGHT = 28
MIN_NODE_WIDTH = 180
MIN_NODE_HEIGHT = 82
MIN_DECISION_WIDTH = 180
MIN_DECISION_HEIGHT = 120
ORDER_KEY_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
MAX_LABEL_CHARS = 20
MAX_META_CHARS = 26
MAX_DESCRIPTION_CHARS = 30
MAX_DECISION_TEXT_CHARS = 18
MAX_DECISION_DETAIL_CHARS = 18
MAX_DECISION_LINES = 3
MAX_EDGE_LABEL_CHARS = 26
MAX_SUBTITLE_CHARS = 70
MAX_NOTE_CHARS = 88
EDGE_LABEL_OFFSET = 24
EDGE_LABEL_BACKGROUND = "#ffffff"
NODE_OBSTACLE_PADDING_X = 18
NODE_OBSTACLE_PADDING_Y = 16
TEXT_OBSTACLE_PADDING_X = 10
TEXT_OBSTACLE_PADDING_Y = 8
LABEL_SEARCH_STEP = 24
MAX_LABEL_SEARCH_RADIUS = 264
BRANCH_LABEL_OFFSET_X = 28
BRANCH_LABEL_OFFSET_Y = 24
BRANCH_LABEL_EXTRA_SPREAD = 64
PORT_SLOT_MARGIN = 24
PORT_SLOT_SPACING = 18
ROUTE_EXIT_MARGIN = 28
ROUTE_CHANNEL_SPACING = 22
MAX_ROUTE_GAP_BONUS = 220
EDGE_WARNING_DENSITY = 1.35
EDGE_SPLIT_DENSITY = 1.6
MAX_READABLE_EDGE_DEGREE = 5
MAX_READABLE_OVERLOADED_NODES = 3
SIDE_COLUMN_GAP = 120
SIDE_GROUP_NODE_GAP = 28
HYBRID_OVERVIEW_KINDS = {"architecture", "container", "context"}
VALID_OVERVIEW_STYLES = {"auto", "pure-layers", "core-with-sides"}
VALID_GROUP_PLACEMENTS = {"layer", "side-left", "side-right"}


def stable_int(*parts: Any) -> int:
    joined = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "diagram"


def normalize_role(value: str | None) -> str:
    role = (value or "service").strip().lower()
    aliases = {
        "client/frontend": "client",
        "frontend": "client",
        "api/gateway": "api",
        "gateway": "api",
        "service/backend": "service",
        "backend": "service",
        "database/storage": "database",
        "storage": "database",
        "external/3rd party": "external",
        "3rd party": "external",
        "external system": "external",
        "infra": "infrastructure",
        "decision / branch": "decision",
        "branch": "decision",
        "host/vm": "host",
        "vm": "host",
        "node": "host",
        "server": "host",
        "container": "container-runtime",
        "docker": "container-runtime",
        "k8s": "container-runtime",
        "kubernetes": "container-runtime",
        "zone": "network",
        "subnet": "network",
        "vpc": "network",
        "message queue": "queue",
        "stream": "queue",
        "event bus": "queue",
        "channel": "topic",
        "event topic": "topic",
        "trusted": "trust-zone",
        "trusted zone": "trust-zone",
        "internal zone": "trust-zone",
        "untrusted": "untrusted-zone",
        "external zone": "untrusted-zone",
        "semi-trusted": "dmz",
        "package": "library",
        "module": "library",
        "dependency": "library",
    }
    return aliases.get(role, role)


def midpoint(a: str, b: str | None, digits: str = ORDER_KEY_DIGITS) -> str:
    zero = digits[0]
    if b is not None and a >= b:
        raise ValueError(f"{a} >= {b}")
    if a.endswith(zero) or (b and b.endswith(zero)):
        raise ValueError("trailing zero")

    if b:
        common_prefix_length = 0
        while (a[common_prefix_length] if common_prefix_length < len(a) else zero) == b[common_prefix_length]:
            common_prefix_length += 1
        if common_prefix_length > 0:
            return b[:common_prefix_length] + midpoint(a[common_prefix_length:], b[common_prefix_length:], digits)

    digit_a = digits.index(a[0]) if a else 0
    digit_b = digits.index(b[0]) if b is not None else len(digits)
    if digit_b - digit_a > 1:
        mid_digit = (digit_a + digit_b + 1) // 2
        return digits[mid_digit]
    if b and len(b) > 1:
        return b[:1]
    return digits[digit_a] + midpoint(a[1:], None, digits)


def get_integer_length(head: str) -> int:
    if "a" <= head <= "z":
        return ord(head) - ord("a") + 2
    if "A" <= head <= "Z":
        return ord("Z") - ord(head) + 2
    raise ValueError(f"invalid order key head: {head}")


def validate_integer(integer: str) -> None:
    if len(integer) != get_integer_length(integer[0]):
        raise ValueError(f"invalid integer part of order key: {integer}")


def get_integer_part(key: str) -> str:
    integer_part_length = get_integer_length(key[0])
    if integer_part_length > len(key):
        raise ValueError(f"invalid order key: {key}")
    return key[:integer_part_length]


def validate_order_key(key: str, digits: str = ORDER_KEY_DIGITS) -> None:
    if key == "A" + (digits[0] * 26):
        raise ValueError(f"invalid order key: {key}")
    integer_part = get_integer_part(key)
    fractional_part = key[len(integer_part):]
    if fractional_part.endswith(digits[0]):
        raise ValueError(f"invalid order key: {key}")


def increment_integer(integer: str, digits: str = ORDER_KEY_DIGITS) -> str | None:
    validate_integer(integer)
    head = integer[0]
    remainder = list(integer[1:])
    carry = True
    for index in range(len(remainder) - 1, -1, -1):
        if not carry:
            break
        digit_index = digits.index(remainder[index]) + 1
        if digit_index == len(digits):
            remainder[index] = digits[0]
        else:
            remainder[index] = digits[digit_index]
            carry = False

    if carry:
        if head == "Z":
            return "a" + digits[0]
        if head == "z":
            return None
        next_head = chr(ord(head) + 1)
        if next_head > "a":
            remainder.append(digits[0])
        else:
            remainder.pop()
        return next_head + "".join(remainder)
    return head + "".join(remainder)


def decrement_integer(integer: str, digits: str = ORDER_KEY_DIGITS) -> str | None:
    validate_integer(integer)
    head = integer[0]
    remainder = list(integer[1:])
    borrow = True
    for index in range(len(remainder) - 1, -1, -1):
        if not borrow:
            break
        digit_index = digits.index(remainder[index]) - 1
        if digit_index == -1:
            remainder[index] = digits[-1]
        else:
            remainder[index] = digits[digit_index]
            borrow = False

    if borrow:
        if head == "a":
            return "Z" + digits[-1]
        if head == "A":
            return None
        previous_head = chr(ord(head) - 1)
        if previous_head < "Z":
            remainder.append(digits[-1])
        else:
            remainder.pop()
        return previous_head + "".join(remainder)
    return head + "".join(remainder)


def generate_order_key_between(a: str | None, b: str | None, digits: str = ORDER_KEY_DIGITS) -> str:
    if a is not None:
        validate_order_key(a, digits)
    if b is not None:
        validate_order_key(b, digits)
    if a is not None and b is not None and a >= b:
        raise ValueError(f"{a} >= {b}")

    if a is None:
        if b is None:
            return "a" + digits[0]
        integer_part_b = get_integer_part(b)
        fractional_part_b = b[len(integer_part_b):]
        if integer_part_b == "A" + (digits[0] * 26):
            return integer_part_b + midpoint("", fractional_part_b, digits)
        if integer_part_b < b:
            return integer_part_b
        decremented = decrement_integer(integer_part_b, digits)
        if decremented is None:
            raise ValueError("cannot decrement any more")
        return decremented

    if b is None:
        integer_part_a = get_integer_part(a)
        fractional_part_a = a[len(integer_part_a):]
        incremented = increment_integer(integer_part_a, digits)
        return integer_part_a + midpoint(fractional_part_a, None, digits) if incremented is None else incremented

    integer_part_a = get_integer_part(a)
    fractional_part_a = a[len(integer_part_a):]
    integer_part_b = get_integer_part(b)
    fractional_part_b = b[len(integer_part_b):]
    if integer_part_a == integer_part_b:
        return integer_part_a + midpoint(fractional_part_a, fractional_part_b, digits)
    incremented = increment_integer(integer_part_a, digits)
    if incremented is None:
        raise ValueError("cannot increment any more")
    if incremented < b:
        return incremented
    return integer_part_a + midpoint(fractional_part_a, None, digits)


def estimate_text_size(text: str, font_size: int, min_width: int = 0) -> tuple[int, int]:
    lines = text.splitlines() or [""]
    max_chars = max(len(line) for line in lines)
    width = max(min_width, int(max_chars * font_size * 0.58))
    height = max(int(len(lines) * font_size * TEXT_LINE_HEIGHT), font_size)
    return width, height


def wrap_text_lines(text: str, max_chars: int) -> list[str]:
    wrapped: list[str] = []
    for raw_line in (text or "").splitlines() or [""]:
        stripped = raw_line.strip()
        if not stripped:
            wrapped.append("")
            continue
        wrapped.extend(
            textwrap.wrap(
                stripped,
                width=max_chars,
                break_long_words=False,
                break_on_hyphens=False,
            )
            or [stripped]
        )
    return wrapped


def wrap_text(text: str, max_chars: int) -> str:
    return "\n".join(wrap_text_lines(text, max_chars))


def node_shape(node: dict[str, Any]) -> str:
    return node.get("shape") or ("decision" if normalize_role(node.get("role")) == "decision" else "box")


def is_decision_node(node: dict[str, Any]) -> bool:
    return node_shape(node) == "decision"


def node_body_lines(node: dict[str, Any]) -> list[str]:
    lines = wrap_text_lines(node["label"], MAX_LABEL_CHARS)
    node_type = node.get("node_type")
    technology = node.get("technology")
    meta = " | ".join(part for part in [node_type, technology] if part)
    if meta:
        lines.extend(wrap_text_lines(f"[{meta}]", MAX_META_CHARS))
    description = node.get("description")
    if description:
        lines.extend(wrap_text_lines(description, MAX_DESCRIPTION_CHARS))
    return lines


def decision_body_lines(node: dict[str, Any]) -> list[str]:
    label_lines = wrap_text_lines(node["label"], MAX_DECISION_TEXT_CHARS)
    description = node.get("description")
    if not description:
        return label_lines

    detail_lines = wrap_text_lines(description, MAX_DECISION_DETAIL_CHARS)
    if len(label_lines) + len(detail_lines) <= MAX_DECISION_LINES:
        return label_lines + detail_lines
    return label_lines


def decision_body_text(node: dict[str, Any]) -> str:
    return "\n".join(decision_body_lines(node))


def node_dimensions(node: dict[str, Any]) -> tuple[int, int]:
    if is_decision_node(node):
        text = decision_body_text(node)
        text_width, text_height = estimate_text_size(text, DECISION_FONT_SIZE, min_width=max(int(MIN_DECISION_WIDTH / 2) - 24, 96))
        width = max(MIN_DECISION_WIDTH, (text_width * 2) + (NODE_PADDING_X * 2))
        height = max(MIN_DECISION_HEIGHT, (text_height * 2) + (NODE_PADDING_Y * 2))
        return width, height

    body = "\n".join(node_body_lines(node))
    text_width, text_height = estimate_text_size(body, NODE_FONT_SIZE, min_width=MIN_NODE_WIDTH - (NODE_PADDING_X * 2))
    width = max(MIN_NODE_WIDTH, text_width + (NODE_PADDING_X * 2))
    height = max(MIN_NODE_HEIGHT, text_height + (NODE_PADDING_Y * 2))
    return width, height


def diagram_kind_label(value: str | None) -> str:
    kind = (value or "dynamic").strip().lower()
    labels = {
        "dynamic": "Dynamic diagram",
        "container": "Container diagram",
        "component": "Component diagram",
        "context": "System context diagram",
        "architecture": "Architecture overview",
        "deployment": "Deployment diagram",
        "data-flow": "Data / event flow",
        "trust-boundary": "Trust boundary diagram",
        "dependency-map": "Dependency map",
    }
    return labels.get(kind, kind.title())


def normalize_overview_style(value: str | None) -> str:
    style = (value or "auto").strip().lower()
    aliases = {
        "core_with_sides": "core-with-sides",
        "core with sides": "core-with-sides",
        "core": "core-with-sides",
        "layers": "pure-layers",
        "pure_layers": "pure-layers",
    }
    style = aliases.get(style, style)
    return style if style in VALID_OVERVIEW_STYLES else "auto"


def normalize_group_placement(value: str | None) -> str:
    placement = (value or "layer").strip().lower()
    aliases = {
        "left": "side-left",
        "right": "side-right",
        "side_left": "side-left",
        "side_right": "side-right",
    }
    placement = aliases.get(placement, placement)
    return placement if placement in VALID_GROUP_PLACEMENTS else "layer"


def hybrid_overview_candidate(spec: dict[str, Any]) -> bool:
    if spec.get("layout", "flow") != "layers":
        return False
    if spec.get("view_mode") not in {None, "overview"}:
        return False
    return (spec.get("diagram_kind") or "dynamic").strip().lower() in HYBRID_OVERVIEW_KINDS


def group_entities(nodes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        grouped[node.get("group", "")].append(node)
    return grouped


def infer_external_group_side(group_node_ids: set[str], edges: list[dict[str, Any]]) -> str:
    outbound = 0
    inbound = 0
    for edge in edges:
        source_in_group = edge.get("from") in group_node_ids
        target_in_group = edge.get("to") in group_node_ids
        if source_in_group and not target_in_group:
            outbound += 1
        elif target_in_group and not source_in_group:
            inbound += 1
    return "side-left" if outbound >= inbound else "side-right"


def async_infrastructure_group(nodes_in_group: list[dict[str, Any]], edges: list[dict[str, Any]]) -> bool:
    if not nodes_in_group:
        return False

    node_ids = {node["id"] for node in nodes_in_group}
    queue_like = sum(1 for node in nodes_in_group if normalize_role(node.get("role")) in {"queue", "topic"})
    infra_like = sum(1 for node in nodes_in_group if normalize_role(node.get("role")) == "infrastructure")
    async_edges = sum(
        1
        for edge in edges
        if (edge.get("from") in node_ids or edge.get("to") in node_ids)
        and edge.get("kind") in {"async", "publish", "subscribe"}
    )

    if queue_like and queue_like >= max(1, len(nodes_in_group) // 2):
        return True
    return async_edges > 0 and (queue_like + infra_like) == len(nodes_in_group)


def enrich_groups(
    spec: dict[str, Any],
    nodes: list[dict[str, Any]],
    groups: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    enriched = [dict(group) for group in groups]
    requested_style = normalize_overview_style(spec.get("overview_style"))
    explicit_side = any(normalize_group_placement(group.get("placement")) != "layer" for group in enriched)

    if not hybrid_overview_candidate(spec):
        for group in enriched:
            group["placement"] = normalize_group_placement(group.get("placement"))
        resolved_style = "core-with-sides" if explicit_side else "pure-layers"
        return enriched, resolved_style

    nodes_by_group = group_entities(nodes)
    inferred_placements: dict[str, str] = {}
    if requested_style != "pure-layers":
        for group in enriched:
            explicit = normalize_group_placement(group.get("placement"))
            if explicit != "layer":
                inferred_placements[group["id"]] = explicit
                continue

            nodes_in_group = nodes_by_group.get(group["id"], [])
            if not nodes_in_group:
                inferred_placements[group["id"]] = "layer"
                continue

            external_like = sum(
                1
                for node in nodes_in_group
                if (node.get("boundary") == "external") or normalize_role(node.get("role")) == "external"
            )
            if external_like >= max(1, len(nodes_in_group) // 2):
                inferred_placements[group["id"]] = infer_external_group_side(
                    {node["id"] for node in nodes_in_group},
                    spec.get("edges", []),
                )
                continue

            if async_infrastructure_group(nodes_in_group, spec.get("edges", [])):
                inferred_placements[group["id"]] = "side-right"
                continue

            inferred_placements[group["id"]] = "layer"

    inferred_side = any(placement != "layer" for placement in inferred_placements.values())
    if explicit_side:
        resolved_style = "core-with-sides"
    elif requested_style == "auto":
        resolved_style = "core-with-sides" if inferred_side else "pure-layers"
    else:
        resolved_style = requested_style

    for group in enriched:
        placement = normalize_group_placement(group.get("placement"))
        if placement == "layer" and resolved_style == "core-with-sides":
            placement = inferred_placements.get(group["id"], "layer")
        group["placement"] = placement

    return enriched, resolved_style


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def topological_depths(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, int]:
    node_ids = [node["id"] for node in nodes]
    indegree = {node_id: 0 for node_id in node_ids}
    graph: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in edges:
        source = edge["from"]
        target = edge["to"]
        graph[source].append(target)
        indegree[target] += 1

    order_hint = {node["id"]: node.get("order", index) for index, node in enumerate(nodes)}
    queue = deque(sorted((node_id for node_id, degree in indegree.items() if degree == 0), key=lambda item: order_hint[item]))
    depths = {node_id: 0 for node_id in node_ids}
    visited: list[str] = []

    while queue:
        current = queue.popleft()
        visited.append(current)
        for neighbor in graph[current]:
            depths[neighbor] = max(depths[neighbor], depths[current] + 1)
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    if len(visited) != len(node_ids):
        return {node["id"]: node.get("order", index) for index, node in enumerate(nodes)}
    return depths


@dataclass
class NodePlacement:
    node: dict[str, Any]
    x: int
    y: int
    width: int
    height: int
    depth: int = 0
    lane_index: int = 0
    placement_kind: str = "layer"

    @property
    def center_x(self) -> float:
        return self.x + (self.width / 2)

    @property
    def center_y(self) -> float:
        return self.y + (self.height / 2)


@dataclass
class GroupPlacement:
    group_id: str
    label: str
    x: int
    y: int
    width: int
    height: int
    stroke_color: str = DEFAULT_GROUP_STROKE
    placement: str = "layer"


@dataclass
class EdgePlan:
    edge: dict[str, Any]
    edge_id: str
    source: NodePlacement
    target: NodePlacement
    start_side: str
    end_side: str
    start_offset: float = 0.0
    end_offset: float = 0.0
    channel_distance: float = 0.0
    corridor_side: str | None = None
    route_style: str = "default"
    outer_left: float | None = None
    outer_right: float | None = None
    side_inner_left: float | None = None
    side_inner_right: float | None = None


@dataclass(frozen=True)
class RoutedEdge:
    edge_id: str
    points: list[tuple[float, float]]


def clamp_value(value: float, minimum: float, maximum: float) -> float:
    if minimum > maximum:
        return (minimum + maximum) / 2
    return max(minimum, min(value, maximum))


def edge_element_id(edge: dict[str, Any]) -> str:
    return edge.get("id") or f"edge-{edge['from']}-{edge['to']}-{slugify(edge.get('label', 'link'))}"


def quantize_int(value: float, step: int = 40) -> int:
    return int(round(value / step) * step)


def distributed_offsets(count: int, span: float, spacing: float) -> list[float]:
    if count <= 1:
        return [0.0] * count
    usable_span = max(0.0, min(span, spacing * (count - 1)))
    if usable_span == 0:
        return [0.0] * count
    step = usable_span / (count - 1)
    start = -(usable_span / 2)
    return [start + (index * step) for index in range(count)]


def node_side_port_span(placement: NodePlacement, side: str) -> float:
    if side in {"top", "bottom"}:
        base = placement.width
    else:
        base = placement.height
    multiplier = 0.55 if is_decision_node(placement.node) else 0.72
    return max((base * multiplier) - (PORT_SLOT_MARGIN * 2), 0.0)


def node_side_anchor(placement: NodePlacement, side: str, offset: float = 0.0) -> tuple[float, float]:
    center_x = placement.center_x
    center_y = placement.center_y
    half_width = placement.width / 2
    half_height = placement.height / 2

    if is_decision_node(placement.node):
        if side in {"top", "bottom"}:
            dx = clamp_value(offset, -half_width + PORT_SLOT_MARGIN, half_width - PORT_SLOT_MARGIN)
            dy = half_height * (1 - (abs(dx) / max(half_width, 1)))
            return center_x + dx, center_y - dy if side == "top" else center_y + dy
        dy = clamp_value(offset, -half_height + PORT_SLOT_MARGIN, half_height - PORT_SLOT_MARGIN)
        dx = half_width * (1 - (abs(dy) / max(half_height, 1)))
        return (center_x - dx if side == "left" else center_x + dx), center_y + dy

    if side == "top":
        dx = clamp_value(offset, -half_width + PORT_SLOT_MARGIN, half_width - PORT_SLOT_MARGIN)
        return center_x + dx, placement.y
    if side == "bottom":
        dx = clamp_value(offset, -half_width + PORT_SLOT_MARGIN, half_width - PORT_SLOT_MARGIN)
        return center_x + dx, placement.y + placement.height
    if side == "left":
        dy = clamp_value(offset, -half_height + PORT_SLOT_MARGIN, half_height - PORT_SLOT_MARGIN)
        return placement.x, center_y + dy
    dy = clamp_value(offset, -half_height + PORT_SLOT_MARGIN, half_height - PORT_SLOT_MARGIN)
    return placement.x + placement.width, center_y + dy


def preferred_connection_sides(
    source: NodePlacement,
    target: NodePlacement,
    *,
    layout: str,
    direction: str,
) -> tuple[str, str]:
    dx = target.center_x - source.center_x
    dy = target.center_y - source.center_y

    if layout == "flow" and direction == "vertical":
        if source.depth != target.depth:
            return ("bottom", "top") if source.depth < target.depth else ("top", "bottom")
        if source.lane_index != target.lane_index:
            return ("right", "left") if dx >= 0 else ("left", "right")

    if layout == "flow" and direction == "horizontal":
        if source.depth != target.depth:
            return ("right", "left") if source.depth < target.depth else ("left", "right")
        if source.lane_index != target.lane_index:
            return ("bottom", "top") if dy >= 0 else ("top", "bottom")

    if abs(dx) >= abs(dy):
        return ("right", "left") if dx >= 0 else ("left", "right")
    return ("bottom", "top") if dy >= 0 else ("top", "bottom")


def simplify_route_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    deduped: list[tuple[float, float]] = []
    for x, y in points:
        if deduped and abs(deduped[-1][0] - x) < 0.01 and abs(deduped[-1][1] - y) < 0.01:
            continue
        deduped.append((round(x, 2), round(y, 2)))

    if len(deduped) <= 2:
        return deduped

    simplified = [deduped[0]]
    for index, point in enumerate(deduped[1:-1], start=1):
        prev_x, prev_y = simplified[-1]
        next_x, next_y = deduped[index + 1]
        same_x = abs(prev_x - point[0]) < 0.01 and abs(point[0] - next_x) < 0.01
        same_y = abs(prev_y - point[1]) < 0.01 and abs(point[1] - next_y) < 0.01
        if same_x or same_y:
            continue
        simplified.append(point)
    simplified.append(deduped[-1])
    return simplified


def connected_axis_positions(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    depths: dict[str, int],
    group_index: dict[str, int],
) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    node_lookup = {node["id"]: node for node in nodes}
    neighbor_groups: dict[str, list[int]] = defaultdict(list)
    neighbor_depths: dict[str, list[int]] = defaultdict(list)

    for edge in edges:
        source_id = edge["from"]
        target_id = edge["to"]
        source_group = group_index.get(node_lookup[source_id].get("group"), 0)
        target_group = group_index.get(node_lookup[target_id].get("group"), 0)
        source_depth = depths.get(source_id, 0)
        target_depth = depths.get(target_id, 0)

        neighbor_groups[source_id].append(target_group)
        neighbor_groups[target_id].append(source_group)
        neighbor_depths[source_id].append(target_depth)
        neighbor_depths[target_id].append(source_depth)

    return neighbor_groups, neighbor_depths


def flow_gap_loads(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    depths: dict[str, int],
    group_index: dict[str, int],
) -> tuple[dict[int, int], dict[int, int]]:
    node_lookup = {node["id"]: node for node in nodes}
    row_gap_load: dict[int, int] = defaultdict(int)
    lane_gap_load: dict[int, int] = defaultdict(int)

    for edge in edges:
        source_depth = depths.get(edge["from"], 0)
        target_depth = depths.get(edge["to"], 0)
        low_depth, high_depth = sorted((source_depth, target_depth))
        for gap_index in range(low_depth, high_depth):
            row_gap_load[gap_index] += 1

        source_lane = group_index.get(node_lookup[edge["from"]].get("group"), 0)
        target_lane = group_index.get(node_lookup[edge["to"]].get("group"), 0)
        low_lane, high_lane = sorted((source_lane, target_lane))
        for gap_index in range(low_lane, high_lane):
            lane_gap_load[gap_index] += 1

    return row_gap_load, lane_gap_load


def gap_bonus(load: int) -> int:
    return min(max(0, load - 2) * ROUTE_CHANNEL_SPACING, MAX_ROUTE_GAP_BONUS)


@dataclass
class SceneBuilder:
    title: str
    elements: list[dict[str, Any]] = field(default_factory=list)
    floating_label_boxes: list[tuple[int, int, int, int]] = field(default_factory=list)
    last_index: str | None = None

    def reserve_box(self, x: int, y: int, width: int, height: int, *, pad_x: int = 6, pad_y: int = 4) -> tuple[int, int, int, int]:
        box = (x - pad_x, y - pad_y, x + width + pad_x, y + height + pad_y)
        self.floating_label_boxes.append(box)
        return box

    def next_index(self) -> str:
        index = generate_order_key_between(self.last_index, None)
        self.last_index = index
        return index

    def base_element(self, element_id: str, element_type: str, x: int, y: int, width: int, height: int) -> dict[str, Any]:
        return {
            "id": element_id,
            "type": element_type,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "angle": 0,
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "index": self.next_index(),
            "roundness": {"type": 3} if element_type == "rectangle" else None,
            "seed": stable_int(self.title, element_id, "seed"),
            "version": 1,
            "versionNonce": stable_int(self.title, element_id, "nonce"),
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
        }

    def add_text(
        self,
        element_id: str,
        text: str,
        x: int,
        y: int,
        font_size: int,
        *,
        width: int | None = None,
        height: int | None = None,
        container_id: str | None = None,
        group_ids: list[str] | None = None,
        align: str = "left",
        color: str = "#1e1e1e",
        background_color: str = "transparent",
        reserve_for_floating_labels: bool = False,
    ) -> dict[str, Any]:
        text_width, text_height = estimate_text_size(text, font_size, min_width=width or 0)
        item = self.base_element(element_id, "text", x, y, width or text_width, height or text_height)
        item.update(
            {
                "strokeColor": color,
                "backgroundColor": background_color,
                "groupIds": group_ids or [],
                "roundness": None,
                "text": text,
                "fontSize": font_size,
                "fontFamily": 3,
                "textAlign": align,
                "verticalAlign": "middle",
                "containerId": container_id,
                "originalText": text,
                "autoResize": width is None,
                "lineHeight": TEXT_LINE_HEIGHT,
            }
        )
        self.elements.append(item)
        if reserve_for_floating_labels:
            self.reserve_box(item["x"], item["y"], item["width"], item["height"], pad_x=TEXT_OBSTACLE_PADDING_X, pad_y=TEXT_OBSTACLE_PADDING_Y)
        return item

    def resolve_floating_label_position(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        *,
        preferred_positions: list[tuple[int, int]] | None = None,
    ) -> tuple[int, int]:
        candidates: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()

        def add_candidate(candidate_x: int, candidate_y: int) -> None:
            candidate = (candidate_x, candidate_y)
            if candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)

        for candidate_x, candidate_y in preferred_positions or []:
            add_candidate(int(candidate_x), int(candidate_y))

        base_offsets = [
            (0, 0),
            (18, -18),
            (-18, 18),
            (28, 24),
            (-28, -24),
            (40, 0),
            (-40, 0),
            (0, 40),
            (0, -40),
            (48, 32),
            (-48, 32),
            (48, -32),
            (-48, -32),
            (64, 0),
            (-64, 0),
            (0, 56),
            (0, -56),
        ]
        for offset_x, offset_y in base_offsets:
            add_candidate(x + offset_x, y + offset_y)

        for radius in range(LABEL_SEARCH_STEP, MAX_LABEL_SEARCH_RADIUS + LABEL_SEARCH_STEP, LABEL_SEARCH_STEP):
            for direction_x, direction_y in [
                (1, 0),
                (-1, 0),
                (0, 1),
                (0, -1),
                (1, 1),
                (-1, 1),
                (1, -1),
                (-1, -1),
                (2, 1),
                (-2, 1),
                (2, -1),
                (-2, -1),
                (1, 2),
                (-1, 2),
                (1, -2),
                (-1, -2),
            ]:
                add_candidate(x + (direction_x * radius), y + (direction_y * radius))

        best_fallback: tuple[int, int] | None = None
        best_score: tuple[int, int, int] | None = None
        for candidate_x, candidate_y in candidates:
            candidate = (
                candidate_x - 6,
                candidate_y - 4,
                candidate_x + width + 6,
                candidate_y + height + 4,
            )
            overlapping = [existing for existing in self.floating_label_boxes if boxes_overlap(candidate, existing)]
            if not overlapping:
                self.reserve_box(candidate_x, candidate_y, width, height)
                return candidate_x, candidate_y

            overlap_score = sum(overlap_area(candidate, existing) for existing in overlapping)
            candidate_score = (
                overlap_score,
                len(overlapping),
                abs(candidate_x - x) + abs(candidate_y - y),
            )
            if best_score is None or candidate_score < best_score:
                best_score = candidate_score
                best_fallback = (candidate_x, candidate_y)

        fallback_x, fallback_y = best_fallback or (x, y)
        self.reserve_box(fallback_x, fallback_y, width, height)
        return fallback_x, fallback_y

    def add_group(self, placement: GroupPlacement) -> None:
        rect_id = f"group-{placement.group_id}"
        rect = self.base_element(rect_id, "rectangle", placement.x, placement.y, placement.width, placement.height)
        rect.update(
            {
                "strokeColor": placement.stroke_color,
                "backgroundColor": "transparent",
                "strokeStyle": "dashed",
                "roundness": {"type": 3},
            }
        )
        self.elements.append(rect)
        group_label = wrap_text(placement.label, 28)
        self.add_text(
            f"{rect_id}-label",
            group_label,
            placement.x + 16,
            placement.y + 10,
            LABEL_FONT_SIZE,
            group_ids=[placement.group_id],
            width=min(placement.width - 32, 260),
            reserve_for_floating_labels=True,
        )

    def add_node(self, placement: NodePlacement) -> dict[str, Any]:
        node = placement.node
        role = normalize_role(node.get("role"))
        style = ROLE_STYLES[role]
        node_id = f"node-{node['id']}"
        shape = node_shape(node)

        rect = self.base_element(node_id, "diamond" if shape == "decision" else "rectangle", placement.x, placement.y, placement.width, placement.height)
        rect.update(
            {
                "strokeColor": style["stroke"],
                "backgroundColor": style["fill"],
                "groupIds": [node["group"]] if node.get("group") else [],
                "boundElements": [],
            }
        )
        self.elements.append(rect)
        self.reserve_box(
            placement.x,
            placement.y,
            placement.width,
            placement.height,
            pad_x=NODE_OBSTACLE_PADDING_X,
            pad_y=NODE_OBSTACLE_PADDING_Y,
        )

        if shape == "decision":
            text = decision_body_text(node)
            text_width, text_height = estimate_text_size(text, DECISION_FONT_SIZE)
            available_width = max(int((placement.width / 2) - 20), 96)
            text_width = min(text_width, available_width)
            text_item = self.add_text(
                f"text-{node['id']}",
                text,
                int(placement.center_x - (text_width / 2)),
                int(placement.center_y - (text_height / 2)),
                DECISION_FONT_SIZE,
                width=text_width,
                height=text_height,
                container_id=node_id,
                group_ids=[node["group"]] if node.get("group") else [],
                align="center",
            )
            rect["boundElements"].append({"id": text_item["id"], "type": "text"})
        else:
            body = "\n".join(node_body_lines(node))
            text_width = max(placement.width - 24, 120)
            _, text_height = estimate_text_size(body, NODE_FONT_SIZE, min_width=text_width)
            text_item = self.add_text(
                f"text-{node['id']}",
                body,
                placement.x + 12,
                int(placement.y + ((placement.height - text_height) / 2)),
                NODE_FONT_SIZE,
                width=text_width,
                height=text_height,
                container_id=node_id,
                group_ids=[node["group"]] if node.get("group") else [],
                align="center",
            )
            rect["boundElements"].append({"id": text_item["id"], "type": "text"})

        return rect

    def add_arrow(
        self,
        edge: dict[str, Any],
        placements: dict[str, NodePlacement],
        elements_by_node: dict[str, dict[str, Any]],
        *,
        route: RoutedEdge | None = None,
    ) -> None:
        source = placements[edge["from"]]
        target = placements[edge["to"]]
        edge_kind = edge.get("kind", "sync")
        style = EDGE_STYLES.get(edge_kind, EDGE_STYLES["sync"])
        if route is None:
            start_x, start_y, end_x, end_y = connection_points(source, target)
            points = arrow_points(start_x, start_y, end_x, end_y)
        else:
            points = route.points
            start_x, start_y = points[0]
            end_x, end_y = points[-1]
        dx = points[-1][0] - points[0][0]
        dy = points[-1][1] - points[0][1]

        arrow_id = edge_element_id(edge)
        arrow = self.base_element(arrow_id, "arrow", int(start_x), int(start_y), int(dx), int(dy))
        arrow.update(
            {
                "strokeColor": style["strokeColor"],
                "backgroundColor": "transparent",
                "strokeStyle": style["strokeStyle"],
                "roundness": {"type": 2},
                "points": [[round(x - start_x, 2), round(y - start_y, 2)] for x, y in points],
                "lastCommittedPoint": None,
                "startBinding": {
                    "elementId": elements_by_node[edge["from"]]["id"],
                    "focus": 0,
                    "gap": 1,
                    "fixedPoint": None,
                },
                "endBinding": {
                    "elementId": elements_by_node[edge["to"]]["id"],
                    "focus": 0,
                    "gap": 1,
                    "fixedPoint": None,
                },
                "startArrowhead": None,
                "endArrowhead": "arrow",
                "elbowed": len(points) > 2,
            }
        )
        self.elements.append(arrow)
        for node_id in [edge["from"], edge["to"]]:
            elements_by_node[node_id].setdefault("boundElements", []).append({"id": arrow["id"], "type": "arrow"})

        label = edge.get("label", "").strip()
        sequence = edge.get("sequence")
        if sequence is not None and label and not re.match(rf"^{sequence}\.", label):
            label = f"{sequence}. {label}"
        elif sequence is not None and not label:
            label = f"{sequence}"

        if label:
            wrapped_label = wrap_text(label, MAX_EDGE_LABEL_CHARS)
            text_width, text_height = estimate_text_size(wrapped_label, LEGEND_FONT_SIZE, min_width=120)
            text_width = min(text_width, 240)
            preferred_positions = decision_branch_label_candidates(edge_kind, source, target, text_width, text_height)
            if preferred_positions:
                label_align = "left"
                base_x, base_y = preferred_positions[0]
                label_x, label_y = self.resolve_floating_label_position(
                    base_x,
                    base_y,
                    text_width,
                    text_height,
                    preferred_positions=preferred_positions,
                )
            else:
                anchor_x, anchor_y, orientation, sign = edge_label_anchor(points)
                label_align = "left" if orientation == "vertical" else "center"
                preferred_positions = edge_label_candidates(anchor_x, anchor_y, orientation, sign, source, target, text_width, text_height)
                base_x, base_y = preferred_positions[0]
                label_x, label_y = self.resolve_floating_label_position(
                    base_x,
                    base_y,
                    text_width,
                    text_height,
                    preferred_positions=preferred_positions,
                )
            self.add_text(
                f"{arrow['id']}-label",
                wrapped_label,
                label_x,
                label_y,
                LEGEND_FONT_SIZE,
                width=text_width,
                height=text_height,
                align=label_align,
                background_color=EDGE_LABEL_BACKGROUND,
            )


def connection_points(source: NodePlacement, target: NodePlacement) -> tuple[float, float, float, float]:
    start_x, start_y = node_boundary_point(source, target.center_x, target.center_y)
    end_x, end_y = node_boundary_point(target, source.center_x, source.center_y)
    return start_x, start_y, end_x, end_y


def arrow_points(start_x: float, start_y: float, end_x: float, end_y: float) -> list[tuple[float, float]]:
    dx = end_x - start_x
    dy = end_y - start_y
    if abs(dx) < 8 or abs(dy) < 8:
        return [(start_x, start_y), (end_x, end_y)]

    if abs(dx) > abs(dy):
        mid_x = start_x + (dx / 2)
        return [
            (start_x, start_y),
            (mid_x, start_y),
            (mid_x, end_y),
            (end_x, end_y),
        ]

    mid_y = start_y + (dy / 2)
    return [
        (start_x, start_y),
        (start_x, mid_y),
        (end_x, mid_y),
        (end_x, end_y),
    ]


def edge_label_position(points: list[tuple[float, float]]) -> tuple[float, float]:
    if len(points) <= 2:
        start = points[0]
        end = points[-1]
        return (start[0] + end[0]) / 2, (start[1] + end[1]) / 2

    middle_index = len(points) // 2
    first = points[middle_index - 1]
    second = points[middle_index]
    return (first[0] + second[0]) / 2, (first[1] + second[1]) / 2


def edge_label_anchor(points: list[tuple[float, float]]) -> tuple[float, float, str, int]:
    if len(points) < 2:
        return 0, 0, "horizontal", 1

    segments = []
    for start, end in zip(points, points[1:]):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = abs(dx) + abs(dy)
        orientation = "horizontal" if abs(dx) >= abs(dy) else "vertical"
        sign = 1
        if orientation == "horizontal" and dy < 0:
            sign = -1
        if orientation == "vertical" and dx < 0:
            sign = -1
        segments.append((length, (start[0] + end[0]) / 2, (start[1] + end[1]) / 2, orientation, sign))

    if not segments:
        mid_x, mid_y = edge_label_position(points)
        return mid_x, mid_y, "horizontal", 1

    horizontal_segments = [segment for segment in segments if segment[3] == "horizontal" and segment[0] >= 32]
    candidate_pool = horizontal_segments or segments
    best = max(candidate_pool, key=lambda item: item[0])
    _, mid_x, mid_y, orientation, sign = best
    return mid_x, mid_y, orientation, sign


def boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def overlap_area(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    overlap_width = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    overlap_height = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return overlap_width * overlap_height


def node_boundary_point(placement: NodePlacement, toward_x: float, toward_y: float) -> tuple[float, float]:
    center_x = placement.center_x
    center_y = placement.center_y
    dx = toward_x - center_x
    dy = toward_y - center_y
    if dx == 0 and dy == 0:
        return center_x, center_y

    half_width = max(placement.width / 2, 1)
    half_height = max(placement.height / 2, 1)
    if is_decision_node(placement.node):
        scale = 1 / ((abs(dx) / half_width) + (abs(dy) / half_height))
    else:
        scale = 1 / max(abs(dx) / half_width, abs(dy) / half_height)

    return center_x + (dx * scale), center_y + (dy * scale)


def assign_edge_port_offsets(plans: list[EdgePlan]) -> None:
    side_buckets: dict[tuple[str, str], list[tuple[EdgePlan, str]]] = defaultdict(list)
    for plan in plans:
        side_buckets[(plan.source.node["id"], plan.start_side)].append((plan, "start"))
        side_buckets[(plan.target.node["id"], plan.end_side)].append((plan, "end"))

    for (_node_id, side), entries in side_buckets.items():
        first_plan, endpoint_kind = entries[0]
        placement = first_plan.source if endpoint_kind == "start" else first_plan.target
        ordered = sorted(
            entries,
            key=lambda item: (
                item[0].target.center_x if item[1] == "start" and side in {"top", "bottom"} else
                item[0].source.center_x if item[1] == "end" and side in {"top", "bottom"} else
                item[0].target.center_y if item[1] == "start" else
                item[0].source.center_y,
                item[0].edge.get("sequence") is None,
                item[0].edge.get("sequence") or 0,
                item[0].edge_id,
            ),
        )
        offsets = distributed_offsets(len(ordered), node_side_port_span(placement, side), PORT_SLOT_SPACING)
        for (plan, endpoint), offset in zip(ordered, offsets):
            if endpoint == "start":
                plan.start_offset = offset
            else:
                plan.end_offset = offset


def forced_side_for_corridor(placement: NodePlacement, corridor_side: str) -> str:
    if placement.placement_kind == "side-left":
        return "right"
    if placement.placement_kind == "side-right":
        return "left"
    return "left" if corridor_side == "left" else "right"


def assign_edge_channel_offsets(plans: list[EdgePlan], *, layout: str, direction: str) -> None:
    buckets: dict[tuple[Any, ...], list[EdgePlan]] = defaultdict(list)

    for plan in plans:
        if plan.route_style == "side-vertical" and plan.corridor_side in {"left", "right"}:
            buckets[("side", plan.corridor_side)].append(plan)
            continue
        if plan.start_side in {"top", "bottom"}:
            downward = plan.start_side == "bottom"
            if layout == "flow":
                if direction == "vertical":
                    band_index = plan.source.depth
                else:
                    band_index = plan.source.lane_index
                key = ("horizontal", direction, downward, band_index)
            else:
                anchor = plan.source.y + plan.source.height if downward else plan.source.y
                key = ("horizontal", downward, quantize_int(anchor))
        else:
            rightward = plan.start_side == "right"
            if layout == "flow":
                if direction == "vertical":
                    band_index = plan.source.lane_index
                else:
                    band_index = plan.source.depth
                key = ("vertical", direction, rightward, band_index)
            else:
                anchor = plan.source.x + plan.source.width if rightward else plan.source.x
                key = ("vertical", rightward, quantize_int(anchor))
        buckets[key].append(plan)

    for plans_in_bucket in buckets.values():
        ordered = sorted(
            plans_in_bucket,
            key=lambda plan: (
                min(plan.source.center_x, plan.target.center_x) if plan.start_side in {"top", "bottom"} else min(plan.source.center_y, plan.target.center_y),
                max(plan.source.center_x, plan.target.center_x) if plan.start_side in {"top", "bottom"} else max(plan.source.center_y, plan.target.center_y),
                plan.edge.get("sequence") is None,
                plan.edge.get("sequence") or 0,
                plan.edge_id,
            ),
        )
        for index, plan in enumerate(ordered):
            plan.channel_distance = ROUTE_EXIT_MARGIN + (index * ROUTE_CHANNEL_SPACING)


def build_routed_edge(plan: EdgePlan) -> RoutedEdge:
    start = node_side_anchor(plan.source, plan.start_side, plan.start_offset)
    end = node_side_anchor(plan.target, plan.end_side, plan.end_offset)

    if plan.route_style == "side-vertical" and plan.corridor_side in {"left", "right"}:
        if plan.corridor_side == "left" and plan.side_inner_right is not None:
            corridor_x = plan.side_inner_right + plan.channel_distance
        elif plan.corridor_side == "right" and plan.side_inner_left is not None:
            corridor_x = plan.side_inner_left - plan.channel_distance
        else:
            return RoutedEdge(plan.edge_id, arrow_points(start[0], start[1], end[0], end[1]))
        points = simplify_route_points([start, (corridor_x, start[1]), (corridor_x, end[1]), end])
        return RoutedEdge(plan.edge_id, points)

    if plan.route_style == "outer-vertical" and plan.corridor_side in {"left", "right"} and plan.outer_left is not None and plan.outer_right is not None:
        going_down = plan.target.center_y >= plan.source.center_y
        exit_y = (
            plan.source.y + plan.source.height + plan.channel_distance
            if going_down
            else plan.source.y - plan.channel_distance
        )
        approach_y = (
            plan.target.y - plan.channel_distance
            if going_down
            else plan.target.y + plan.target.height + plan.channel_distance
        )
        corridor_x = (
            plan.outer_left - plan.channel_distance
            if plan.corridor_side == "left"
            else plan.outer_right + plan.channel_distance
        )
        points = simplify_route_points(
            [
                start,
                (start[0], exit_y),
                (corridor_x, exit_y),
                (corridor_x, approach_y),
                (end[0], approach_y),
                end,
            ]
        )
        return RoutedEdge(plan.edge_id, points)

    if plan.start_side in {"top", "bottom"} and plan.end_side in {"top", "bottom"}:
        preferred_y = (plan.source.y + plan.source.height + plan.channel_distance) if plan.start_side == "bottom" else (plan.source.y - plan.channel_distance)
        low = min(start[1], end[1]) + 18
        high = max(start[1], end[1]) - 18
        if low >= high:
            points = arrow_points(start[0], start[1], end[0], end[1])
        else:
            channel_y = clamp_value(preferred_y, low, high)
            points = simplify_route_points([start, (start[0], channel_y), (end[0], channel_y), end])
        return RoutedEdge(plan.edge_id, points)

    if plan.start_side in {"left", "right"} and plan.end_side in {"left", "right"}:
        preferred_x = (plan.source.x + plan.source.width + plan.channel_distance) if plan.start_side == "right" else (plan.source.x - plan.channel_distance)
        low = min(start[0], end[0]) + 18
        high = max(start[0], end[0]) - 18
        if low >= high:
            points = arrow_points(start[0], start[1], end[0], end[1])
        else:
            channel_x = clamp_value(preferred_x, low, high)
            points = simplify_route_points([start, (channel_x, start[1]), (channel_x, end[1]), end])
        return RoutedEdge(plan.edge_id, points)

    return RoutedEdge(plan.edge_id, arrow_points(start[0], start[1], end[0], end[1]))


def plan_edge_routes(spec: dict[str, Any], placements: dict[str, NodePlacement]) -> dict[str, RoutedEdge]:
    layout = spec.get("layout", "flow")
    direction = spec.get("direction", "vertical")
    plans: list[EdgePlan] = []
    core_placements = [placement for placement in placements.values() if placement.placement_kind == "layer"]
    bounds_source = core_placements or list(placements.values())
    outer_left = min((placement.x for placement in bounds_source), default=CANVAS_MARGIN) - GROUP_PADDING_X
    outer_right = max((placement.x + placement.width for placement in bounds_source), default=CANVAS_MARGIN) + GROUP_PADDING_X
    side_left = [placement for placement in placements.values() if placement.placement_kind == "side-left"]
    side_right = [placement for placement in placements.values() if placement.placement_kind == "side-right"]
    side_inner_right = max((placement.x + placement.width for placement in side_left), default=None)
    side_inner_left = min((placement.x for placement in side_right), default=None)

    for edge in spec["edges"]:
        source = placements[edge["from"]]
        target = placements[edge["to"]]
        corridor_side: str | None = None
        route_style = "default"
        if source.placement_kind != "layer" or target.placement_kind != "layer":
            if source.placement_kind == "side-left" or target.placement_kind == "side-left":
                corridor_side = "left"
            elif source.placement_kind == "side-right" or target.placement_kind == "side-right":
                corridor_side = "right"
            if corridor_side is not None:
                start_side = forced_side_for_corridor(source, corridor_side)
                end_side = forced_side_for_corridor(target, corridor_side)
                route_style = "side-vertical"
            else:
                start_side, end_side = preferred_connection_sides(
                    source,
                    target,
                    layout=layout,
                    direction=direction,
                )
        else:
            start_side, end_side = preferred_connection_sides(
                source,
                target,
                layout=layout,
                direction=direction,
            )
        if layout == "layers" and source.placement_kind == "layer" and target.placement_kind == "layer" and abs(source.lane_index - target.lane_index) > 1:
            start_side, end_side = ("bottom", "top") if target.center_y >= source.center_y else ("top", "bottom")
            corridor_side = preferred_outer_corridor(source, target, outer_left, outer_right)
            route_style = "outer-vertical"
        plans.append(
            EdgePlan(
                edge=edge,
                edge_id=edge_element_id(edge),
                source=source,
                target=target,
                start_side=start_side,
                end_side=end_side,
                corridor_side=corridor_side,
                route_style=route_style,
                outer_left=outer_left,
                outer_right=outer_right,
                side_inner_left=side_inner_left,
                side_inner_right=side_inner_right,
            )
        )

    assign_edge_port_offsets(plans)
    assign_edge_channel_offsets(plans, layout=layout, direction=direction)
    return {plan.edge_id: build_routed_edge(plan) for plan in plans}


def placement_obstacle_box(placement: NodePlacement, *, pad_x: int = 12, pad_y: int = 10) -> tuple[float, float, float, float]:
    return (
        placement.x - pad_x,
        placement.y - pad_y,
        placement.x + placement.width + pad_x,
        placement.y + placement.height + pad_y,
    )


def orthogonal_segment_intersects_box(
    start: tuple[float, float],
    end: tuple[float, float],
    box: tuple[float, float, float, float],
) -> bool:
    left, top, right, bottom = box
    x1, y1 = start
    x2, y2 = end

    if abs(x1 - x2) < 0.01:
        if x1 <= left or x1 >= right:
            return False
        low, high = sorted((y1, y2))
        return low < bottom and high > top

    if abs(y1 - y2) < 0.01:
        if y1 <= top or y1 >= bottom:
            return False
        low, high = sorted((x1, x2))
        return low < right and high > left

    seg_left, seg_right = sorted((x1, x2))
    seg_top, seg_bottom = sorted((y1, y2))
    return seg_left < right and seg_right > left and seg_top < bottom and seg_bottom > top


def route_overlap_metrics(
    spec: dict[str, Any],
    placements: dict[str, NodePlacement],
    routes: dict[str, RoutedEdge],
) -> tuple[int, dict[str, int]]:
    overlap_counts: dict[str, int] = defaultdict(int)

    for edge in spec["edges"]:
        edge_id = edge_element_id(edge)
        route = routes.get(edge_id)
        if route is None:
            continue
        for node_id, placement in placements.items():
            if node_id in {edge["from"], edge["to"]}:
                continue
            box = placement_obstacle_box(placement)
            if any(
                orthogonal_segment_intersects_box(start, end, box)
                for start, end in zip(route.points, route.points[1:])
            ):
                overlap_counts[node_id] += 1

    return sum(overlap_counts.values()), overlap_counts


def connected_center_x(
    node_id: str,
    spec: dict[str, Any],
    placements: dict[str, NodePlacement],
) -> float | None:
    centers: list[float] = []
    for edge in spec.get("edges", []):
        if edge.get("from") == node_id and edge.get("to") in placements:
            centers.append(placements[edge["to"]].center_x)
        elif edge.get("to") == node_id and edge.get("from") in placements:
            centers.append(placements[edge["from"]].center_x)
    if not centers:
        return None
    return sum(centers) / len(centers)


def preferred_outer_corridor(
    source: NodePlacement,
    target: NodePlacement,
    outer_left: float,
    outer_right: float,
) -> str:
    left_cost = abs(source.center_x - outer_left) + abs(target.center_x - outer_left)
    right_cost = abs(source.center_x - outer_right) + abs(target.center_x - outer_right)
    return "left" if left_cost <= right_cost else "right"


def nudge_transit_obstacles(
    spec: dict[str, Any],
    placements: dict[str, NodePlacement],
    group_placements: list[GroupPlacement],
) -> dict[str, NodePlacement]:
    layout = spec.get("layout", "flow")
    direction = spec.get("direction", "vertical")
    if layout not in {"flow", "layers"}:
        return placements

    routes = plan_edge_routes(spec, placements)
    total_overlaps, node_overlaps = route_overlap_metrics(spec, placements, routes)
    if total_overlaps == 0:
        return placements

    group_by_id = {group.group_id: group for group in group_placements}
    adjusted = dict(placements)
    cell_counts: dict[tuple[int, int], int] = defaultdict(int)
    group_counts: dict[str, int] = defaultdict(int)
    for placement in placements.values():
        cell_counts[(placement.depth, placement.lane_index)] += 1
        group_counts[placement.node.get("group", "")] += 1

    if layout == "layers":
        layer_groups = [group for group in group_placements if group.placement == "layer"]
        if layer_groups:
            max_group_right = max(group.x + group.width for group in layer_groups)
            for group in layer_groups:
                group.width = max_group_right - group.x

    for node_id, overlap_count in sorted(node_overlaps.items(), key=lambda item: (-item[1], item[0])):
        placement = adjusted[node_id]
        if overlap_count <= 0:
            continue

        group = group_by_id.get(placement.node.get("group", ""))
        if group is None:
            continue

        if layout == "flow":
            if direction != "vertical" or cell_counts[(placement.depth, placement.lane_index)] != 1:
                continue
        elif placement.placement_kind != "layer" or group_counts[placement.node.get("group", "")] != 1:
            continue

        min_x = group.x + GROUP_PADDING_X
        max_x = group.x + group.width - placement.width - GROUP_PADDING_X
        if max_x - min_x < 24:
            continue

        preferred_center = connected_center_x(node_id, spec, adjusted)
        preferred_x = placement.x if preferred_center is None else int(preferred_center - (placement.width / 2))
        candidate_xs: set[int] = {
            int(min_x),
            int(max_x),
            int((min_x + max_x) / 2),
            int(min_x + ((max_x - min_x) / 3)),
            int(min_x + (2 * (max_x - min_x) / 3)),
            int(clamp_value(preferred_x, min_x, max_x)),
        }
        if layout == "layers":
            for step_x in range(int(min_x), int(max_x) + 1, 80):
                candidate_xs.add(step_x)
        candidate_xs = set(candidate_xs)

        current_score = (
            total_overlaps,
            overlap_count,
            abs(placement.x - preferred_x),
            0,
        )
        best_score = current_score
        best_placement = placement
        best_routes = routes

        for candidate_x in sorted(candidate_xs):
            if abs(candidate_x - placement.x) < 2:
                continue

            candidate_placement = NodePlacement(
                node=placement.node,
                x=candidate_x,
                y=placement.y,
                width=placement.width,
                height=placement.height,
                depth=placement.depth,
                lane_index=placement.lane_index,
            )
            trial_placements = dict(adjusted)
            trial_placements[node_id] = candidate_placement
            trial_routes = plan_edge_routes(spec, trial_placements)
            trial_total, trial_overlaps = route_overlap_metrics(spec, trial_placements, trial_routes)
            trial_score = (
                trial_total,
                trial_overlaps.get(node_id, 0),
                abs(candidate_x - preferred_x),
                abs(candidate_x - placement.x),
            )
            if trial_score < best_score:
                best_score = trial_score
                best_placement = candidate_placement
                best_routes = trial_routes

        if best_placement is not placement:
            adjusted[node_id] = best_placement
            routes = best_routes
            total_overlaps, node_overlaps = route_overlap_metrics(spec, adjusted, routes)

    return adjusted


def edge_label_candidates(
    anchor_x: float,
    anchor_y: float,
    orientation: str,
    sign: int,
    source: NodePlacement,
    target: NodePlacement,
    text_width: int,
    text_height: int,
) -> list[tuple[int, int]]:
    if orientation == "vertical":
        horizontal_sign = sign if sign else (1 if target.center_x >= source.center_x else -1)
        if horizontal_sign >= 0:
            base_x = int(anchor_x + EDGE_LABEL_OFFSET)
        else:
            base_x = int(anchor_x - EDGE_LABEL_OFFSET - text_width)
        base_y = int(anchor_y - (text_height / 2))
        return [
            (base_x, base_y),
            (base_x, base_y - (text_height + 18)),
            (base_x, base_y + text_height + 18),
            (base_x + (horizontal_sign * 48), base_y),
            (base_x - (horizontal_sign * 48), base_y),
        ]

    vertical_direction = -1 if target.center_y >= source.center_y else 1
    base_x = int(anchor_x - (text_width / 2))
    base_y = int(anchor_y + (vertical_direction * (text_height + EDGE_LABEL_OFFSET)))
    return [
        (base_x, base_y),
        (base_x - 48, base_y),
        (base_x + 48, base_y),
        (base_x, base_y + (vertical_direction * (text_height + 18))),
        (base_x - 32, base_y + (vertical_direction * (text_height + 18))),
        (base_x + 32, base_y + (vertical_direction * (text_height + 18))),
    ]


def decision_branch_label_candidates(
    edge_kind: str,
    source: NodePlacement,
    target: NodePlacement,
    text_width: int,
    text_height: int,
) -> list[tuple[int, int]]:
    if edge_kind not in {"conditional-yes", "conditional-no"} or not is_decision_node(source.node):
        return []

    horizontal_sign = 1 if target.center_x >= source.center_x else -1
    vertical_sign = -1 if edge_kind == "conditional-yes" else 1
    outward_x = source.center_x + (horizontal_sign * ((source.width / 2) + BRANCH_LABEL_OFFSET_X))
    if horizontal_sign >= 0:
        primary_x = int(outward_x + 8)
        secondary_x = primary_x + BRANCH_LABEL_EXTRA_SPREAD
    else:
        primary_x = int(outward_x - text_width - 8)
        secondary_x = primary_x - BRANCH_LABEL_EXTRA_SPREAD

    primary_y = int(source.center_y + (vertical_sign * ((source.height / 4) + text_height + BRANCH_LABEL_OFFSET_Y)))
    secondary_y = int(source.center_y + (vertical_sign * ((source.height / 2) + text_height + BRANCH_LABEL_OFFSET_Y)))
    midpoint_x = int(((source.center_x + target.center_x) / 2) - (text_width / 2))
    midpoint_y = int(((source.center_y + target.center_y) / 2) + (vertical_sign * (text_height + BRANCH_LABEL_OFFSET_Y)))

    return [
        (primary_x, primary_y),
        (secondary_x, primary_y),
        (primary_x, secondary_y),
        (secondary_x, secondary_y),
        (midpoint_x, midpoint_y),
    ]


def validate_spec(spec: dict[str, Any]) -> None:
    ensure(isinstance(spec, dict), "Spec must be a JSON object.")
    ensure(isinstance(spec.get("title"), str) and spec["title"].strip(), "Spec must include a non-empty 'title'.")
    ensure(isinstance(spec.get("nodes"), list) and spec["nodes"], "Spec must include a non-empty 'nodes' array.")
    ensure(isinstance(spec.get("edges"), list), "Spec must include an 'edges' array.")

    node_ids: set[str] = set()
    for index, node in enumerate(spec["nodes"]):
        ensure(isinstance(node, dict), f"Node at index {index} must be an object.")
        ensure(isinstance(node.get("id"), str) and node["id"].strip(), f"Node at index {index} must include a non-empty 'id'.")
        ensure(node["id"] not in node_ids, f"Duplicate node id '{node['id']}'.")
        ensure(isinstance(node.get("label"), str) and node["label"].strip(), f"Node '{node['id']}' must include a non-empty 'label'.")
        role = normalize_role(node.get("role"))
        ensure(role in ROLE_STYLES, f"Node '{node['id']}' uses unsupported role '{node.get('role')}'.")
        node_ids.add(node["id"])

    for index, edge in enumerate(spec["edges"]):
        ensure(isinstance(edge, dict), f"Edge at index {index} must be an object.")
        ensure(edge.get("from") in node_ids, f"Edge at index {index} references unknown source '{edge.get('from')}'.")
        ensure(edge.get("to") in node_ids, f"Edge at index {index} references unknown target '{edge.get('to')}'.")

    layout = spec.get("layout", "flow")
    ensure(layout in {"flow", "layers"}, "Spec 'layout' must be either 'flow' or 'layers'.")
    direction = spec.get("direction", "vertical")
    ensure(direction in {"vertical", "horizontal"}, "Spec 'direction' must be either 'vertical' or 'horizontal'.")
    if "overview_style" in spec:
        ensure(
            normalize_overview_style(spec.get("overview_style")) == spec.get("overview_style"),
            "Spec 'overview_style' must be 'auto', 'pure-layers', or 'core-with-sides'.",
        )
    for group in spec.get("groups", []):
        if isinstance(group, dict) and "placement" in group:
            ensure(
                normalize_group_placement(group.get("placement")) == group.get("placement"),
                "Group 'placement' must be 'layer', 'side-left', or 'side-right'.",
            )


def complete_groups(spec: dict[str, Any], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = [dict(group) for group in spec.get("groups", []) if isinstance(group, dict) and group.get("id")]
    seen = {group["id"] for group in groups}

    inferred: list[dict[str, Any]] = []
    for node in nodes:
        group_id = node.get("group")
        if not group_id or group_id in seen:
            continue
        inferred.append({"id": group_id, "label": group_id.replace("-", " ").title()})
        seen.add(group_id)

    if groups or inferred:
        return groups + inferred

    role_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        role_buckets[normalize_role(node.get("role"))].append(node)

    derived_groups = []
    for role in ROLE_ORDER:
        if not role_buckets.get(role):
            continue
        group_id = role
        for node in role_buckets[role]:
            node["group"] = group_id
        derived_groups.append({"id": group_id, "label": ROLE_STYLES[role]["label"]})
    return derived_groups


def layout_flow(
    spec: dict[str, Any],
    nodes: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    top_y: int,
) -> tuple[dict[str, NodePlacement], list[GroupPlacement], int, int]:
    direction = spec.get("direction", "vertical")
    edges = spec["edges"]
    depths = topological_depths(nodes, edges)
    group_index = {group["id"]: index for index, group in enumerate(groups)}
    fallback_group = groups[0]["id"]

    for node in nodes:
        node.setdefault("group", fallback_group)

    neighbor_groups, neighbor_depths = connected_axis_positions(nodes, edges, depths, group_index)
    row_gap_load, lane_gap_load = flow_gap_loads(nodes, edges, depths, group_index)

    cell_map: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        cell_map[(depths[node["id"]], group_index.get(node["group"], 0))].append(node)

    max_depth = max(depths.values(), default=0)
    lane_sizes: dict[str, int] = {}
    row_sizes: dict[int, int] = {}

    if direction == "vertical":
        for group in groups:
            max_width = 0
            column = group_index[group["id"]]
            for depth in range(max_depth + 1):
                same_cell = cell_map.get((depth, column), [])
                cell_width = sum(node_dimensions(node)[0] for node in same_cell)
                if len(same_cell) > 1:
                    cell_width += COLUMN_GAP * (len(same_cell) - 1)
                max_width = max(max_width, cell_width)
            lane_sizes[group["id"]] = max(max_width + (GROUP_PADDING_X * 2), 260)
        for depth in range(max_depth + 1):
            max_height = 0
            for group in groups:
                same_cell = cell_map.get((depth, group_index[group["id"]]), [])
                if same_cell:
                    max_height = max(max_height, max(node_dimensions(node)[1] for node in same_cell))
            row_sizes[depth] = max(max_height, MIN_NODE_HEIGHT)
    else:
        for group in groups:
            max_height = 0
            column = group_index[group["id"]]
            for depth in range(max_depth + 1):
                same_cell = cell_map.get((depth, column), [])
                cell_height = sum(node_dimensions(node)[1] for node in same_cell)
                if len(same_cell) > 1:
                    cell_height += COLUMN_GAP * (len(same_cell) - 1)
                max_height = max(max_height, cell_height)
            lane_sizes[group["id"]] = max(max_height + (GROUP_PADDING_Y * 2), 220)
        for depth in range(max_depth + 1):
            max_width = 0
            for group in groups:
                same_cell = cell_map.get((depth, group_index[group["id"]]), [])
                if same_cell:
                    max_width = max(max_width, max(node_dimensions(node)[0] for node in same_cell))
            row_sizes[depth] = max(max_width, MIN_NODE_WIDTH)

    placements: dict[str, NodePlacement] = {}
    group_placements: list[GroupPlacement] = []

    if direction == "vertical":
        lane_x: dict[str, int] = {}
        current_x = CANVAS_MARGIN
        for index, group in enumerate(groups):
            column = group_index[group["id"]]
            lane_x[group["id"]] = current_x
            current_x += lane_sizes[group["id"]]
            if index < len(groups) - 1:
                current_x += GROUP_GAP + gap_bonus(lane_gap_load.get(column, 0))

        row_y: dict[int, int] = {}
        current_y = top_y
        for depth in range(max_depth + 1):
            row_y[depth] = current_y
            current_y += row_sizes[depth]
            if depth < max_depth:
                current_y += ROW_GAP + gap_bonus(row_gap_load.get(depth, 0))

        content_bottom = top_y
        for group in groups:
            lane_left = lane_x[group["id"]]
            lane_width = lane_sizes[group["id"]]
            column = group_index[group["id"]]
            for depth in range(max_depth + 1):
                same_cell = sorted(
                    cell_map.get((depth, column), []),
                    key=lambda item: (
                        (sum(neighbor_groups[item["id"]]) / len(neighbor_groups[item["id"]])) if neighbor_groups.get(item["id"]) else column,
                        item.get("order", 0),
                        item["id"],
                    ),
                )
                if not same_cell:
                    continue
                cell_total = sum(node_dimensions(node)[0] for node in same_cell) + (COLUMN_GAP * (len(same_cell) - 1))
                cursor_x = int(lane_left + ((lane_width - cell_total) / 2))
                for node in same_cell:
                    width, height = node_dimensions(node)
                    x = cursor_x
                    y = int(row_y[depth] + ((row_sizes[depth] - height) / 2))
                    placements[node["id"]] = NodePlacement(
                        node=node,
                        x=x,
                        y=y,
                        width=width,
                        height=height,
                        depth=depth,
                        lane_index=column,
                    )
                    cursor_x += width + COLUMN_GAP
                    content_bottom = max(content_bottom, y + height)

        for group in groups:
            group_placements.append(
                GroupPlacement(
                    group_id=group["id"],
                    label=group.get("label", group["id"].replace("-", " ").title()),
                    x=lane_x[group["id"]],
                    y=top_y - 16,
                    width=lane_sizes[group["id"]],
                    height=(content_bottom - top_y) + 56,
                    stroke_color=group.get("strokeColor", DEFAULT_GROUP_STROKE),
                )
            )

        return placements, group_placements, current_x, content_bottom

    lane_y: dict[str, int] = {}
    current_y = top_y
    for index, group in enumerate(groups):
        column = group_index[group["id"]]
        lane_y[group["id"]] = current_y
        current_y += lane_sizes[group["id"]]
        if index < len(groups) - 1:
            current_y += GROUP_GAP + gap_bonus(lane_gap_load.get(column, 0))

    column_x: dict[int, int] = {}
    current_x = CANVAS_MARGIN
    for depth in range(max_depth + 1):
        column_x[depth] = current_x
        current_x += row_sizes[depth]
        if depth < max_depth:
            current_x += ROW_GAP + gap_bonus(row_gap_load.get(depth, 0))

    content_right = CANVAS_MARGIN
    for group in groups:
        lane_top = lane_y[group["id"]]
        lane_height = lane_sizes[group["id"]]
        column = group_index[group["id"]]
        for depth in range(max_depth + 1):
            same_cell = sorted(
                cell_map.get((depth, column), []),
                key=lambda item: (
                    (sum(neighbor_depths[item["id"]]) / len(neighbor_depths[item["id"]])) if neighbor_depths.get(item["id"]) else depth,
                    item.get("order", 0),
                    item["id"],
                ),
            )
            if not same_cell:
                continue
            cell_total = sum(node_dimensions(node)[1] for node in same_cell) + (COLUMN_GAP * (len(same_cell) - 1))
            cursor_y = int(lane_top + ((lane_height - cell_total) / 2))
            for node in same_cell:
                width, height = node_dimensions(node)
                x = int(column_x[depth] + ((row_sizes[depth] - width) / 2))
                y = cursor_y
                placements[node["id"]] = NodePlacement(
                    node=node,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    depth=depth,
                    lane_index=column,
                )
                cursor_y += height + COLUMN_GAP
                content_right = max(content_right, x + width)

    for group in groups:
        group_placements.append(
            GroupPlacement(
                group_id=group["id"],
                label=group.get("label", group["id"].replace("-", " ").title()),
                x=CANVAS_MARGIN - 16,
                y=lane_y[group["id"]],
                width=(content_right - CANVAS_MARGIN) + 56,
                height=lane_sizes[group["id"]],
                stroke_color=group.get("strokeColor", DEFAULT_GROUP_STROKE),
            )
        )

    return placements, group_placements, content_right, current_y


def layout_layers_pure(
    spec: dict[str, Any],
    nodes: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    top_y: int,
    *,
    start_x: int = CANVAS_MARGIN,
) -> tuple[dict[str, NodePlacement], list[GroupPlacement], int, int]:
    group_nodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    group_index = {group["id"]: index for index, group in enumerate(groups)}
    for node in nodes:
        node.setdefault("group", groups[0]["id"])
        group_nodes[node["group"]].append(node)

    node_group_index = {node["id"]: group_index.get(node["group"], 0) for node in nodes}
    group_gap_load: dict[int, int] = defaultdict(int)
    for edge in spec.get("edges", []):
        if edge.get("from") not in node_group_index or edge.get("to") not in node_group_index:
            continue
        low_group, high_group = sorted((node_group_index[edge["from"]], node_group_index[edge["to"]]))
        for gap_index in range(low_group, high_group):
            group_gap_load[gap_index] += 1

    placements: dict[str, NodePlacement] = {}
    group_placements: list[GroupPlacement] = []
    current_y = top_y
    max_right = start_x

    for index, group in enumerate(groups):
        nodes_in_group = sorted(group_nodes.get(group["id"], []), key=lambda item: (item.get("order", 0), item["id"]))
        if not nodes_in_group:
            continue

        node_sizes = [node_dimensions(node) for node in nodes_in_group]
        group_width = sum(width for width, _ in node_sizes) + (COLUMN_GAP * (len(node_sizes) - 1)) + (GROUP_PADDING_X * 2)
        header_height = 28
        group_height = max(height for _, height in node_sizes) + (GROUP_PADDING_Y * 2) + header_height

        cursor_x = start_x + GROUP_PADDING_X
        for depth, (node, (width, height)) in enumerate(zip(nodes_in_group, node_sizes)):
            x = cursor_x
            y = int(current_y + header_height + ((group_height - header_height - height) / 2))
            placements[node["id"]] = NodePlacement(
                node=node,
                x=x,
                y=y,
                width=width,
                height=height,
                depth=depth,
                lane_index=group_index.get(group["id"], 0),
                placement_kind=normalize_group_placement(group.get("placement")),
            )
            cursor_x += width + COLUMN_GAP

        group_placements.append(
            GroupPlacement(
                group_id=group["id"],
                label=group.get("label", group["id"].replace("-", " ").title()),
                x=start_x,
                y=current_y,
                width=group_width,
                height=group_height,
                stroke_color=group.get("strokeColor", DEFAULT_GROUP_STROKE),
                placement=normalize_group_placement(group.get("placement")),
            )
        )
        current_y += group_height
        if index < len(groups) - 1:
            current_y += GROUP_GAP + gap_bonus(group_gap_load.get(group_index.get(group["id"], 0), 0))
        max_right = max(max_right, start_x + group_width)

    return placements, group_placements, max_right, current_y


def connected_centers(
    node_id: str,
    spec: dict[str, Any],
    placements: dict[str, NodePlacement],
    *,
    placement_kind: str | None = None,
) -> list[tuple[float, float]]:
    centers: list[tuple[float, float]] = []
    for edge in spec.get("edges", []):
        other_id: str | None = None
        if edge.get("from") == node_id:
            other_id = edge.get("to")
        elif edge.get("to") == node_id:
            other_id = edge.get("from")
        if other_id not in placements:
            continue
        other = placements[other_id]
        if placement_kind is not None and other.placement_kind != placement_kind:
            continue
        centers.append((other.center_x, other.center_y))
    return centers


def side_group_dimensions(nodes_in_group: list[dict[str, Any]]) -> tuple[int, int]:
    node_sizes = [node_dimensions(node) for node in nodes_in_group]
    header_height = 28
    group_width = max(width for width, _ in node_sizes) + (GROUP_PADDING_X * 2)
    group_height = (
        header_height
        + (GROUP_PADDING_Y * 2)
        + sum(height for _, height in node_sizes)
        + (SIDE_GROUP_NODE_GAP * (len(node_sizes) - 1))
    )
    return group_width, group_height


def layout_layers_with_sides(
    spec: dict[str, Any],
    nodes: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    top_y: int,
) -> tuple[dict[str, NodePlacement], list[GroupPlacement], int, int]:
    left_groups = [group for group in groups if normalize_group_placement(group.get("placement")) == "side-left"]
    right_groups = [group for group in groups if normalize_group_placement(group.get("placement")) == "side-right"]
    core_groups = [group for group in groups if normalize_group_placement(group.get("placement")) == "layer"]
    if not core_groups:
        fallback_groups = [dict(group, placement="layer") for group in groups]
        return layout_layers_pure(spec, nodes, fallback_groups, top_y)

    nodes_by_group = group_entities(nodes)
    left_widths = [side_group_dimensions(nodes_by_group.get(group["id"], []))[0] for group in left_groups if nodes_by_group.get(group["id"])]
    core_start_x = CANVAS_MARGIN
    if left_widths:
        core_start_x += sum(left_widths) + (GROUP_GAP * max(0, len(left_widths) - 1)) + SIDE_COLUMN_GAP

    core_node_ids = {node["id"] for node in nodes if node.get("group") in {group["id"] for group in core_groups}}
    core_nodes = [node for node in nodes if node["id"] in core_node_ids]
    core_edges = [
        edge for edge in spec.get("edges", [])
        if edge.get("from") in core_node_ids and edge.get("to") in core_node_ids
    ]
    core_spec = dict(spec, edges=core_edges)
    placements, group_placements, content_width, content_bottom = layout_layers_pure(
        core_spec,
        core_nodes,
        core_groups,
        top_y,
        start_x=core_start_x,
    )

    core_left = min((group.x for group in group_placements), default=core_start_x)
    core_right = max((group.x + group.width for group in group_placements), default=content_width)
    left_x = CANVAS_MARGIN
    right_x = core_right + SIDE_COLUMN_GAP
    max_right = max(content_width, core_right)

    def add_side_group(group: dict[str, Any], group_x: int) -> tuple[GroupPlacement | None, int]:
        nodes_in_group = nodes_by_group.get(group["id"], [])
        if not nodes_in_group:
            return None, group_x

        connected_y = []
        for node in nodes_in_group:
            connected_y.extend(center_y for _center_x, center_y in connected_centers(node["id"], spec, placements, placement_kind="layer"))
        nodes_with_targets = []
        for node in nodes_in_group:
            linked_centers = connected_centers(node["id"], spec, placements, placement_kind="layer")
            target_y = sum(center_y for _center_x, center_y in linked_centers) / len(linked_centers) if linked_centers else None
            nodes_with_targets.append((node, target_y))

        nodes_with_targets.sort(key=lambda item: (item[1] if item[1] is not None else float("inf"), item[0].get("order", 0), item[0]["id"]))
        ordered_nodes = [node for node, _target_y in nodes_with_targets]
        target_center_y = (
            sum(connected_y) / len(connected_y)
            if connected_y
            else max(top_y + 80, (content_bottom + top_y) / 2)
        )

        group_width, group_height = side_group_dimensions(ordered_nodes)
        group_top = int(max(top_y, target_center_y - (group_height / 2)))
        header_height = 28
        cursor_y = group_top + header_height + GROUP_PADDING_Y

        for depth, node in enumerate(ordered_nodes):
            width, height = node_dimensions(node)
            x = int(group_x + ((group_width - width) / 2))
            placements[node["id"]] = NodePlacement(
                node=node,
                x=x,
                y=cursor_y,
                width=width,
                height=height,
                depth=depth,
                lane_index=groups.index(group),
                placement_kind=normalize_group_placement(group.get("placement")),
            )
            cursor_y += height + SIDE_GROUP_NODE_GAP

        group_placement = GroupPlacement(
            group_id=group["id"],
            label=group.get("label", group["id"].replace("-", " ").title()),
            x=group_x,
            y=group_top,
            width=group_width,
            height=group_height,
            stroke_color=group.get("strokeColor", DEFAULT_GROUP_STROKE),
            placement=normalize_group_placement(group.get("placement")),
        )
        return group_placement, group_x + group_width

    for index, group in enumerate(left_groups):
        placement, group_right = add_side_group(group, left_x)
        if placement is None:
            continue
        group_placements.append(placement)
        content_bottom = max(content_bottom, placement.y + placement.height)
        max_right = max(max_right, group_right)
        left_x = group_right + (GROUP_GAP if index < len(left_groups) - 1 else SIDE_COLUMN_GAP)

    for index, group in enumerate(right_groups):
        placement, group_right = add_side_group(group, right_x)
        if placement is None:
            continue
        group_placements.append(placement)
        content_bottom = max(content_bottom, placement.y + placement.height)
        max_right = max(max_right, group_right)
        right_x = group_right + (GROUP_GAP if index < len(right_groups) - 1 else SIDE_COLUMN_GAP)

    ordered_group_ids = [group["id"] for group in groups]
    group_placements.sort(key=lambda placement: ordered_group_ids.index(placement.group_id))
    return placements, group_placements, max_right, content_bottom


def layout_layers(
    spec: dict[str, Any],
    nodes: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    top_y: int,
    *,
    overview_style: str = "pure-layers",
) -> tuple[dict[str, NodePlacement], list[GroupPlacement], int, int]:
    if overview_style == "core-with-sides":
        return layout_layers_with_sides(spec, nodes, groups, top_y)
    return layout_layers_pure(spec, nodes, groups, top_y)


def add_title_block(builder: SceneBuilder, spec: dict[str, Any]) -> int:
    title = wrap_text(spec["title"].strip(), 34)
    title_width, title_height = estimate_text_size(title, TITLE_FONT_SIZE, min_width=320)
    title_width = min(title_width, 720)
    builder.add_text("diagram-title", title, CANVAS_MARGIN, CANVAS_MARGIN, TITLE_FONT_SIZE, width=title_width, align="left")

    subtitle = spec.get("subtitle")
    if not subtitle:
        subtitle = diagram_kind_label(spec.get("diagram_kind"))
        scope = spec.get("scope")
        if scope:
            subtitle = f"{subtitle} | {scope}"

    subtitle = wrap_text(subtitle, MAX_SUBTITLE_CHARS)
    _, subtitle_height = estimate_text_size(subtitle, SUBTITLE_FONT_SIZE)
    builder.add_text(
        "diagram-subtitle",
        subtitle,
        CANVAS_MARGIN,
        CANVAS_MARGIN + title_height + 8,
        SUBTITLE_FONT_SIZE,
        width=520,
        height=subtitle_height,
        align="left",
    )
    return CANVAS_MARGIN + title_height + 8 + subtitle_height + TOP_SECTION_GAP


def _collect_evidence_sources(spec: dict[str, Any]) -> list[str]:
    """Return the distinct evidence_source values used in nodes and edges, preserving order."""
    seen: set[str] = set()
    sources: list[str] = []
    for item in list(spec.get("nodes", [])) + list(spec.get("edges", [])):
        src = item.get("evidence_source")
        if src and src not in seen:
            sources.append(src)
            seen.add(src)
    return [s for s in EVIDENCE_STYLES if s in seen]


def _has_evidence_metadata(spec: dict[str, Any]) -> bool:
    """Return True if any node or edge carries evidence_source."""
    for item in list(spec.get("nodes", [])) + list(spec.get("edges", [])):
        if item.get("evidence_source"):
            return True
    return False


def add_legend(
    builder: SceneBuilder,
    spec: dict[str, Any],
    placements: dict[str, NodePlacement],
    content_width: int,
) -> None:
    if spec.get("show_legend", True) is False:
        return

    used_roles = [role for role in ROLE_ORDER if any(normalize_role(node.get("role")) == role for node in spec["nodes"])]
    used_edge_styles = [kind for kind in EDGE_STYLES if any(edge.get("kind", "sync") == kind for edge in spec["edges"])]

    show_evidence = spec.get("show_evidence", True) is not False and _has_evidence_metadata(spec)
    used_evidence = _collect_evidence_sources(spec) if show_evidence else []

    if not used_roles and not used_edge_styles and not used_evidence:
        return

    evidence_section_height = (len(used_evidence) * LEGEND_ITEM_HEIGHT + 28) if used_evidence else 0
    legend_height = 60 + (len(used_roles) * LEGEND_ITEM_HEIGHT) + (len(used_edge_styles) * LEGEND_ITEM_HEIGHT) + evidence_section_height
    legend_x = content_width + 120
    legend_y = CANVAS_MARGIN
    builder.add_group(GroupPlacement("legend", "Legend", legend_x, legend_y, LEGEND_WIDTH, legend_height, DEFAULT_GROUP_STROKE))

    current_y = legend_y + 44
    for role in used_roles:
        style = ROLE_STYLES[role]
        sample = builder.base_element(f"legend-role-{role}", "rectangle", legend_x + 18, current_y, 26, 18)
        sample.update({"strokeColor": style["stroke"], "backgroundColor": style["fill"], "roundness": {"type": 3}})
        builder.elements.append(sample)
        builder.add_text(
            f"legend-role-{role}-text",
            style["label"],
            legend_x + 56,
            current_y - 2,
            LEGEND_FONT_SIZE,
            width=210,
            height=20,
        )
        current_y += LEGEND_ITEM_HEIGHT

    for edge_kind in used_edge_styles:
        style = EDGE_STYLES[edge_kind]
        arrow = builder.base_element(f"legend-edge-{edge_kind}", "arrow", legend_x + 18, current_y + 9, 32, 0)
        arrow.update(
            {
                "strokeColor": style["strokeColor"],
                "backgroundColor": "transparent",
                "strokeStyle": style["strokeStyle"],
                "roundness": {"type": 2},
                "points": [[0, 0], [32, 0]],
                "lastCommittedPoint": None,
                "startBinding": None,
                "endBinding": None,
                "startArrowhead": None,
                "endArrowhead": "arrow",
                "elbowed": False,
            }
        )
        builder.elements.append(arrow)
        builder.add_text(
            f"legend-edge-{edge_kind}-text",
            style["label"],
            legend_x + 62,
            current_y - 2,
            LEGEND_FONT_SIZE,
            width=210,
            height=20,
        )
        current_y += LEGEND_ITEM_HEIGHT

    # Evidence source legend section
    if used_evidence:
        current_y += 10
        builder.add_text(
            "legend-evidence-header",
            "Evidence",
            legend_x + 18,
            current_y,
            LEGEND_FONT_SIZE,
            width=210,
            height=20,
        )
        current_y += 18
        for ev_source in used_evidence:
            ev_style = EVIDENCE_STYLES[ev_source]
            builder.add_text(
                f"legend-ev-{ev_source}",
                f"{ev_style['marker']}  {ev_style['label']}",
                legend_x + 18,
                current_y,
                LEGEND_FONT_SIZE,
                width=210,
                height=20,
                color=ev_style["color"],
            )
            current_y += LEGEND_ITEM_HEIGHT

    note = wrap_text("Relationship labels should describe intent.", 32)
    _, note_height = estimate_text_size(note, LEGEND_FONT_SIZE)
    builder.add_text("legend-note", note, legend_x, legend_y + legend_height + 12, LEGEND_FONT_SIZE, width=LEGEND_WIDTH, height=note_height)


def add_notes(builder: SceneBuilder, spec: dict[str, Any], placements: dict[str, NodePlacement]) -> None:
    notes = spec.get("notes") or []
    if not notes:
        return

    base_y = max((placement.y + placement.height) for placement in placements.values()) + 56
    for index, note in enumerate(notes):
        text = wrap_text(note["text"] if isinstance(note, dict) else str(note), MAX_NOTE_CHARS)
        _, note_height = estimate_text_size(text, LABEL_FONT_SIZE)
        builder.add_text(
            f"diagram-note-{index}",
            text,
            CANVAS_MARGIN,
            base_y + (index * (note_height + 12)),
            LABEL_FONT_SIZE,
            width=720,
            height=note_height,
        )


def add_evidence_notes(builder: SceneBuilder, spec: dict[str, Any], placements: dict[str, NodePlacement]) -> None:
    """Append an evidence summary note below the diagram when evidence metadata is present."""
    if spec.get("show_evidence", True) is False or not _has_evidence_metadata(spec):
        return

    # Build a compact summary: count items by evidence_source and confidence
    source_counts: dict[str, int] = defaultdict(int)
    confidence_counts: dict[str, int] = defaultdict(int)
    for item in list(spec.get("nodes", [])) + list(spec.get("edges", [])):
        src = item.get("evidence_source")
        conf = item.get("confidence")
        if src:
            source_counts[src] += 1
        if conf:
            confidence_counts[conf] += 1

    lines = ["Evidence Summary:"]
    for src in EVIDENCE_STYLES:
        if src in source_counts:
            lines.append(f"  {EVIDENCE_STYLES[src]['marker']} {EVIDENCE_STYLES[src]['label']}: {source_counts[src]}")
    for conf in ("high", "medium", "low"):
        if conf in confidence_counts:
            lines.append(f"  {conf.title()} confidence: {confidence_counts[conf]}")

    text = "\n".join(lines)
    base_y = max((p.y + p.height) for p in placements.values()) + 56
    # Offset below any existing notes
    existing_notes = spec.get("notes") or []
    if existing_notes:
        base_y += len(existing_notes) * 40

    _, text_height = estimate_text_size(text, LABEL_FONT_SIZE)
    builder.add_text(
        "evidence-summary",
        text,
        CANVAS_MARGIN,
        base_y,
        LABEL_FONT_SIZE,
        width=720,
        height=text_height,
        color="#495057",
    )


def build_scene(spec: dict[str, Any]) -> dict[str, Any]:
    validate_spec(spec)
    nodes = [dict(node, role=normalize_role(node.get("role"))) for node in spec["nodes"]]
    groups = complete_groups(spec, nodes)
    groups, overview_style = enrich_groups(spec, nodes, groups)
    ensure(groups, "Could not derive diagram groups.")

    builder = SceneBuilder(title=spec["title"])
    top_y = add_title_block(builder, spec)

    if spec.get("layout", "flow") == "flow":
        placements, group_placements, content_width, _ = layout_flow(spec, nodes, groups, top_y)
    else:
        placements, group_placements, content_width, _ = layout_layers(
            spec,
            nodes,
            groups,
            top_y,
            overview_style=overview_style,
        )
    placements = nudge_transit_obstacles(spec, placements, group_placements)
    edge_routes = plan_edge_routes(spec, placements)

    for group_placement in group_placements:
        builder.add_group(group_placement)

    elements_by_node: dict[str, dict[str, Any]] = {}
    for node in nodes:
        element = builder.add_node(placements[node["id"]])
        elements_by_node[node["id"]] = element

    for edge in spec["edges"]:
        builder.add_arrow(edge, placements, elements_by_node, route=edge_routes.get(edge_element_id(edge)))

    add_legend(builder, spec, placements, content_width)
    add_notes(builder, spec, placements)
    add_evidence_notes(builder, spec, placements)

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "excali-claude-builder",
        "elements": builder.elements,
        "appState": {
            "gridSize": 20,
            "viewBackgroundColor": "#ffffff",
            "name": spec["title"],
        },
        "files": {},
    }


def is_multi_view_spec(spec: dict[str, Any]) -> bool:
    """Return True if the spec uses the multi-view model format."""
    return isinstance(spec.get("model"), dict) and isinstance(spec.get("views"), list)


def compile_view(model: dict[str, Any], view: dict[str, Any], model_title: str) -> dict[str, Any]:
    """Compile a single view definition against the shared model into a builder-ready spec.

    Selects the subset of entities and relationships requested by the view,
    then emits a flat single-view spec that ``build_scene`` can render directly.
    """
    entities = model.get("entities", [])
    relationships = model.get("relationships", [])

    # Filter entities by view's entity_ids if specified
    entity_ids = view.get("entity_ids")
    if entity_ids is not None:
        entity_set = set(entity_ids)
        selected_entities = [e for e in entities if e["id"] in entity_set]
    else:
        selected_entities = list(entities)

    selected_ids = {e["id"] for e in selected_entities}

    # Filter relationships to those whose endpoints are both selected
    selected_relationships = [
        r for r in relationships
        if r["from"] in selected_ids and r["to"] in selected_ids
    ]

    # Build the flat single-view spec
    nodes = []
    for entity in selected_entities:
        node: dict[str, Any] = {}
        for key in ("id", "label", "role", "group", "node_type", "technology",
                     "description", "order", "shape",
                     "evidence_source", "confidence", "owner", "boundary", "runtime"):
            if key in entity:
                node[key] = entity[key]
        nodes.append(node)

    edges = []
    for rel in selected_relationships:
        edge: dict[str, Any] = {}
        for key in ("from", "to", "label", "kind", "sequence", "id",
                     "evidence_source", "confidence"):
            if key in rel:
                edge[key] = rel[key]
        edges.append(edge)

    compiled: dict[str, Any] = {
        "title": view.get("title") or model_title,
        "nodes": nodes,
        "edges": edges,
    }

    # Copy through view-level rendering options
    for key in ("view_mode", "subtitle", "diagram_kind", "layout", "direction", "scope",
                "overview_style", "show_legend", "show_evidence", "groups", "notes"):
        if key in view:
            compiled[key] = view[key]

    return compiled


DEFAULT_MAX_NODES = 15
DEFAULT_UNIQUE_SUFFIX_LENGTH = 6


def short_unique_id(length: int = DEFAULT_UNIQUE_SUFFIX_LENGTH) -> str:
    return uuid.uuid4().hex[:length]


def append_suffix_to_path(path: Path, suffix: str) -> Path:
    return path.with_name(f"{path.stem}-{suffix}{path.suffix}")


def view_readability_metrics(view_spec: dict[str, Any]) -> dict[str, float]:
    nodes = view_spec.get("nodes", [])
    edges = view_spec.get("edges", [])
    node_ids = {node["id"] for node in nodes}
    degree: dict[str, int] = defaultdict(int)

    for edge in edges:
        source_id = edge.get("from")
        target_id = edge.get("to")
        if source_id in node_ids:
            degree[source_id] += 1
        if target_id in node_ids and target_id != source_id:
            degree[target_id] += 1

    max_degree = max(degree.values(), default=0)
    overloaded_nodes = sum(1 for value in degree.values() if value >= MAX_READABLE_EDGE_DEGREE)
    edge_density = len(edges) / max(len(nodes), 1)
    edge_limit = max(int(len(nodes) * 1.5), len(nodes) + 4, DEFAULT_MAX_NODES + 4)

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "edge_density": edge_density,
        "max_degree": max_degree,
        "overloaded_nodes": overloaded_nodes,
        "edge_limit": edge_limit,
    }


def should_split_view(view_spec: dict[str, Any], max_nodes: int) -> bool:
    metrics = view_readability_metrics(view_spec)
    if metrics["node_count"] > max_nodes:
        return True

    risk_flags = 0
    if metrics["edge_count"] > metrics["edge_limit"]:
        risk_flags += 1
    if metrics["edge_density"] >= EDGE_SPLIT_DENSITY:
        risk_flags += 1
    if metrics["max_degree"] > MAX_READABLE_EDGE_DEGREE:
        risk_flags += 1
    if metrics["overloaded_nodes"] > MAX_READABLE_OVERLOADED_NODES:
        risk_flags += 1
    return risk_flags >= 2


def resolve_output_base(
    compiled_views: list[tuple[str, dict[str, Any]]],
    base_output: Path,
    *,
    unique_output: bool = False,
) -> Path:
    """Return an output base path that will not overwrite existing artifacts.

    When *unique_output* is true, a short unique suffix is always appended to the
    requested base filename. Otherwise, a suffix is only appended when the
    requested output path (or any derived multi-view artifact path) already
    exists on disk.
    """
    if unique_output:
        return append_suffix_to_path(base_output, short_unique_id())

    if len(compiled_views) == 1:
        return append_suffix_to_path(base_output, short_unique_id()) if base_output.exists() else base_output

    extension = base_output.suffix
    for view_id, _view_spec in compiled_views:
        candidate = base_output.parent / f"{base_output.stem}-{view_id}{extension}"
        if candidate.exists():
            return append_suffix_to_path(base_output, short_unique_id())
    return base_output


def auto_split_view(
    view_id: str,
    view_spec: dict[str, Any],
    max_nodes: int,
) -> list[tuple[str, dict[str, Any]]]:
    """Split a compiled view into overview + detail views when it exceeds budget.

    If the view is within the readability budget, returns it unchanged as a
    single-element list. Otherwise, returns an overview containing all nodes
    plus one detail view per group that has two or more nodes.
    """
    if not should_split_view(view_spec, max_nodes):
        return [(view_id, view_spec)]

    nodes = view_spec.get("nodes", [])

    # --- Build overview (keep all nodes, no split) ---
    overview_spec = dict(view_spec)
    overview_spec["title"] = view_spec.get("title", "Overview") + " — Overview"
    result: list[tuple[str, dict[str, Any]]] = [(f"{view_id}-overview", overview_spec)]

    # --- Build one detail view per group with 2+ nodes ---
    groups_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        groups_by_id[node.get("group", "default")].append(node)

    for group_id, group_nodes in groups_by_id.items():
        if len(group_nodes) < 2:
            continue

        group_node_ids = {n["id"] for n in group_nodes}
        detail_edges = [
            e for e in view_spec.get("edges", [])
            if e["from"] in group_node_ids or e["to"] in group_node_ids
        ]

        # Include nodes referenced by edges but outside this group
        referenced_ids = set()
        for e in detail_edges:
            referenced_ids.add(e["from"])
            referenced_ids.add(e["to"])
        extra_nodes = [
            n for n in nodes
            if n["id"] in referenced_ids and n["id"] not in group_node_ids
        ]

        group_label = group_id.replace("-", " ").title()
        detail_spec: dict[str, Any] = {
            "title": f"{view_spec.get('title', 'Detail')} — {group_label}",
            "nodes": list(group_nodes) + extra_nodes,
            "edges": detail_edges,
        }
        # Carry through rendering options
        for key in ("view_mode", "subtitle", "diagram_kind", "layout", "direction", "scope",
                     "overview_style", "show_legend", "show_evidence", "groups", "notes"):
            if key in view_spec:
                detail_spec[key] = view_spec[key]

        result.append((f"{view_id}-{slugify(group_id)}", detail_spec))

    return result if len(result) > 1 else [(view_id, view_spec)]


def compile_spec(spec: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Compile a spec into a list of (view_id, builder_ready_spec) pairs.

    For legacy single-view specs, returns one pair with view_id ``"default"``.
    For multi-view specs, returns one pair per view definition.
    Views that exceed ``max_nodes`` are automatically split into overview + detail
    artifacts.
    """
    if not is_multi_view_spec(spec):
        return [("default", spec)]

    model = spec["model"]
    views = spec["views"]
    model_title = spec.get("title", "Diagram")
    max_nodes = model.get("max_nodes") or DEFAULT_MAX_NODES

    if not views:
        raise ValueError("Multi-view spec must include at least one view in 'views'.")

    compiled_views: list[tuple[str, dict[str, Any]]] = []
    for view in views:
        view_id = view.get("view_id")
        if not view_id:
            raise ValueError("Each view must include a 'view_id'.")
        compiled = compile_view(model, view, model_title)
        compiled_views.extend(auto_split_view(view_id, compiled, max_nodes))

    return compiled_views


def build_artifacts(
    compiled_views: list[tuple[str, dict[str, Any]]],
    base_output: Path,
) -> list[Path]:
    """Build .excalidraw artifacts from compiled views and write them to disk.

    For a single compiled view, writes directly to *base_output*.
    For multiple compiled views, writes one artifact per view using the requested
    base filename: ``{base_output.stem}-{view_id}{base_output.suffix}``.

    Returns the list of artifact paths that were written.
    """
    base_output.parent.mkdir(parents=True, exist_ok=True)
    artifacts: list[Path] = []

    if len(compiled_views) == 1:
        _view_id, view_spec = compiled_views[0]
        scene = build_scene(view_spec)
        base_output.write_text(json.dumps(scene, indent=2), encoding="utf-8")
        artifacts.append(base_output)
    else:
        for view_id, view_spec in compiled_views:
            scene = build_scene(view_spec)
            artifact_name = f"{base_output.stem}-{view_id}{base_output.suffix}"
            artifact_path = base_output.parent / artifact_name
            artifact_path.write_text(json.dumps(scene, indent=2), encoding="utf-8")
            artifacts.append(artifact_path)

    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a .excalidraw diagram from a structured JSON spec.")
    parser.add_argument("spec", help="Path to the diagram spec JSON file.")
    parser.add_argument("--output", help="Output .excalidraw path. Defaults to <spec>.excalidraw")
    parser.add_argument(
        "--unique-output",
        action="store_true",
        help="Append a short unique suffix to the output filename(s). Useful for keeping multiple runs of the same topic.",
    )
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"Spec not found: {spec_path}", file=sys.stderr)
        return 1

    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        compiled_views = compile_spec(spec)
    except Exception as exc:  # pragma: no cover - surfaced to user directly
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    base_output = Path(args.output) if args.output else spec_path.with_suffix(".excalidraw")
    base_output = resolve_output_base(compiled_views, base_output, unique_output=args.unique_output)

    try:
        artifacts = build_artifacts(compiled_views, base_output)
        for artifact_path in artifacts:
            print(artifact_path)
    except Exception as exc:  # pragma: no cover - surfaced to user directly
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
