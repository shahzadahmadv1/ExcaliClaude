# /diagram — Generate an Excalidraw diagram

Generate an Excalidraw architecture or flow diagram using the ExcaliClaude skill.

## Arguments

$ARGUMENTS

If no arguments are provided, ask the user what they would like to diagram.

## Instructions

1. **Activate the `excalidraw-diagram` skill** — follow its full generation process.

2. **Determine view mode from the request:**
   - "overview" / "architecture" / "what exists" → `overview`
   - "flow" / "what happens when" / "request path" → `focused-flow`
   - "internals" / "how does X work" → `drill-down`
   - "end to end" / "overview + detail" / "document" → `scenario-pack`
   - When unclear, default to `focused-flow` for flow questions, `overview` for architecture questions.

3. **Set scope controls based on context:**
   - `detail_level`: `minimal` for executives, `standard` by default, `detailed` for deep dives
   - `audience`: `technical` by default, `executive` if the user mentions stakeholders/leadership
   - `max_nodes`: set to 10-12 for focused views, leave unset for overviews
   - `scope_filter`: set when the user names specific services or phases

4. **Build the shared model first**, then define views. Follow the two-phase generation process in SKILL.md.

5. **Save artifacts:**
   - Spec: `docs/diagrams/specs/<date>-<topic>.diagram.json`
   - Diagram: `docs/diagrams/<date>-<topic>.excalidraw`
   - Mermaid (optional): `docs/diagrams/<date>-<topic>.mermaid.md`

6. **Run the full pipeline:**
   ```bash
   python <skill-dir>/references/build_excalidraw_diagram.py <spec> --output <diagram>
   python <skill-dir>/references/validate_excalidraw.py <diagram>
   python <skill-dir>/references/render_excalidraw.py <diagram>
   ```

7. **Optionally export Mermaid** when the user asks for text-friendly output:
   ```bash
   python <skill-dir>/references/export_mermaid.py <spec> --output <mermaid-file>
   ```

8. **Report results:**
   - List all generated artifact paths
   - State the view mode used
   - Note whether the diagram is codebase-accurate or conceptual
   - Summarize evidence sources if discovery was performed
