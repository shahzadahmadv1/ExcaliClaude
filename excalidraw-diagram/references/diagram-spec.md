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

---

## Shared Semantic Model

The shared model is the canonical representation of a system's entities and relationships. One model can produce multiple diagram views. When only one view is needed, the model and view can be combined in a single spec (the legacy single-view format).

### Model Top-Level Fields

```json
{
  "title": "Payment System",
  "model": {
    "entities": [],
    "relationships": [],
    "scope_filter": null,
    "max_nodes": null,
    "detail_level": "standard",
    "audience": "technical"
  },
  "views": []
}
```

| Field | Required | Values | Purpose |
|------|----------|--------|---------|
| `title` | Yes | string | System or project title shared across views |
| `model` | No | object | Shared semantic model. Omit to use legacy single-view format |
| `views` | No | array | One or more view definitions derived from the model |

When `model` is omitted, the spec is treated as a legacy single-view spec and processed exactly as before.

### Model Object Fields

| Field | Required | Values | Purpose |
|------|----------|--------|---------|
| `entities` | Yes | array | Canonical components, services, and systems |
| `relationships` | Yes | array | Canonical connections between entities |
| `scope_filter` | No | string or array of strings | Limit views to a subset of entities by id or group. Currently treated as planning metadata; the builder does not enforce filtering automatically. |
| `max_nodes` | No | integer | Advisory node budget per view; triggers auto-split when exceeded |
| `detail_level` | No | `minimal`, `standard`, `detailed` | How much metadata to surface in views (default: `standard`). Currently treated as planning metadata; the builder does not change rendering directly from this field. |
| `audience` | No | `technical`, `executive`, `mixed` | Influences label verbosity and abstraction level (default: `technical`). Currently treated as planning metadata; the builder does not change rendering directly from this field. |

### Entity Fields

Entities are the shared pool of components that views can select from.

```json
{
  "id": "auth-service",
  "label": "Auth Service",
  "role": "service",
  "group": "services",
  "node_type": "Container",
  "technology": "ASP.NET Core",
  "description": "Validates credentials and issues sessions",
  "order": 3,
  "evidence_source": "code",
  "confidence": "high",
  "owner": "platform-team",
  "boundary": "internal",
  "runtime": "kubernetes"
}
```

| Field | Required | Purpose |
|------|----------|---------|
| `id` | Yes | Unique stable identifier |
| `label` | Yes | Primary name |
| `role` | Yes | Visual style bucket (see Supported Roles below) |
| `group` | No | Logical grouping / swimlane membership |
| `node_type` | No | Secondary classification |
| `technology` | No | Tech/protocol/runtime |
| `description` | No | Short user-facing explanation |
| `order` | No | Stable fallback ordering |
| `evidence_source` | No | `code`, `inferred`, `user-specified` — where this entity was discovered |
| `confidence` | No | `high`, `medium`, `low` — how certain the discovery is |
| `owner` | No | Team or individual responsible |
| `boundary` | No | `internal`, `external`, `shared` — trust/org boundary |
| `runtime` | No | Deployment or runtime environment |

### Relationship Fields

Relationships are the shared pool of connections that views can select from.

```json
{
  "from": "auth-service",
  "to": "user-db",
  "label": "Read user",
  "kind": "read",
  "sequence": 3,
  "evidence_source": "code",
  "confidence": "high"
}
```

| Field | Required | Purpose |
|------|----------|---------|
| `from` | Yes | Source entity id |
| `to` | Yes | Target entity id |
| `label` | No | Relationship label |
| `kind` | No | Line style bucket (see Supported Edge Kinds below) |
| `sequence` | No | Ordering for dynamic flows |
| `id` | No | Optional stable id override |
| `evidence_source` | No | `code`, `inferred`, `user-specified` |
| `confidence` | No | `high`, `medium`, `low` |

### Evidence Metadata

Evidence fields help downstream views and reports distinguish what is known from what is guessed.

**Allowed `evidence_source` values:** `code`, `inferred`, `user-specified`
- `code` — derived directly from source code analysis
- `inferred` — deduced from patterns, naming, or conventions but not directly confirmed
- `user-specified` — provided explicitly by the user

**Allowed `confidence` values:** `high`, `medium`, `low`

---

## View Definitions

A view selects a subset of model entities and relationships and renders them as one diagram.

### View Object Fields

```json
{
  "view_id": "auth-overview",
  "view_mode": "overview",
  "title": "Authentication Flow",
  "subtitle": "Dynamic diagram | Browser login path",
  "diagram_kind": "dynamic",
  "layout": "flow",
  "direction": "vertical",
  "overview_style": "auto",
  "scope": "ExcaliClaude sample",
  "show_legend": true,
  "entity_ids": null,
  "groups": [],
  "notes": []
}
```

