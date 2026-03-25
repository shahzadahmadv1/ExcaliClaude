#!/usr/bin/env python3
"""Build a polished .excalidraw scene from a structured diagram spec."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import textwrap
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
}

EDGE_STYLES = {
    "sync": {"strokeStyle": "solid", "strokeColor": "#495057", "label": "Sync / request"},
    "async": {"strokeStyle": "dashed", "strokeColor": "#495057", "label": "Async / event"},
    "read": {"strokeStyle": "dotted", "strokeColor": "#495057", "label": "Read / query"},
    "write": {"strokeStyle": "solid", "strokeColor": "#495057", "label": "Write / command"},
    "conditional-yes": {"strokeStyle": "solid", "strokeColor": "#2b8a3e", "label": "Yes branch"},
    "conditional-no": {"strokeStyle": "solid", "strokeColor": "#c92a2a", "label": "No branch"},
}

ROLE_ORDER = ["client", "api", "service", "database", "external", "infrastructure", "decision"]
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
    }
    return labels.get(kind, kind.title())


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
        background_color: str = "transparent",
        reserve_for_floating_labels: bool = False,
    ) -> dict[str, Any]:
        text_width, text_height = estimate_text_size(text, font_size, min_width=width or 0)
        item = self.base_element(element_id, "text", x, y, width or text_width, height or text_height)
        item.update(
            {
                "strokeColor": "#1e1e1e",
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

    def add_arrow(self, edge: dict[str, Any], placements: dict[str, NodePlacement], elements_by_node: dict[str, dict[str, Any]]) -> None:
        source = placements[edge["from"]]
        target = placements[edge["to"]]
        edge_kind = edge.get("kind", "sync")
        style = EDGE_STYLES.get(edge_kind, EDGE_STYLES["sync"])
        start_x, start_y, end_x, end_y = connection_points(source, target)
        points = arrow_points(start_x, start_y, end_x, end_y)
        dx = points[-1][0] - points[0][0]
        dy = points[-1][1] - points[0][1]

        arrow_id = edge.get("id") or f"edge-{edge['from']}-{edge['to']}-{slugify(edge.get('label', 'link'))}"
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
        for group in groups:
            lane_x[group["id"]] = current_x
            current_x += lane_sizes[group["id"]] + GROUP_GAP

        row_y: dict[int, int] = {}
        current_y = top_y
        for depth in range(max_depth + 1):
            row_y[depth] = current_y
            current_y += row_sizes[depth] + ROW_GAP

        content_bottom = top_y
        for group in groups:
            lane_left = lane_x[group["id"]]
            lane_width = lane_sizes[group["id"]]
            column = group_index[group["id"]]
            for depth in range(max_depth + 1):
                same_cell = sorted(cell_map.get((depth, column), []), key=lambda item: item.get("order", 0))
                if not same_cell:
                    continue
                cell_total = sum(node_dimensions(node)[0] for node in same_cell) + (COLUMN_GAP * (len(same_cell) - 1))
                cursor_x = int(lane_left + ((lane_width - cell_total) / 2))
                for node in same_cell:
                    width, height = node_dimensions(node)
                    x = cursor_x
                    y = int(row_y[depth] + ((row_sizes[depth] - height) / 2))
                    placements[node["id"]] = NodePlacement(node=node, x=x, y=y, width=width, height=height)
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

        return placements, group_placements, current_x - GROUP_GAP, content_bottom

    lane_y: dict[str, int] = {}
    current_y = top_y
    for group in groups:
        lane_y[group["id"]] = current_y
        current_y += lane_sizes[group["id"]] + GROUP_GAP

    column_x: dict[int, int] = {}
    current_x = CANVAS_MARGIN
    for depth in range(max_depth + 1):
        column_x[depth] = current_x
        current_x += row_sizes[depth] + ROW_GAP

    content_right = CANVAS_MARGIN
    for group in groups:
        lane_top = lane_y[group["id"]]
        lane_height = lane_sizes[group["id"]]
        column = group_index[group["id"]]
        for depth in range(max_depth + 1):
            same_cell = sorted(cell_map.get((depth, column), []), key=lambda item: item.get("order", 0))
            if not same_cell:
                continue
            cell_total = sum(node_dimensions(node)[1] for node in same_cell) + (COLUMN_GAP * (len(same_cell) - 1))
            cursor_y = int(lane_top + ((lane_height - cell_total) / 2))
            for node in same_cell:
                width, height = node_dimensions(node)
                x = int(column_x[depth] + ((row_sizes[depth] - width) / 2))
                y = cursor_y
                placements[node["id"]] = NodePlacement(node=node, x=x, y=y, width=width, height=height)
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

    return placements, group_placements, content_right, current_y - GROUP_GAP


def layout_layers(
    spec: dict[str, Any],
    nodes: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    top_y: int,
) -> tuple[dict[str, NodePlacement], list[GroupPlacement], int, int]:
    del spec
    group_nodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        node.setdefault("group", groups[0]["id"])
        group_nodes[node["group"]].append(node)

    placements: dict[str, NodePlacement] = {}
    group_placements: list[GroupPlacement] = []
    current_y = top_y
    max_right = CANVAS_MARGIN

    for group in groups:
        nodes_in_group = sorted(group_nodes.get(group["id"], []), key=lambda item: item.get("order", 0))
        if not nodes_in_group:
            continue

        node_sizes = [node_dimensions(node) for node in nodes_in_group]
        group_width = sum(width for width, _ in node_sizes) + (COLUMN_GAP * (len(node_sizes) - 1)) + (GROUP_PADDING_X * 2)
        header_height = 28
        group_height = max(height for _, height in node_sizes) + (GROUP_PADDING_Y * 2) + header_height

        cursor_x = CANVAS_MARGIN + GROUP_PADDING_X
        for node, (width, height) in zip(nodes_in_group, node_sizes):
            x = cursor_x
            y = int(current_y + header_height + ((group_height - header_height - height) / 2))
            placements[node["id"]] = NodePlacement(node=node, x=x, y=y, width=width, height=height)
            cursor_x += width + COLUMN_GAP

        group_placements.append(
            GroupPlacement(
                group_id=group["id"],
                label=group.get("label", group["id"].replace("-", " ").title()),
                x=CANVAS_MARGIN,
                y=current_y,
                width=group_width,
                height=group_height,
                stroke_color=group.get("strokeColor", DEFAULT_GROUP_STROKE),
            )
        )
        current_y += group_height + GROUP_GAP
        max_right = max(max_right, CANVAS_MARGIN + group_width)

    return placements, group_placements, max_right, current_y - GROUP_GAP


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
    if not used_roles and not used_edge_styles:
        return

    legend_height = 60 + (len(used_roles) * LEGEND_ITEM_HEIGHT) + (len(used_edge_styles) * LEGEND_ITEM_HEIGHT)
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


def build_scene(spec: dict[str, Any]) -> dict[str, Any]:
    validate_spec(spec)
    nodes = [dict(node, role=normalize_role(node.get("role"))) for node in spec["nodes"]]
    groups = complete_groups(spec, nodes)
    ensure(groups, "Could not derive diagram groups.")

    builder = SceneBuilder(title=spec["title"])
    top_y = add_title_block(builder, spec)

    if spec.get("layout", "flow") == "flow":
        placements, group_placements, content_width, _ = layout_flow(spec, nodes, groups, top_y)
    else:
        placements, group_placements, content_width, _ = layout_layers(spec, nodes, groups, top_y)

    for group_placement in group_placements:
        builder.add_group(group_placement)

    elements_by_node: dict[str, dict[str, Any]] = {}
    for node in nodes:
        element = builder.add_node(placements[node["id"]])
        elements_by_node[node["id"]] = element

    for edge in spec["edges"]:
        builder.add_arrow(edge, placements, elements_by_node)

    add_legend(builder, spec, placements, content_width)
    add_notes(builder, spec, placements)

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a .excalidraw diagram from a structured JSON spec.")
    parser.add_argument("spec", help="Path to the diagram spec JSON file.")
    parser.add_argument("--output", help="Output .excalidraw path. Defaults to <spec>.excalidraw")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"Spec not found: {spec_path}", file=sys.stderr)
        return 1

    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        scene = build_scene(spec)
    except Exception as exc:  # pragma: no cover - surfaced to user directly
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else spec_path.with_suffix(".excalidraw")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scene, indent=2), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
