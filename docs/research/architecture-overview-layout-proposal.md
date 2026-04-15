# Architecture Overview Layout Proposal

## Status

Proposal only. Not implemented in the spec contract or builder defaults yet.

## Problem

The current overview strategy treats all groups as horizontal layers. That works for internal tiers such as ingress, services, and persistence, but it breaks down when:

- external systems are shown as if they are an internal tier
- queues/topics are shown as a full-width layer instead of a communication backbone
- long-span relationships must cross through unrelated boxes in lower layers

This is both a semantic problem and a readability problem. The diagram implies that messaging and third-party systems are part of the same structural stack as the system's owned components, and it creates avoidable connector congestion.

## Research Basis

The proposal follows a few consistent ideas from official guidance:

- C4 system context diagrams place external actors and systems outside the system boundary rather than inside an internal tier.
- arc42 separates context from internal building blocks, which reinforces the idea that communication partners should not be modeled as if they are an internal application layer.
- C4 guidance for queues/topics recommends modeling messaging explicitly when it matters, rather than hiding it inside a generic horizontal band.
- Azure and AWS event-driven guidance both describe queues, topics, and event buses as communication infrastructure between producers and consumers rather than as a bottom application layer.

Sources:

- https://c4model.com/diagrams/system-context
- https://c4model.com/abstractions/queues-and-topics
- https://arc42.org/overview
- https://docs.arc42.org/section-5/
- https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/event-driven
- https://docs.aws.amazon.com/decision-guides/latest/sns-or-sqs-or-eventbridge/sns-or-sqs-or-eventbridge.html

## Recommendation

Keep `layout: "layers"` for architecture overviews, but extend it into a hybrid layout:

- internal system groups remain horizontal layers
- external systems move to left or right side columns
- messaging moves to a side backbone column by default

This keeps the mental model simple and avoids a full layout-mode rewrite.

## Goals

- Make architecture overviews read like system structure, not like a forced stack of unrelated bands.
- Reduce connector overlap by reserving separate side corridors for external and async traffic.
- Keep the change backwards-compatible with existing `layout: "layers"` views.
- Preserve explicit user control when a team really does want pure horizontal layers.

## Non-Goals

- Replace `layout: "flow"` for runtime narratives.
- Introduce a full obstacle-avoiding graph layout engine.
- Force one universal style for every architecture diagram.
- Reclassify deployment views, trust-boundary views, or drill-down internals.

## Proposed Spec Extension

### View-Level Hint

Add an optional `overview_style` field for overview/container/context/architecture views:

```json
{
  "view_mode": "overview",
  "diagram_kind": "architecture",
  "layout": "layers",
  "overview_style": "core-with-sides"
}
```

Allowed values:

- `auto` default behavior
- `pure-layers` current behavior
- `core-with-sides` internal layers plus side columns
- `brokered` producer -> broker/backbone -> consumer emphasis

### Group-Level Placement

Extend groups with an optional `placement` field:

```json
{
  "id": "messaging",
  "label": "Async Backbone",
  "placement": "side-right"
}
```

Allowed values:

- `layer` default horizontal tier
- `side-left`
- `side-right`

Optional future field:

- `zone`: `core`, `external`, `backbone`

`placement` is the only field required for the first implementation. `zone` is planning metadata unless the builder later needs different styling or labels.

## Default Inference Rules

Only apply these defaults when all of the following are true:

- `view_mode` is `overview`
- `diagram_kind` is `architecture`, `container`, or `context`
- `layout` is `layers`
- the user did not explicitly set `overview_style: "pure-layers"`

Inference order:

1. Respect any explicit `group.placement`.
2. Put groups dominated by `boundary: external` or `role: external` into a side column.
3. Put groups dominated by `queue`, `topic`, or async infrastructure roles into `side-right`.
4. Keep owned ingress/API groups in the top core layers.
5. Keep services/workers in the middle core layers.
6. Keep owned databases/persistence in the bottom core layers.

Side choice for external systems:

- use `side-left` for inbound actors and upstream callers
- use `side-right` for downstream providers and partner services
- if unclear, choose the side that minimizes crossings against the current core ordering

When to use `brokered` instead of `core-with-sides`:

- one broker or bus is the main architectural story
- most important relationships are async publish/subscribe
- the overview would otherwise show many producers and consumers all pointing into one side column

