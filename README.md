<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://excalidraw.com/favicon.ico">
    <img src="https://excalidraw.com/favicon.ico" width="60" alt="Excalidraw">
  </picture>
  <span>&nbsp;&nbsp;&nbsp;+&nbsp;&nbsp;&nbsp;</span>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://claude.ai/favicon.ico">
    <img src="https://claude.ai/favicon.ico" width="60" alt="Claude">
  </picture>
</p>

<h1 align="center">ExcaliClaude</h1>

<p align="center">
  <strong>A Claude Code skill that generates Excalidraw architecture and flow diagrams from natural language.</strong>
</p>

<p align="center">
  <a href="#installation">Installation</a> &bull;
  <a href="#usage">Usage</a> &bull;
  <a href="#how-it-works">How It Works</a> &bull;
  <a href="#standalone-tools">Standalone Tools</a> &bull;
  <a href="#configuration">Configuration</a> &bull;
  <a href="#license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Skill-blueviolet?style=flat-square" alt="Claude Code Skill">
  <img src="https://img.shields.io/badge/Output-.diagram.json%20%2B%20.excalidraw-orange?style=flat-square" alt="Diagram Output">
  <img src="https://img.shields.io/badge/Views-Overview%20%2B%20Detail-green?style=flat-square" alt="Multi-view Output">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square" alt="Python 3.10+">
</p>

---

## What Is This?

ExcaliClaude is a Claude Code skill that turns natural language requests into readable Excalidraw diagrams using a spec-first pipeline.

The checked-in skill entrypoint is `excalidraw-diagram/SKILL.md`. The builder, validator, renderer, and Mermaid exporter live under `excalidraw-diagram/references/`.

Instead of asking Claude to freehand raw Excalidraw geometry, the workflow is:

1. discover the real flow when it exists in code
2. build a shared semantic model
3. derive one or more focused views from that model
4. render deterministic `.excalidraw` output
5. validate the structure
6. optionally render preview PNGs and export Mermaid text

### Key Features

- **Multi-view output**: supports `overview`, `focused-flow`, `drill-down`, and `scenario-pack`.
- **Codebase-aware discovery**: can explore an existing repo and use real names instead of placeholders.
- **Evidence-aware modeling**: entities and relationships can carry `code`, `inferred`, or `user-specified` evidence metadata.
- **Deterministic builder**: layout, node sizing, legends, and label placement come from code instead of prompt-only geometry.
- **Hybrid overview layout**: architecture overviews can keep core tiers centered while moving external systems and async backbones to side columns.
- **Automatic split behavior**: large views can split into overview plus detail artifacts.
- **Multiple diagram kinds**: dynamic, container, component, context, architecture, deployment, data-flow, trust-boundary, and dependency-map.
- **Secondary Mermaid export**: emits text-native diagram output from the same compiled view data.
- **Overwrite-safe naming**: use `--unique-output` to append a short suffix, and collisions are avoided automatically.

---

## Installation

### 1. Copy the skill into your Claude Code skills directory

```bash
git clone https://github.com/shahzadahmadv1/ExcaliClaude.git
cd ExcaliClaude

mkdir -p ~/.claude/skills/excalidraw-diagram
cp -r excalidraw-diagram/* ~/.claude/skills/excalidraw-diagram/
```

### 2. Optional: install Playwright for preview rendering

Without Playwright, the skill still generates specs and `.excalidraw` files. It only skips PNG preview rendering.

```bash
pip install playwright
playwright install chromium
```

Or with `uv`:

```bash
uv pip install playwright
uv run playwright install chromium
```

### 3. Recommended: install an Excalidraw editor

