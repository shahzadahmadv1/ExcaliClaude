# Excalidraw JSON Schema Reference

This document is the primary reference for generating valid Excalidraw `.excalidraw` files. All examples are copy-pasteable and complete.

---

## 1. File Scaffold

Every `.excalidraw` file is a JSON object with this top-level structure:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [],
  "appState": {
    "gridSize": 20,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `"excalidraw"` |
| `version` | number | Schema version, always `2` |
| `source` | string | Always `"https://excalidraw.com"` |
| `elements` | array | All diagram elements (rectangles, text, arrows, etc.) |
| `appState` | object | Canvas settings — `gridSize` and `viewBackgroundColor` are the only fields needed |
| `files` | object | Embedded images — always `{}` for generated diagrams |

### Minimal Complete File

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    {
      "id": "box-1",
      "type": "rectangle",
      "x": 100,
      "y": 100,
      "width": 200,
      "height": 80,
      "version": 1,
      "versionNonce": 1847293560,
      "seed": 390214823,
      "isDeleted": false,
      "updated": 1,
      "fillStyle": "solid",
      "strokeWidth": 2,
      "strokeStyle": "solid",
      "roughness": 1,
      "opacity": 100,
      "backgroundColor": "#e8f5e9",
      "strokeColor": "#43a047",
      "groupIds": [],
      "roundness": { "type": 3 },
      "boundElements": [],
      "angle": 0,
      "locked": false,
      "link": null
    }
  ],
  "appState": {
    "gridSize": 20,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

---

## 2. Common Element Properties

Every element (rectangle, text, arrow, ellipse, diamond, line) shares these properties.

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `id` | string | yes | — | Unique identifier. Use descriptive slugs like `"svc-auth"`, `"arrow-1"`, `"label-db"`. |
| `type` | string | yes | — | One of: `"rectangle"`, `"ellipse"`, `"diamond"`, `"text"`, `"arrow"`, `"line"` |
| `x` | number | yes | — | X position of the element's origin (top-left corner) |
| `y` | number | yes | — | Y position of the element's origin (top-left corner) |
| `width` | number | yes | — | Element width in pixels. Minimum 120 for boxes with labels. |
| `height` | number | yes | — | Element height in pixels. Minimum 60 for boxes with labels. |
| `version` | number | yes | 1 | Element version. Start at 1. |
| `versionNonce` | number | yes | — | Random integer for the collaboration/undo system. Use any large random int. |
| `seed` | number | yes | — | Random integer that controls the deterministic hand-drawn roughness pattern. Use any large random int. |
| `isDeleted` | boolean | no | `false` | Whether the element is soft-deleted. Always set to `false`. |
| `updated` | number | no | `1` | Timestamp. Use `1` for generated diagrams. |
| `fillStyle` | string | no | `"solid"` | Fill pattern. Use `"solid"` for clean readable fills. Other options: `"hachure"`, `"cross-hatch"`. |
| `strokeWidth` | number | no | `2` | Border width. `2` is the standard — visible but not heavy. |
| `strokeStyle` | string | no | `"solid"` | Border style. `"solid"` for normal borders, `"dashed"` for optional/async connections. |
| `roughness` | number | no | `1` | Hand-drawn feel. `0` = sharp, `1` = hand-drawn (preferred), `2` = very sketchy. |
| `opacity` | number | no | `100` | Element opacity, 0–100. Always use `100`. |
| `backgroundColor` | string | no | `"transparent"` | Fill color. Use role-based palette colors (e.g. `"#e8f5e9"` for services). |
| `strokeColor` | string | no | `"#1e1e1e"` | Border/outline color. Use role-based palette colors (e.g. `"#43a047"` for services). |
| `groupIds` | string[] | no | `[]` | Array of group IDs this element belongs to. See Group Mechanics below. |
| `roundness` | object or null | no | `null` | Set to `{ "type": 3 }` for rounded rectangles (service boxes, containers). `null` for sharp corners. |
| `boundElements` | array | no | `[]` | Array of `{ "id": "<element-id>", "type": "text" | "arrow" }` objects. See Container Binding Rules. |
| `angle` | number | no | `0` | Rotation angle in radians. Always use `0`. |
| `locked` | boolean | no | `false` | Whether the element is locked. Always use `false`. |
| `link` | string or null | no | `null` | Hyperlink. Always use `null`. |

---

## 3. Rectangle Element

Rectangles are used for services, components, and containers. Here is a complete service box with role-based coloring (Service/Backend role):

```json
{
  "id": "svc-auth",
  "type": "rectangle",
  "x": 200,
  "y": 100,
  "width": 180,
  "height": 80,
  "version": 1,
  "versionNonce": 1293847562,
  "seed": 482917365,
  "isDeleted": false,
  "updated": 1,
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "backgroundColor": "#e8f5e9",
  "strokeColor": "#43a047",
  "groupIds": [],
  "roundness": { "type": 3 },
  "boundElements": [
    { "id": "label-auth", "type": "text" },
    { "id": "arrow-1", "type": "arrow" }
  ],
  "angle": 0,
  "locked": false,
  "link": null
}
```

**Role color quick-reference for rectangles:**

| Role | `backgroundColor` | `strokeColor` |
|------|-------------------|---------------|
| Client/Frontend | `"#e3f2fd"` | `"#1e88e5"` |
| API/Gateway | `"#fff3e0"` | `"#ef6c00"` |
| Service/Backend | `"#e8f5e9"` | `"#43a047"` |
| Database/Storage | `"#fce4ec"` | `"#e53935"` |
| External/3rd Party | `"#f3e5f5"` | `"#8e24aa"` |
| Infrastructure | `"#eceff1"` | `"#546e7a"` |

---

## 4. Text Element

Text elements have additional properties beyond the common set. When a text element is placed inside a container (rectangle, ellipse, diamond), set `containerId` to the container's ID.

### Text Bound Inside a Container

```json
{
  "id": "label-auth",
  "type": "text",
  "x": 245,
  "y": 125,
  "width": 90,
  "height": 25,
  "version": 1,
  "versionNonce": 738291045,
  "seed": 192837465,
  "isDeleted": false,
  "updated": 1,
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "backgroundColor": "transparent",
  "strokeColor": "#1e1e1e",
  "groupIds": [],
  "roundness": null,
  "boundElements": [],
  "angle": 0,
  "locked": false,
  "link": null,
  "text": "Auth Service",
  "fontSize": 20,
  "fontFamily": 3,
  "textAlign": "center",
  "verticalAlign": "middle",
  "containerId": "svc-auth",
  "lineHeight": 1.25,
  "originalText": "Auth Service",
  "autoResize": true
}
```

### Text-Specific Properties

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `text` | string | yes | — | The displayed text content |
| `fontSize` | number | yes | `20` | Font size in pixels. Titles: 28, labels: 20, annotations: 16. |
| `fontFamily` | number | yes | `3` | Font ID. `3` = Cascadia/monospace (preferred). |
| `textAlign` | string | yes | `"center"` | Horizontal alignment: `"left"`, `"center"`, `"right"` |
| `verticalAlign` | string | yes | `"middle"` | Vertical alignment: `"top"`, `"middle"` |
| `containerId` | string or null | yes | `null` | ID of the parent container. `null` for free-standing text. |
| `lineHeight` | number | yes | `1.25` | Line height multiplier |
| `originalText` | string | yes | — | Same as `text`. Excalidraw uses this for word-wrap recovery. |
| `autoResize` | boolean | no | `true` | Whether the text auto-resizes to fit content. |

**Notes:**
- When `containerId` is set, `textAlign` and `verticalAlign` control positioning within the container.
- The `x`, `y`, `width`, `height` of bound text are approximate — Excalidraw recalculates them from the container. Set them to reasonable centered values.
- `strokeColor` for text is the text color. Use `"#1e1e1e"` (near-black) for all labels.
- `backgroundColor` for text should always be `"transparent"`.
- `roundness` for text should always be `null`.

### Free-Standing Text (Title / Annotation)

For titles or annotations not bound to a container, set `containerId` to `null`:

```json
{
  "id": "title-main",
  "type": "text",
  "x": 100,
  "y": 20,
  "width": 300,
  "height": 35,
  "version": 1,
  "versionNonce": 583920174,
  "seed": 847261935,
  "isDeleted": false,
  "updated": 1,
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "backgroundColor": "transparent",
  "strokeColor": "#1e1e1e",
  "groupIds": [],
  "roundness": null,
  "boundElements": [],
  "angle": 0,
  "locked": false,
  "link": null,
  "text": "Authentication Flow",
  "fontSize": 28,
  "fontFamily": 3,
  "textAlign": "left",
  "verticalAlign": "top",
  "containerId": null,
  "lineHeight": 1.25,
  "originalText": "Authentication Flow",
  "autoResize": true
}
```

---

## 5. Arrow Element

Arrows connect elements and show data flow. They use a `points` array for path definition and optional `startBinding`/`endBinding` for connecting to other elements.

### Straight Arrow (Horizontal)

```json
{
  "id": "arrow-1",
  "type": "arrow",
  "x": 380,
  "y": 140,
  "width": 120,
  "height": 0,
  "version": 1,
  "versionNonce": 1029384756,
  "seed": 564738291,
  "isDeleted": false,
  "updated": 1,
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "backgroundColor": "transparent",
  "strokeColor": "#495057",
  "groupIds": [],
  "roundness": { "type": 2 },
  "boundElements": [],
  "angle": 0,
  "locked": false,
  "link": null,
  "points": [
    [0, 0],
    [120, 0]
  ],
  "startBinding": {
    "elementId": "svc-auth",
    "focus": 0,
    "gap": 8
  },
  "endBinding": {
    "elementId": "svc-db",
    "focus": 0,
    "gap": 8
  },
  "startArrowhead": null,
  "endArrowhead": "arrow",
  "lastCommittedPoint": null
}
```

### Bent Arrow (L-Shape / Multi-Segment)

For arrows that need to route around elements, add intermediate waypoints to the `points` array:

```json
{
  "id": "arrow-2",
  "type": "arrow",
  "x": 380,
  "y": 140,
  "width": 200,
  "height": 120,
  "version": 1,
  "versionNonce": 847291036,
  "seed": 293847561,
  "isDeleted": false,
  "updated": 1,
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "backgroundColor": "transparent",
  "strokeColor": "#495057",
  "groupIds": [],
  "roundness": { "type": 2 },
  "boundElements": [],
  "angle": 0,
  "locked": false,
  "link": null,
  "points": [
    [0, 0],
    [100, 0],
    [100, 120],
    [200, 120]
  ],
  "startBinding": {
    "elementId": "svc-auth",
    "focus": 0,
    "gap": 8
  },
  "endBinding": {
    "elementId": "svc-cache",
    "focus": 0,
    "gap": 8
  },
  "startArrowhead": null,
  "endArrowhead": "arrow",
  "lastCommittedPoint": null
}
```

### Arrow-Specific Properties

| Property | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `points` | number[][] | yes | — | Array of `[x, y]` tuples relative to the element's origin. Minimum 2 points. |
| `startBinding` | object or null | no | `null` | `{ "elementId": "<id>", "focus": 0, "gap": 8 }` — connects start to an element |
| `endBinding` | object or null | no | `null` | `{ "elementId": "<id>", "focus": 0, "gap": 8 }` — connects end to an element |
| `startArrowhead` | string or null | no | `null` | Start decoration: `null` (none), `"arrow"`, `"dot"`, `"bar"` |
| `endArrowhead` | string or null | no | `"arrow"` | End decoration: `null`, `"arrow"` (standard), `"dot"`, `"bar"` |
| `lastCommittedPoint` | null | no | `null` | Internal state. Always use `null`. |

**Point patterns:**
- **Straight horizontal:** `[[0, 0], [dx, 0]]`
- **Straight vertical:** `[[0, 0], [0, dy]]`
- **Straight diagonal:** `[[0, 0], [dx, dy]]`
- **L-shape (right then down):** `[[0, 0], [dx, 0], [dx, dy]]`
- **L-shape (down then right):** `[[0, 0], [0, dy], [dx, dy]]`
- **Z-shape:** `[[0, 0], [dx/2, 0], [dx/2, dy], [dx, dy]]`

**Binding notes:**
- `focus`: Controls which side of the target the arrow aims at. `0` = center, negative = left/top, positive = right/bottom. Use `0` for most cases.
- `gap`: Pixel distance between the arrowhead and the element border. Use `8`.
- The arrow's `x, y` should be near the source element's edge. The first point is always `[0, 0]`.
- `width` and `height` should match the bounding box of the points array.
- Arrow `roundness` uses `{ "type": 2 }` (not type 3 like rectangles).

---

## 6. Container Binding Rules

Excalidraw uses a **bidirectional binding contract** between containers and their contents. Both sides must reference each other or the binding is broken.

### Text Inside a Box

For a label centered in a rectangle:

1. **Text element** must have `containerId` set to the rectangle's `id`.
2. **Rectangle element** must include the text in `boundElements`:

```
Rectangle "svc-auth":
  boundElements: [{ "id": "label-auth", "type": "text" }]

Text "label-auth":
  containerId: "svc-auth"
```

**Complete paired example:**

```json
[
  {
    "id": "svc-api",
    "type": "rectangle",
    "x": 100,
    "y": 100,
    "width": 180,
    "height": 80,
    "version": 1,
    "versionNonce": 1384729560,
    "seed": 829174365,
    "isDeleted": false,
    "updated": 1,
    "fillStyle": "solid",
    "strokeWidth": 2,
    "strokeStyle": "solid",
    "roughness": 1,
    "opacity": 100,
    "backgroundColor": "#fff3e0",
    "strokeColor": "#ef6c00",
    "groupIds": [],
    "roundness": { "type": 3 },
    "boundElements": [
      { "id": "label-api", "type": "text" },
      { "id": "arrow-to-db", "type": "arrow" }
    ],
    "angle": 0,
    "locked": false,
    "link": null
  },
  {
    "id": "label-api",
    "type": "text",
    "x": 140,
    "y": 125,
    "width": 100,
    "height": 25,
    "version": 1,
    "versionNonce": 293847102,
    "seed": 572910384,
    "isDeleted": false,
    "updated": 1,
    "fillStyle": "solid",
    "strokeWidth": 2,
    "strokeStyle": "solid",
    "roughness": 1,
    "opacity": 100,
    "backgroundColor": "transparent",
    "strokeColor": "#1e1e1e",
    "groupIds": [],
    "roundness": null,
    "boundElements": [],
    "angle": 0,
    "locked": false,
    "link": null,
    "text": "API Gateway",
    "fontSize": 20,
    "fontFamily": 3,
    "textAlign": "center",
    "verticalAlign": "middle",
    "containerId": "svc-api",
    "lineHeight": 1.25,
    "originalText": "API Gateway",
    "autoResize": true
  }
]
```

### Arrow Connected to a Box

For an arrow that starts at one box and ends at another:

1. **Arrow element** must have `startBinding.elementId` set to the source box's `id`.
2. **Arrow element** must have `endBinding.elementId` set to the target box's `id`.
3. **Source box** must include `{ "id": "<arrow-id>", "type": "arrow" }` in its `boundElements`.
4. **Target box** must include `{ "id": "<arrow-id>", "type": "arrow" }` in its `boundElements`.

```
Rectangle "svc-api":
  boundElements: [
    { "id": "label-api", "type": "text" },
    { "id": "arrow-to-db", "type": "arrow" }
  ]

Arrow "arrow-to-db":
  startBinding: { "elementId": "svc-api", "focus": 0, "gap": 8 }
  endBinding:   { "elementId": "svc-db",  "focus": 0, "gap": 8 }

Rectangle "svc-db":
  boundElements: [
    { "id": "label-db", "type": "text" },
    { "id": "arrow-to-db", "type": "arrow" }
  ]
```

### Binding Checklist

When generating elements, always verify:

- [ ] Every text element with a `containerId` has a matching entry in the container's `boundElements` array with `"type": "text"`.
- [ ] Every arrow with a `startBinding` or `endBinding` has a matching entry in the referenced element's `boundElements` array with `"type": "arrow"`.
- [ ] A container can have at most one bound text element.
- [ ] A container can have multiple bound arrows.
- [ ] Free-standing text has `containerId: null` and does NOT appear in any element's `boundElements`.

---

## 7. Diamond and Ellipse Elements

### Diamond (Decision Points)

Diamonds are used for conditional/decision nodes in flow diagrams. They share all common properties with rectangles. The key difference is `"type": "diamond"`.

```json
{
  "id": "decision-auth",
  "type": "diamond",
  "x": 250,
  "y": 300,
  "width": 160,
  "height": 120,
  "version": 1,
  "versionNonce": 847291563,
  "seed": 193847562,
  "isDeleted": false,
  "updated": 1,
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "backgroundColor": "#fff3e0",
  "strokeColor": "#ef6c00",
  "groupIds": [],
  "roundness": { "type": 2 },
  "boundElements": [
    { "id": "label-decision", "type": "text" },
    { "id": "arrow-yes", "type": "arrow" },
    { "id": "arrow-no", "type": "arrow" }
  ],
  "angle": 0,
  "locked": false,
  "link": null
}
```

**Diamond notes:**
- Use `roundness: { "type": 2 }` (not type 3).
- Make diamonds wider (160+) and taller (120+) than rectangles to fit labels inside the diamond shape.
- The label text binds via `containerId` the same way as rectangles.

### Ellipse (Start/End Points)

Ellipses mark start and end points in flow diagrams. Use `"type": "ellipse"`.

```json
{
  "id": "start-node",
  "type": "ellipse",
  "x": 280,
  "y": 50,
  "width": 100,
  "height": 60,
  "version": 1,
  "versionNonce": 293810475,
  "seed": 572839104,
  "isDeleted": false,
  "updated": 1,
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "backgroundColor": "#eceff1",
  "strokeColor": "#546e7a",
  "groupIds": [],
  "roundness": { "type": 2 },
  "boundElements": [
    { "id": "label-start", "type": "text" },
    { "id": "arrow-start-out", "type": "arrow" }
  ],
  "angle": 0,
  "locked": false,
  "link": null
}
```

**Ellipse notes:**
- Use `roundness: { "type": 2 }`.
- Text binding works the same as rectangles — set `containerId` on the label, include it in `boundElements`.
- Keep ellipses smaller than rectangles (100x60 is typical for "Start"/"End" labels).

---

## 8. Group Mechanics

Groups in Excalidraw are defined by shared `groupIds` values. There is no separate group object — grouping is implicit.

### How It Works

1. Choose a unique group ID string (e.g. `"group-auth-layer"`).
2. Add that ID to the `groupIds` array of every element that belongs to the group.
3. All elements sharing the same group ID are treated as a group — they select and move together.

### Example: Grouped Service Box with Label

```json
[
  {
    "id": "svc-users",
    "type": "rectangle",
    "x": 100,
    "y": 100,
    "width": 180,
    "height": 80,
    "groupIds": ["group-users"],
    "boundElements": [{ "id": "label-users", "type": "text" }],
    "..."
  },
  {
    "id": "label-users",
    "type": "text",
    "x": 140,
    "y": 125,
    "width": 100,
    "height": 25,
    "groupIds": ["group-users"],
    "containerId": "svc-users",
    "text": "User Service",
    "..."
  }
]
```

### Nested Groups

Elements can belong to multiple groups by having multiple entries in `groupIds`. The order matters — groups listed later are the outermost groups.

```json
{
  "groupIds": ["group-auth-box", "group-backend-layer"]
}
```

This element belongs to both the "auth-box" group and the outer "backend-layer" group.

### When to Use Groups

- **Service + label pairs:** Group a rectangle with its bound text label so they move together.
- **Layer boundaries:** Group all elements within a logical layer (e.g. all backend services).
- **Compound components:** Group a container rectangle with all its internal elements.

**Note:** Bound text (text with `containerId`) already moves with its container without grouping. Groups are mainly useful for moving multiple independent elements together or for creating visual layers.
