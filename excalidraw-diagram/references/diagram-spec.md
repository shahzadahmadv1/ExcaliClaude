# Diagram Spec Reference

Use this file when preparing a diagram for `build_excalidraw_diagram.py`.

## Purpose

Do not generate raw Excalidraw coordinates first. Generate a compact semantic spec, then hand it to the builder.

This keeps Claude focused on:

- choosing the right diagram scope
- naming the real components and relationships
- selecting the right groups and labels
- keeping the diagram small enough to read

The builder handles:

- box sizing
- lane/container sizing
- positioning
- legends
- relationship label placement

## Required Top-Level Fields

```json
{
  "title": "Authentication Flow",
  "diagram_kind": "dynamic",
  "layout": "flow",
  "direction": "vertical",
  "nodes": [],
  "edges": []
}
```

## Top-Level Fields

| Field | Required | Values | Purpose |
|------|----------|--------|---------|
| `title` | Yes | string | Diagram title shown on canvas |
| `subtitle` | No | string | Short scope/intent line under the title |
| `diagram_kind` | No | `dynamic`, `container`, `component`, `context`, `architecture` | Controls the subtitle and the intended abstraction |
| `layout` | No | `flow`, `layers` | `flow` for runtime/request paths, `layers` for static architecture |
| `direction` | No | `vertical`, `horizontal` | Flow direction for `layout: flow` |
| `scope` | No | string | Optional scope text for the subtitle |
| `show_legend` | No | boolean | Hide only when the diagram is trivially obvious |
| `groups` | No | array | Ordered swimlanes/layers |
| `nodes` | Yes | array | Components/systems shown in the diagram |
| `edges` | Yes | array | Relationships and flow steps |
| `notes` | No | array | Short annotations shown below the main canvas |

## Groups

Use groups to create swimlanes or layers. Order them exactly as you want them rendered.

```json
[
  { "id": "client", "label": "Client" },
  { "id": "services", "label": "Application" },
  { "id": "data", "label": "Data" }
]
```

Fields:

- `id`: machine-safe identifier
- `label`: human-readable container title
- `strokeColor`: optional custom border color

## Nodes

Every node should explain what it is, not just name it.

```json
{
  "id": "auth-service",
  "label": "Auth Service",
  "role": "service",
  "group": "services",
  "node_type": "Container",
  "technology": "ASP.NET Core",
  "description": "Validates credentials and issues sessions",
  "order": 3
}
```

### Node Fields

| Field | Required | Purpose |
|------|----------|---------|
| `id` | Yes | Unique stable identifier |
| `label` | Yes | Primary name rendered in the box |
| `role` | Yes | Visual style bucket |
| `group` | No | Swimlane/layer membership |
| `node_type` | No | Secondary classification shown under the name |
| `technology` | No | Tech/protocol/runtime shown with the type |
| `description` | No | Short user-facing explanation |
| `shape` | No | Set to `decision` for decision diamonds |
| `order` | No | Stable fallback ordering |

### Supported Roles

- `client`
- `api`
- `service`
- `database`
- `external`
- `infrastructure`
- `decision`

## Edges

Use short relationship labels that explain intent. Do not leave important arrows unlabeled.

```json
{
  "from": "auth-service",
  "to": "user-db",
  "sequence": 3,
  "label": "Read user",
  "kind": "read"
}
```

### Edge Fields

| Field | Required | Purpose |
|------|----------|---------|
| `from` | Yes | Source node id |
| `to` | Yes | Target node id |
| `label` | No | Relationship label shown near the arrow |
| `sequence` | No | Prepended to the label for dynamic flows |
| `kind` | No | Line style bucket |
| `id` | No | Optional stable id override |

### Supported Edge Kinds

- `sync`
- `async`
- `read`
- `write`
- `conditional-yes`
- `conditional-no`

## Guidance

- Prefer 6-10 primary nodes per diagram.
- Split large flows into overview + detail diagrams instead of cramming everything into one canvas.
- Use `layout: flow` for "what happens when" questions.
- Use `layout: layers` for "what exists and how it is grouped" questions.
- Use real class/service/system names when the codebase was explored.
- Keep descriptions short enough to fit in 2-3 lines.

## Example

See [enhanced-auth-flow.spec.json](./examples/enhanced-auth-flow.spec.json) for a full sample.
