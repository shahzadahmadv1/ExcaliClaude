---
name: excalidraw-diagram
description: Generates Excalidraw diagrams for architecture and existing-code flows. Use when the user asks to explain, visualize, or draw a system, request path, runtime interaction, or codebase-backed flow. Explores the codebase when needed, writes a structured diagram spec first, then builds polished .excalidraw output with validation and preview rendering.
---

# Excalidraw Diagram Generator

Generate Excalidraw diagrams that are readable, code-aware, and visually consistent.

Do not freehand raw Excalidraw JSON unless the builder is unavailable. The default path is:

1. discover the real flow
2. choose the right diagram level
3. write a compact diagram spec
4. build the `.excalidraw` file with the builder script
5. validate and preview it

## Trigger Logic

Activate when the user asks to create, explain with, visualize, or draw:

- an architecture
- a flow
- a request path
- a runtime interaction
- an existing code path
- a service/system overview

Examples:

- "Explain the auth flow with a diagram"
- "Draw the payment processing path"
- "Visualize the customer acquisition architecture"
- "Show me how this service talks to Redis and Postgres"

## Codebase Discovery

### Explore The Codebase When

- the user is asking about an existing system
- the request mentions a repo, solution, project, namespace, service, or feature
- the user wants an explanation of "how it works now"
- the flow likely exists in code but the prompt does not name every component explicitly

### Skip Discovery When

- the user is designing something new
- the user explicitly asks for a generic or conceptual template
- the prompt already contains all components and relationships needed for the diagram

### Discovery Procedure

1. Identify the repo or project path. If none is given, use the current working directory.
2. Read `references/codebase-discovery-prompt.md`.
3. Dispatch an Explore agent and ask it to return the structured output from that prompt.
4. Use the discovered components and flow sequence as the source of truth.
5. If no useful codebase evidence is found, fall back to a conceptual diagram and state that clearly.

## Diagram Selection

Read `references/diagram-quality-bar.md` before choosing the diagram.

Use a C4-inspired level:

- `dynamic` for request paths, runtime flows, and "what happens when" explanations
- `container` for service/application composition
- `component` for internals of a specific service/container
- `context` for high-level system boundaries
- `architecture` for broad layered overviews that do not fit neatly into one C4 level

If the user asks for multiple levels at once, generate the higher-level overview first and offer a follow-up detail diagram.

## Required References

Read these before writing the spec:

- `references/diagram-quality-bar.md`
- `references/diagram-spec.md`
- `references/color-palette.md`

Use these as examples when helpful:

- `references/examples/enhanced-auth-flow.spec.json`
- `references/examples/simple-flow.excalidraw`
- `references/examples/architecture.excalidraw`

## Generation Process

### Step 1: Decide The Smallest Useful Diagram

Keep the diagram focused on one primary question.

- For flows, show one main narrative.
- For architectures, show one abstraction level at a time.
- If the canvas would need more than about 10 primary nodes, split into overview + detail diagrams.

### Step 2: Build A Semantic Diagram Spec

Write a JSON spec first. Do not start with raw Excalidraw coordinates.

The spec must include:

- `title`
- `diagram_kind`
- `layout`
- `direction` for flow diagrams
- ordered `groups`
- `nodes`
- `edges`

Quality rules:

- Give every important arrow a label.
- Use real class/service/system names when discovery was performed.
- Include `node_type`, `technology`, and short `description` fields when they help explain the flow.
- Use `sequence` on the main interactions in dynamic diagrams.
- Use `shape: "decision"` only for meaningful branches.

### Step 3: Save The Spec

Create:

```bash
mkdir -p docs/diagrams/specs
```

Save the spec to:

```text
docs/diagrams/specs/<date>-<topic>.diagram.json
```

### Step 4: Build The Excalidraw File

Run:

```bash
python <skill-dir>/references/build_excalidraw_diagram.py <spec-file> --output docs/diagrams/<date>-<topic>.excalidraw
```

The builder handles layout, containers, legends, node sizing, and arrow label placement.

### Step 5: Validate Structure

Run:

```bash
python <skill-dir>/references/validate_excalidraw.py <diagram-file>
```

If validation fails, fix the spec first and rebuild. Do not hand-edit raw JSON unless the problem is obviously builder-specific.

### Step 6: Render Preview

Run:

```bash
python <skill-dir>/references/render_excalidraw.py <diagram-file>
```

If Playwright or browser rendering is unavailable:

- keep the `.excalidraw` file
- tell the user preview rendering was skipped

### Step 7: Visual Review

Check the preview for:

- crowded lanes or layers
- labels that are too vague
- unlabeled important arrows
- too many boxes for one story
- missing legend or unclear line styles

If the diagram is weak, edit the spec and rebuild. Prefer spec changes over raw JSON tweaks.

### Step 8: Done

Report:

- the `.excalidraw` path
- the spec path
- the preview path if rendering succeeded
- whether the diagram is codebase-accurate or conceptual

## Constraints

### Quality Bar

- Every diagram needs a title.
- Important relationships need labels.
- Every node should explain what it is, not just name it.
- Prefer 6-10 primary nodes.
- Split mixed abstraction levels instead of forcing them together.

### Complexity Limit

If the discovered flow is too large for one readable diagram:

1. create an overview diagram for the phase/story
2. create detail diagrams for the densest phase or service

Use suffixes such as:

- `<date>-<topic>-overview.excalidraw`
- `<date>-<topic>-phase-1.excalidraw`
- `<date>-<topic>-component-detail.excalidraw`

### Iteration Rule

Iterate on the spec at most 2 times unless the user asks for more refinement.

### Fallback

Only generate raw Excalidraw JSON directly if the builder script is broken or unavailable. If that happens, say so.
