# Contributing to ExcaliClaude

Thanks for your interest in contributing! This project welcomes contributions of all kinds — bug reports, feature ideas, documentation improvements, and code.

## Getting Started

1. Fork and clone the repository:

   ```bash
   git clone https://github.com/<your-username>/ExcaliClaude.git
   cd ExcaliClaude
   ```

2. Install the skill locally:

   ```bash
   mkdir -p ~/.claude/skills/excalidraw-diagram
   cp -r excalidraw-diagram/* ~/.claude/skills/excalidraw-diagram/
   ```

3. (Optional) Install Playwright for preview rendering:

   ```bash
   pip install playwright
   playwright install chromium
   ```

## Making Changes

### Skill prompt (`SKILL.md`)

This is the main instruction file Claude reads. Changes here affect how Claude approaches diagram generation. Test any prompt changes by generating a few different diagram types and checking the output quality.

When you change the prompt logic, also run through the manual evaluation matrix in `docs/evals/skill-evaluation-matrix.md`.

### Builder script (`build_excalidraw_diagram.py`)

The deterministic layout engine. When making changes:

- Run it against both single-view and multi-view examples:

  ```bash
  # Single-view (legacy)
  python excalidraw-diagram/references/build_excalidraw_diagram.py \
    excalidraw-diagram/references/examples/enhanced-auth-flow.spec.json \
    --output test-output.excalidraw \
    --unique-output

  # Multi-view
  python excalidraw-diagram/references/build_excalidraw_diagram.py \
    excalidraw-diagram/references/examples/multi-view-auth.spec.json \
    --output test-multi.excalidraw \
    --unique-output

  # Scenario pack (multi-artifact)
  python excalidraw-diagram/references/build_excalidraw_diagram.py \
    excalidraw-diagram/references/examples/scenario-pack-example.spec.json \
    --output test-scenario.excalidraw \
    --unique-output

  # Dense routing regression
  python excalidraw-diagram/references/build_excalidraw_diagram.py \
    excalidraw-diagram/references/examples/connector-stress-example.spec.json \
    --output test-routing.excalidraw \
    --unique-output
  ```

- Use `--unique-output` when you want a short run suffix appended automatically so repeated diagram runs do not overwrite each other.

- Validate the output:

  ```bash
  python excalidraw-diagram/references/validate_excalidraw.py test-output.excalidraw
  ```

- Test Mermaid export:

  ```bash
  python excalidraw-diagram/references/export_mermaid.py \
    excalidraw-diagram/references/examples/focused-flow-example.spec.json
  ```

- Open the `.excalidraw` file in VS Code or excalidraw.com to visually verify.

### Mermaid exporter (`export_mermaid.py`)

The secondary text export. It imports `compile_spec` from the builder, so changes to the compilation pipeline automatically apply to Mermaid output. Test with at least one multi-view spec to verify multi-graph output.

### Color palette and spec format

- `color-palette.md` — role-to-color mappings
- `diagram-spec.md` — the semantic spec contract between Claude and the builder

Changes to these affect all generated diagrams, so test broadly.

## Submitting a Pull Request

1. Create a branch from `master`:

   ```bash
   git checkout -b my-feature
   ```

2. Make your changes and test them (see above).

3. Commit with a clear message describing what and why.

4. Push and open a pull request against `master`.

5. In your PR description, include:
   - What the change does
   - A before/after screenshot if it affects diagram output
   - Which diagram types you tested with

## Reporting Bugs

Open an issue with:

- What you asked Claude to diagram
- The generated `.diagram.json` spec (if available)
- What went wrong (screenshot or description)
- Your environment (OS, Python version, Playwright installed?)

## Smoke Test Checklist

Before submitting a PR, verify:

- [ ] Build passes on `enhanced-auth-flow.spec.json` (single-view legacy)
- [ ] Build passes on `multi-view-auth.spec.json` (multi-view)
- [ ] Build passes on `scenario-pack-example.spec.json` (multi-artifact)
- [ ] Build passes on `connector-stress-example.spec.json` (dense routing fixture)
- [ ] Validation passes on all generated `.excalidraw` files
- [ ] Mermaid export runs without errors on at least one example
- [ ] If changing the skill prompt, run the evaluation matrix in `docs/evals/skill-evaluation-matrix.md`

## Feature Ideas

Open an issue or start a Discussion. Good contributions include:

- New diagram types or layout modes
- Better color/styling defaults
- Improved label placement or arrow routing
- Additional output formats (Mermaid is already supported)
- Example specs and diagrams
- View mode enhancements (overview, focused-flow, drill-down, scenario-pack)

## Code Style

- Python: follow the existing style in the repo. No specific formatter is enforced yet.
- Markdown: keep lines readable, use ATX headings (`#`).

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