- VS Code: [Excalidraw Editor](https://marketplace.visualstudio.com/items?itemName=pomdtr.excalidraw-editor)
- Excalidraw Web: [excalidraw.com](https://excalidraw.com)
- Obsidian: [Obsidian Excalidraw plugin](https://github.com/zsviczian/obsidian-excalidraw-plugin)

### 4. Start a new Claude Code session

The skill should be auto-discovered as `excalidraw-diagram`.

---

## Usage

### Ask naturally

```text
Create a diagram of the payment processing flow
Generate an overview and drill-down for our authentication system
Show a trust-boundary diagram for this service
Explain how this repo talks to Redis and PostgreSQL with a diagram
```

Claude will:

1. inspect the request
2. explore the codebase if needed
3. build a shared model
4. define one or more views
5. build `.excalidraw` artifacts
6. validate them
7. render preview PNGs when Playwright is available

### View Modes

| View Mode | Best For |
|-----------|----------|
| **Overview** | High-level system map or service landscape |
| **Focused Flow** | One runtime story or request path |
| **Drill-Down** | Internals of one service, phase, or subsystem |
| **Scenario Pack** | Overview plus one or more detail diagrams from one shared model |

### Diagram Kinds

| Kind | Best For |
|------|----------|
| **Dynamic** | Runtime interactions and request paths |
| **Container** | Service or application composition |
| **Component** | Internals of a single service or container |
| **Context** | System boundaries and external dependencies |
| **Architecture** | Broad layered overviews |
| **Deployment** | Infrastructure and deployment topology |
| **Data-Flow** | Data or event movement through the system |
| **Trust-Boundary** | Security zones and trust perimeters |
| **Dependency-Map** | Static service or package dependencies |

### Scope Controls

The model and views can include:

- `detail_level`: `minimal`, `standard`, `detailed`
- `audience`: `technical`, `executive`, `mixed`
- `scope_filter`: narrow the diagram to specific entities or groups
- `max_nodes`: trigger automatic splitting when a view gets too dense
- `show_evidence`: hide or show evidence summary cues when evidence metadata exists

### Output Naming

The intended skill-side naming pattern is:

```text
docs/diagrams/specs/<date>-<topic>-<shortid>.diagram.json
docs/diagrams/<date>-<topic>-<shortid>.excalidraw
docs/diagrams/<date>-<topic>-<shortid>-<view_id>.excalidraw
```

Use `--unique-output` with the standalone builder when you want a short suffix appended automatically. Even without the flag, the builder avoids overwriting existing artifacts by appending a short suffix on collision.

---

## How It Works

### Generation Pipeline

```text
Description / codebase request
            |
            v
+--------------------------+
| 1. Discover              |  Explore the repo when the flow exists in code
+--------------------------+
            |
            v
+--------------------------+
| 2. Build shared model    |  Entities, relationships, evidence metadata
+--------------------------+
            |
            v
+--------------------------+
| 3. Define views          |  Overview / focused-flow / drill-down / pack
+--------------------------+
            |
            v
+--------------------------+
| 4. Build diagram(s)      |  Deterministic Excalidraw JSON
+--------------------------+
            |
            v
+--------------------------+
| 5. Validate              |  Structural validation and spec checks
+--------------------------+
            |
            v
+--------------------------+
| 6. Render / export       |  PNG preview and Mermaid text
+--------------------------+
            |
            v
.diagram.json + .excalidraw + optional .png + optional Mermaid
```

### What the builder handles

- lane and layer sizing
- title and subtitle placement
- node sizing and wrapped text
- legends
- collision-aware edge label placement
- decision diamonds
- evidence summaries
- multi-view artifact generation

---

## Standalone Tools

The builder, validator, renderer, and Mermaid exporter can all be used without Claude Code.

### Build a legacy single-view diagram

```bash
python excalidraw-diagram/references/build_excalidraw_diagram.py \
  excalidraw-diagram/references/examples/enhanced-auth-flow.spec.json \
  --output docs/diagrams/auth-flow.excalidraw \
  --unique-output
```

### Build a multi-view scenario pack

```bash
python excalidraw-diagram/references/build_excalidraw_diagram.py \
  excalidraw-diagram/references/examples/scenario-pack-example.spec.json \
  --output docs/diagrams/auth-pack.excalidraw \
  --unique-output
```

That command prints one artifact path per generated view.

### Validate a generated `.excalidraw` file

```bash
python excalidraw-diagram/references/validate_excalidraw.py path/to/diagram.excalidraw
```

### Validate a spec as well

```bash
python excalidraw-diagram/references/validate_excalidraw.py path/to/diagram.excalidraw --spec path/to/spec.json
```

### Render a PNG preview

```bash
python excalidraw-diagram/references/render_excalidraw.py path/to/diagram.excalidraw
```

### Export Mermaid

```bash
python excalidraw-diagram/references/export_mermaid.py \
  excalidraw-diagram/references/examples/focused-flow-example.spec.json \
  --output docs/diagrams/focused-flow.mmd
```

### Example specs

- `enhanced-auth-flow.spec.json` - legacy single-view sample
- `multi-view-auth.spec.json` - shared model plus multiple views
- `overview-example.spec.json` - overview mode
- `focused-flow-example.spec.json` - focused-flow mode
- `drill-down-example.spec.json` - drill-down mode
- `scenario-pack-example.spec.json` - overview plus multiple details
- `connector-stress-example.spec.json` - dense routing fixture for connector readability

---

## Configuration

### Semantic spec contract

Edit `excalidraw-diagram/references/diagram-spec.md`.

### Discovery behavior

Edit `excalidraw-diagram/references/codebase-discovery-prompt.md`.

### Color and role styling

Edit `excalidraw-diagram/references/color-palette.md`.

### Layout heuristics

Edit `excalidraw-diagram/references/build_excalidraw_diagram.py`.

### Output location and skill behavior

Edit `excalidraw-diagram/SKILL.md`.

---

## Project Structure

```text
ExcaliClaude/
|-- excalidraw-diagram/
|   |-- SKILL.md
|   `-- references/
|       |-- build_excalidraw_diagram.py
|       |-- validate_excalidraw.py
|       |-- render_excalidraw.py
|       |-- export_mermaid.py
|       |-- diagram-spec.md
|       |-- diagram-quality-bar.md
|       |-- codebase-discovery-prompt.md
|       |-- color-palette.md
|       `-- examples/
|-- docs/
|   |-- diagrams/
|   |-- evals/
|   `-- research/
|-- CONTRIBUTING.md
`-- README.md
```

---

## Requirements

| Requirement | Required? | Purpose |
|-------------|-----------|---------|
| Claude Code | Yes | Runs the skill |
| Python 3.10+ | Yes | Builder, validator, renderer, and exporter scripts |
| Playwright | No | PNG preview rendering |
| Excalidraw editor | No | Editing generated `.excalidraw` files |

---

## FAQ

### Does this work without Playwright?

Yes. The skill still produces the spec and `.excalidraw` artifacts. Only PNG preview rendering is skipped.

### Can I avoid overwriting diagrams from repeated runs?

Yes. Use `--unique-output` when calling the builder directly. The builder also appends a short suffix automatically if the requested output path already exists.

### Can I edit the generated diagrams?

Yes. The output is standard Excalidraw JSON and can be edited in Excalidraw-compatible tools.

### Can it diagram existing flows from code?

Yes. That is one of the main goals of the skill. When the request refers to an existing implementation, Claude can explore the repo and diagram real components and relationships.

### Does Mermaid replace Excalidraw?

No. Mermaid is a secondary text export. Excalidraw remains the primary polished output.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the current smoke-test workflow, multi-view examples, Mermaid export checks, and prompt evaluation guidance.

When changing the Claude skill prompt, also run the manual evaluation matrix in `docs/evals/skill-evaluation-matrix.md`.

---

## License

[MIT](LICENSE)
