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
  <a href="#color-palette">Color Palette</a> &bull;
  <a href="#configuration">Configuration</a> &bull;
  <a href="#license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Skill-blueviolet?style=flat-square" alt="Claude Code Skill">
  <img src="https://img.shields.io/badge/Output-.diagram.json%20%2B%20.excalidraw-orange?style=flat-square" alt="Diagram Output">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square" alt="Python 3.10+">
</p>

---

## What Is This?

ExcaliClaude is a [Claude Code](https://claude.ai/claude-code) skill that turns natural language descriptions into polished Excalidraw architecture and flow diagrams using a spec-first generation pipeline.

Instead of asking Claude to hand-author raw Excalidraw geometry, the skill now:

1. explores the codebase when the flow exists in code
2. chooses the right diagram level
3. writes a small semantic diagram spec
4. builds a valid `.excalidraw` file from that spec
5. validates and optionally renders a preview PNG

Example prompt:

> "Create a diagram of the authentication flow: the client hits the load balancer, which routes to the auth service. The auth service checks the user database and caches sessions in Redis."

### Key Features

- **Spec-first generation**: Claude writes a compact semantic diagram spec before rendering.
- **Codebase-aware discovery**: existing flows can be derived from the repo instead of guessed from the prompt.
- **Deterministic layout builder**: lanes, labels, legends, and arrows come from a builder script instead of freehand JSON.
- **Readable-by-default output**: decision diamonds size to their text, and relationship labels use collision-aware placement.
- **C4-inspired diagram selection**: dynamic, container, component, context, and broader architecture views.
- **Validation loop**: structural validation always runs; preview rendering runs when Playwright is installed.
- **Editable output**: diagrams open as standard `.excalidraw` files in VS Code, Excalidraw.com, and compatible tools.

---

## Installation

### 1. Copy the skill to your Claude Code skills directory

```bash
git clone https://github.com/shahzadahmadv1/ExcaliClaude.git
cd ExcaliClaude

mkdir -p ~/.claude/skills/excalidraw-diagram
cp -r excalidraw-diagram/* ~/.claude/skills/excalidraw-diagram/
```

### 2. Optional: install Playwright for preview rendering

Without Playwright, the skill still generates the semantic spec and `.excalidraw` file. It only skips PNG preview rendering.

```bash
pip install playwright
playwright install chromium
```

Or with `uv`:

```bash
uv pip install playwright
uv run playwright install chromium
```

### 3. Recommended: install the Excalidraw VS Code extension

Install [Excalidraw Editor](https://marketplace.visualstudio.com/items?itemName=pomdtr.excalidraw-editor) to open `.excalidraw` files directly in VS Code.

### 4. Start a new Claude Code session

The skill will be auto-discovered as `excalidraw-diagram`.

---

## Usage

### On-demand diagram generation

Ask naturally:

```text
Create a diagram of the payment processing flow
Generate an architecture diagram for our microservices
Explain the customer onboarding path with a diagram
Draw how this service talks to Redis and PostgreSQL
```

Claude will:

1. inspect the request
2. explore the codebase if needed
3. write a semantic spec
4. build the diagram
5. validate it
6. render a preview if Playwright is available

### Automatic offer during planning

When a planning discussion includes multiple interacting components and a clear flow, Claude can offer to generate a diagram once in the current session.

### Output

Generated artifacts are saved to:

```text
docs/diagrams/specs/<date>-<topic>.diagram.json   # Semantic diagram spec
docs/diagrams/<date>-<topic>.excalidraw           # Editable Excalidraw file
docs/diagrams/<date>-<topic>.png                  # Preview PNG, if rendering succeeds
```

Open the `.excalidraw` file in:

- **VS Code** with the [Excalidraw extension](https://marketplace.visualstudio.com/items?itemName=pomdtr.excalidraw-editor)
- **Excalidraw.com**
- **Obsidian** with the [Excalidraw plugin](https://github.com/zsviczian/obsidian-excalidraw-plugin)

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
| 2. Choose level          |  Dynamic / container / component / context
+--------------------------+
            |
            v
+--------------------------+
| 3. Write spec            |  Title, groups, nodes, edges, labels, notes
+--------------------------+
            |
            v
+--------------------------+
| 4. Build diagram         |  Deterministic builder creates Excalidraw JSON
+--------------------------+
            |
            v
+--------------------------+
| 5. Validate              |  Structural validator checks bindings and shape
+--------------------------+
            |
            v
+--------------------------+
| 6. Render preview        |  Excalidraw export utility renders a PNG
+--------------------------+
            |
            v
+--------------------------+
| 7. Refine spec           |  Improve scope, labels, or grouping if needed
+--------------------------+
            |
            v
.diagram.json + .excalidraw + .png
```

### Diagram Types

The skill uses a C4-inspired selection rule and chooses the smallest useful abstraction level first.

| Type | Best For |
|------|----------|
| **Dynamic** | Request paths, runtime interactions, "what happens when" questions |
| **Container** | Service/application composition |
| **Component** | Internal structure of a single service or container |
| **Context** | System boundaries and external dependencies |
| **Architecture** | Broader layered overviews spanning multiple parts of the system |

### Layout Modes

The builder uses deterministic layouts instead of asking Claude to place every box manually.

| Layout | Best For |
|--------|----------|
| **Flow** | Runtime/request paths, including sequence labels |
| **Layers** | Static architecture views and grouped system overviews |

### Validation And Quality

Every generated diagram goes through a spec-first quality loop:

1. **Semantic spec**: Claude writes title, groups, nodes, edges, and notes.
2. **Deterministic build**: `build_excalidraw_diagram.py` turns the spec into Excalidraw geometry.
3. **Structural validation**: `validate_excalidraw.py` checks IDs, bindings, arrow structure, and element ordering/index validity.
4. **Preview render**: `render_excalidraw.py` generates a PNG preview when Playwright is installed.
5. **Spec refinement**: Claude improves the spec instead of directly hand-editing scene JSON where possible.

---

## Color Palette

Every component is color-coded by architectural role:

| Role | Fill | Stroke | Use For |
|------|------|--------|---------|
| **Client / Frontend** | `#e3f2fd` | `#1e88e5` | Browser, mobile app, UI |
| **API / Gateway** | `#fff3e0` | `#ef6c00` | REST API, GraphQL, load balancer |
| **Service / Backend** | `#e8f5e9` | `#43a047` | Services, workers, processors |
| **Database / Storage** | `#fce4ec` | `#e53935` | PostgreSQL, Redis, S3, queues |
| **External / 3rd Party** | `#f3e5f5` | `#8e24aa` | Stripe, Auth0, SendGrid, external APIs |
| **Infrastructure** | `#eceff1` | `#546e7a` | Kubernetes, Docker, CDN |
| **Decision / Branch** | `#FFF3BF` | `#F59F00` | Conditional logic and branching |

Relationship styles are also encoded:

- **Sync**: solid line
- **Async**: dashed line
- **Read**: dotted line
- **Write**: solid line with explicit command label
- **Conditional yes/no**: colored branch relationships

Styling defaults:

- `roughness: 1`
- `fillStyle: "solid"`
- `strokeWidth: 2`
- `fontFamily: 3` (Cascadia / monospace)

---

## Configuration

### Color and relationship styles

Edit `excalidraw-diagram/references/color-palette.md`.

### Semantic spec contract

Edit `excalidraw-diagram/references/diagram-spec.md` if you want to change the structure Claude writes before rendering.

### Output location

The default output location is `docs/diagrams/` with specs in `docs/diagrams/specs/`. To change this, update the save paths in `excalidraw-diagram/skill.md`.

### Layout heuristics

The main spacing and sizing constants now live in `excalidraw-diagram/references/build_excalidraw_diagram.py`.

| Setting | Default |
|---------|---------|
| Canvas margin | `100px` |
| Group spacing | `72px` |
| Row spacing | `120px` |
| Minimum node size | `180x82px` |
| Decision sizing | Dynamic diamond with wrapped internal text, minimum `180x120px` |
| Title font | `28px` |
| Node font | `18px` |
| Decision font | `16px` |
| Legend width | `300px` |

Layout behavior is intentionally handled by the builder rather than the prompt:

- decisions render as true diamonds with centered internal text
- edge labels search for non-overlapping positions before falling back
- conditional yes/no labels use branch-specific placement instead of generic arrow-label placement

---

## Project Structure

```text
ExcaliClaude/
|-- excalidraw-diagram/
|   |-- skill.md
|   `-- references/
|       |-- build_excalidraw_diagram.py
|       |-- render_excalidraw.py
|       |-- validate_excalidraw.py
|       |-- diagram-spec.md
|       |-- diagram-quality-bar.md
|       |-- codebase-discovery-prompt.md
|       |-- excalidraw-schema.md
|       |-- color-palette.md
|       `-- examples/
|           |-- enhanced-auth-flow.spec.json
|           |-- simple-flow.excalidraw
|           `-- architecture.excalidraw
|-- docs/
|   |-- diagrams/
|   |-- research/
|   `-- superpowers/
|-- LICENSE
`-- README.md
```

---

## Standalone Tools

The builder, validator, and renderer can be used without Claude Code.

### Build from a diagram spec

```bash
python excalidraw-diagram/references/build_excalidraw_diagram.py excalidraw-diagram/references/examples/enhanced-auth-flow.spec.json --output docs/diagrams/auth-flow.excalidraw
```

### Validate an Excalidraw file

```bash
python excalidraw-diagram/references/validate_excalidraw.py path/to/diagram.excalidraw
```

Checks:

- top-level structure
- required element properties
- arrow `points` arrays
- text-to-container bindings
- duplicate IDs
- element `index` presence, uniqueness, and ordering

### Render to PNG

```bash
python excalidraw-diagram/references/render_excalidraw.py path/to/diagram.excalidraw
```

Outputs `path/to/diagram.png` when Playwright and Chromium are available.

---

## Requirements

| Requirement | Required? | Purpose |
|-------------|-----------|---------|
| [Claude Code](https://claude.ai/claude-code) | Yes | Runs the skill |
| Python 3.10+ | Yes | Builder and validator scripts |
| [Playwright](https://playwright.dev/python/) | No | Preview PNG rendering |
| [Excalidraw VS Code Extension](https://marketplace.visualstudio.com/items?itemName=pomdtr.excalidraw-editor) | No | Open `.excalidraw` files in VS Code |

---

## FAQ

### Does this work without Playwright?

Yes. The skill still produces the semantic spec and `.excalidraw` file. Only the PNG preview step is skipped.

### Can I edit the generated diagrams?

Yes. The output is a standard `.excalidraw` file and can be edited freely in Excalidraw-compatible tools.

### What kinds of diagrams does this generate?

Dynamic, container, component, context, and broader architecture diagrams focused on software architecture and runtime flows.

### What if the diagram looks wrong?

The intended workflow is to refine the semantic spec and rebuild, not to manually hand-edit raw scene JSON first. If Playwright is installed, Claude can use the PNG preview to iterate on the spec.

### Can it diagram existing flows from code?

Yes. That is one of the main improvements. When the request appears to refer to an existing implementation, the skill can explore the repo and diagram real components and relationships instead of generic placeholders.

### Can I use this outside Claude Code?

The scripts work standalone. The prompt workflow is designed for Claude Code.

---

## Contributing

Contributions are welcome! Whether it's a bug report, feature idea, documentation fix, or new diagram layout — we'd love your help.

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details on how to get started, test changes, and submit a pull request.

Quick version:

1. Fork the repo and create a branch.
2. Make your changes and test with the builder + validator.
3. Open a pull request with a description and screenshots if applicable.

Have an idea but not sure where to start? Open an issue or start a Discussion.

---

## License

[MIT](LICENSE)
