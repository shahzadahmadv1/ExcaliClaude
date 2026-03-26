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

- Run it against the example spec to verify output:

  ```bash
  python excalidraw-diagram/references/build_excalidraw_diagram.py \
    excalidraw-diagram/references/examples/enhanced-auth-flow.spec.json \
    --output test-output.excalidraw
  ```

- Validate the output:

  ```bash
  python excalidraw-diagram/references/validate_excalidraw.py test-output.excalidraw
  ```

- Open the `.excalidraw` file in VS Code or excalidraw.com to visually verify.

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

## Feature Ideas

Open an issue or start a Discussion. Good contributions include:

- New diagram types or layout modes
- Better color/styling defaults
- Improved label placement or arrow routing
- Support for additional output formats
- Example specs and diagrams

## Code Style

- Python: follow the existing style in the repo. No specific formatter is enforced yet.
- Markdown: keep lines readable, use ATX headings (`#`).

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
