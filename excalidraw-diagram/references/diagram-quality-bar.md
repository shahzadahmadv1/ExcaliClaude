# Diagram Quality Bar

Use this file before drafting a diagram spec.

## Target Outcome

The diagram should explain the flow on its own, not just decorate a text answer.

## Non-Negotiables

- Give every diagram a clear title.
- Use the smallest abstraction that answers the question.
- Label important relationships.
- Show a legend whenever color or line style carries meaning.
- Include enough metadata in nodes to explain what they are:
  - name
  - type/abstraction
  - technology when relevant
  - short responsibility
- Keep visual scope tight. If the diagram becomes crowded, split it.

## C4-Inspired Selection Rules

- Use a `dynamic` diagram when the user asks for a request path, runtime flow, or sequence of interactions.
- Use a `container` diagram when the user asks how a system is composed.
- Use a `component` diagram when the question is inside one container/service.
- Use a `context` diagram when the user needs a high-level system boundary view.

If the request mixes multiple levels, create the higher-level overview first and then offer a deeper follow-up diagram.

## Flow Diagram Rules

- Number the main interactions with `sequence`.
- Keep arrows directional and labeled with intent:
  - `POST /login`
  - `Publish event`
  - `Read account`
  - `Write session`
- Use decision nodes only for meaningful branches.
- Prefer one main story per diagram.

## Architecture Diagram Rules

- Group components by layer, bounded context, or ownership.
- Keep the group order meaningful:
  - client -> edge -> application -> data
  - upstream -> core -> downstream
- Do not mix every dependency into the same view. Show only relationships that help explain the question.

## Codebase-Aware Rules

- Use discovered names from the codebase instead of generic placeholders.
- Use actual external system names when they are known.
- Use real boundaries from the repo when possible:
  - project
  - namespace
  - service
  - package
  - layer

## Failure Modes To Avoid

- Boxes with names only and no explanation
- Unlabeled arrows
- Multiple abstraction levels mixed together
- More than one core narrative in the same flow diagram
- Big undifferentiated grids of rectangles
- Generic names like "Auth Service" when the code has a more precise name