## Layout Behavior

### Core-With-Sides

This becomes the default architecture overview pattern.

Structure:

- center canvas: internal layers only
- left margin: inbound actors and external initiators
- right margin: async backbone and downstream external dependencies

Placement rules:

- lay out core groups with the existing `layout_layers()` algorithm
- reserve a left column and right column outside the core content width
- size side columns from node count and widest node, not from core lane width
- vertically align side nodes to the average Y of their main connected core nodes when possible

Routing rules:

- side-bound edges exit the source box toward the nearest outside corridor first
- vertical travel for side-bound edges happens in the side corridor, not through the core rows
- no unrelated route should use a side node as a transit obstacle
- long-span core-to-core edges keep using the exterior corridor rule already added for layered views

### Brokered

Use this when the event bus or messaging fabric is the point of the picture.

Structure:

- producers on the left
- broker/backbone in the center or center-right
- consumers on the right
- persistence beneath the relevant owned services, not beneath the broker unless the broker owns storage

Routing rules:

- producer edges enter the broker from one side
- consumer edges leave from the opposite side
- avoid direct producer-to-consumer arrows unless the relationship is semantically important

## Example

### Current Shape

```text
External Systems
Ingress
Processing
Messaging
Persistence
```

### Proposed Shape

```text
External In      Ingress
                 Processing
                 Persistence      Async Backbone      External Out
```

A compliance-style overview would likely become:

- top core row: event sources and owned entry points
- middle core row: Lambda functions, services, and workers
- bottom core row: DynamoDB and SQL Server
- right side: SQS queues and similar async infrastructure
- outer edges: external API consumers, email providers, third-party services

## Example Spec

```json
{
  "view_id": "architecture-overview",
  "view_mode": "overview",
  "diagram_kind": "architecture",
  "layout": "layers",
  "overview_style": "core-with-sides",
  "groups": [
    { "id": "ingress", "label": "Ingress" },
    { "id": "processing", "label": "Processing" },
    { "id": "persistence", "label": "Persistence" },
    { "id": "messaging", "label": "Async Backbone", "placement": "side-right" },
    { "id": "external-in", "label": "External Inputs", "placement": "side-left" },
    { "id": "external-out", "label": "External Services", "placement": "side-right" }
  ]
}
```

## Builder Changes

Phase 1 should stay small:

1. Extend group parsing to accept `placement`.
2. Add `overview_style` parsing for layered overview views.
3. Partition groups into `core`, `side-left`, and `side-right`.
4. Reuse `layout_layers()` for core groups.
5. Place side groups in reserved columns.
6. Route any edge touching a side group through the corresponding outer corridor.

Phase 2 can add auto-inference:

1. Infer placement from `boundary`, `role`, and edge kinds.
2. Choose `core-with-sides` automatically for likely architecture overviews.
3. Fall back to `pure-layers` when the view is already simple and uncluttered.

Phase 3 can tighten quality:

1. Add an overview fixture that mixes ingress, async messaging, persistence, and external systems.
2. Add validator warnings when external-heavy views are still rendered as pure layers.
3. Add geometric checks for edge-node intersection counts in side-column layouts.

## Prompt and Skill Changes

The skill should stop describing all architecture overviews as stacked tiers.

For overview prompts:

- identify owned internal tiers first
- classify external systems separately from internal layers
- classify messaging infrastructure separately from owned persistence
- choose `core-with-sides` unless the user explicitly asks for simple layers or a broker-centric picture

The discovery prompt should also preserve `boundary`, `role`, and async relationship kinds because those fields now drive layout, not just styling.

## Acceptance Criteria

The proposal is successful if an architecture overview:

- places external systems outside the internal stack by default
- keeps async infrastructure out of the persistence row unless that is explicitly intended
- prevents unrelated routes from crossing messaging or external boxes
- reduces overlap risk without requiring view splitting for every medium-sized system
- still lets the user force `pure-layers` when they want that style

## Recommendation For This Repo

Implement `core-with-sides` first, not `brokered`.

Reason:

- it is a smaller extension to the current model
- it directly addresses the compliance overview problems already observed
- it matches the most common architecture-overview expectation
- it preserves compatibility with existing `layout: "layers"` and only adds optional hints

If that works well, add `brokered` as a second overview pattern for event-centric systems.