| Field | Required | Values | Purpose |
|------|----------|--------|---------|
| `view_id` | Yes | string | Unique identifier for this view; used in artifact naming |
| `view_mode` | Yes | `overview`, `focused-flow`, `drill-down`, `scenario-pack` | The type of view to render |
| `title` | No | string | View-specific title (falls back to model title) |
| `subtitle` | No | string | Short scope/intent line |
| `diagram_kind` | No | `dynamic`, `container`, `component`, `context`, `architecture`, `deployment`, `data-flow`, `trust-boundary`, `dependency-map` | Abstraction level |
| `layout` | No | `flow`, `layers` | Layout algorithm |
| `direction` | No | `vertical`, `horizontal` | Flow direction |
| `overview_style` | No | `auto`, `pure-layers`, `core-with-sides` | For layered overview/context/container views, whether messaging and external systems stay as rows or move to side columns |
| `scope` | No | string | Optional scope text for the subtitle |
| `show_legend` | No | boolean | Hide only when the diagram is trivially obvious |
| `show_evidence` | No | boolean | Show or hide evidence summary cues when evidence metadata is present (default: `true`) |
| `entity_ids` | No | array of strings | Subset of model entity ids to include; null means all |
| `groups` | No | array | Ordered swimlanes/layers for this view |
| `notes` | No | array | Short annotations for this view |

### Supported View Modes

- **`overview`** — High-level system map. Shows all major entities, hides internal detail. Good for "what exists" questions.
- **`focused-flow`** — A single runtime or request path through the system. Good for "what happens when" questions.
- **`drill-down`** — Detailed view of one service, phase, or subsystem. Good for "how does X work internally" questions.
- **`scenario-pack`** — Emits an overview plus one or more focused/drill-down views as separate artifacts. Good for comprehensive documentation.

### Scenario Pack

When `view_mode` is `scenario-pack`, the view acts as a container. The compiler generates:

1. One overview artifact from the full model.
2. One artifact per additional view defined in the `views` array.

Artifact naming follows the requested output stem: `{output_stem}-{view_id}.excalidraw`

---

## Legacy Single-View Format

When the spec omits `model` and `views`, it is treated as a single-view spec. This is the original format and remains fully supported.

### Required Top-Level Fields

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

### Top-Level Fields

| Field | Required | Values | Purpose |
|------|----------|--------|---------|
| `title` | Yes | string | Diagram title shown on canvas |
| `subtitle` | No | string | Short scope/intent line under the title |
| `diagram_kind` | No | `dynamic`, `container`, `component`, `context`, `architecture`, `deployment`, `data-flow`, `trust-boundary`, `dependency-map` | Controls the subtitle and the intended abstraction |
| `layout` | No | `flow`, `layers` | `flow` for runtime/request paths, `layers` for static architecture |
| `direction` | No | `vertical`, `horizontal` | Flow direction for `layout: flow` |
| `overview_style` | No | `auto`, `pure-layers`, `core-with-sides` | Hybrid overview behavior for `layout: layers` |
| `scope` | No | string | Optional scope text for the subtitle |
| `show_legend` | No | boolean | Hide only when the diagram is trivially obvious |
| `show_evidence` | No | boolean | Show or hide evidence summary cues when evidence metadata is present (default: `true`) |
| `groups` | No | array | Ordered swimlanes/layers |
| `nodes` | Yes | array | Components/systems shown in the diagram |
| `edges` | Yes | array | Relationships and flow steps |
| `notes` | No | array | Short annotations shown below the main canvas |

## Groups

Use groups to create swimlanes or layers. Order them exactly as you want them rendered.

```json
[
  { "id": "client", "label": "Client", "placement": "side-left" },
  { "id": "services", "label": "Application" },
  { "id": "data", "label": "Data" },
  { "id": "messaging", "label": "Async Backbone", "placement": "side-right" }
]
```

Fields:

- `id`: machine-safe identifier
- `label`: human-readable container title
- `strokeColor`: optional custom border color
- `placement`: optional `layer`, `side-left`, or `side-right`

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
- `host`
- `container-runtime`
- `network`
- `queue`
- `topic`
- `trust-zone`
- `untrusted-zone`
- `dmz`
- `library`

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
- `publish`
- `subscribe`
- `deploy`
- `data-flow`
- `depends-on`
- `imports`
- `trust-boundary`

## Guidance

- Prefer 6-10 primary nodes per diagram.
- Split large flows into overview + detail diagrams instead of cramming everything into one canvas.
- Use `layout: flow` for "what happens when" questions.
- Use `layout: layers` for "what exists and how it is grouped" questions.
- For layered architecture overviews, prefer `overview_style: core-with-sides` when external systems or messaging would otherwise become full-width rows.
- Use side placements for communication partners and async backbones, not for core owned tiers.
- Use real class/service/system names when the codebase was explored.
- Keep descriptions short enough to fit in 2-3 lines.
- When producing multiple views from one model, give each view a unique `view_id`.
- Use `evidence_source` and `confidence` on entities and relationships when discovery data is available.
- Set `max_nodes` to trigger automatic splitting for large systems.
- Treat `scope_filter`, `detail_level`, and `audience` as planning and selection metadata unless your tooling explicitly implements them.

## Examples

- [enhanced-auth-flow.spec.json](./examples/enhanced-auth-flow.spec.json) — legacy single-view sample
- [multi-view-auth.spec.json](./examples/multi-view-auth.spec.json) — multi-view model sample
- [overview-example.spec.json](./examples/overview-example.spec.json) — overview view mode with evidence metadata
- [focused-flow-example.spec.json](./examples/focused-flow-example.spec.json) — focused-flow view mode with scope controls
- [drill-down-example.spec.json](./examples/drill-down-example.spec.json) — drill-down view mode for service internals
- [scenario-pack-example.spec.json](./examples/scenario-pack-example.spec.json) — scenario-pack with overview + multiple focused flows
