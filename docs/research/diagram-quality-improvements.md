# Diagram Quality Improvement Notes

## Research Summary

The current weakness was not Excalidraw itself. It was the generation strategy.

The previous skill asked Claude to:

1. infer the architecture
2. choose a layout
3. compute coordinates
4. style the diagram
5. output final Excalidraw JSON

That puts semantics and geometry in the same model step, which makes "acceptable" diagrams easy but consistent, high-signal diagrams hard.

The research pointed to a better pattern:

- choose the right abstraction level first
- make relationships explicit and labeled
- include a title and legend
- keep diagrams small enough to read
- convert a structured intermediate representation into the rendering format

## Official Sources

### C4 Model

- Diagram notation guidance: https://c4model.com/diagrams/notation
- Dynamic diagrams: https://c4model.com/diagrams/dynamic

Key takeaways used in this repo:

- every diagram should have a title
- every relationship should be labeled
- dynamic views should show the runtime story, not every static dependency
- abstraction levels should not be mixed casually

### Excalidraw Developer Docs

- Element skeleton API: https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/excalidraw-element-skeleton
- Export utilities: https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils/export

Key takeaways used in this repo:

- Excalidraw supports programmatic scene generation
- Excalidraw also provides an export utility, so previews do not need to be editor screenshots
- Excalidraw fits well as a rendering target instead of a planning format

### Anthropic Prompting Guidance

- XML tags: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags
- Multishot prompting: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/multishot-prompting

Key takeaways used in this repo:

- structured intermediate artifacts are more reliable than broad free-form instructions
- consistent output improves when the task is decomposed into smaller, explicit formats

## Resulting Changes

- Added a spec-first builder: `excalidraw-diagram/references/build_excalidraw_diagram.py`
- Added a diagram spec contract: `excalidraw-diagram/references/diagram-spec.md`
- Added a quality bar reference: `excalidraw-diagram/references/diagram-quality-bar.md`
- Updated the skill to generate a semantic spec before building Excalidraw output
- Updated preview rendering to use Excalidraw's export utility instead of a raw editor screenshot

## Expected Outcome

This should improve:

- layout consistency
- relationship clarity
- diagram titles and legends
- node usefulness, because nodes can include type/technology/description
- maintainability, because iteration now happens on a small JSON spec instead of raw scene JSON
