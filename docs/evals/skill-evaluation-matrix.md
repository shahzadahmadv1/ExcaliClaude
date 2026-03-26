# Claude Skill Evaluation Matrix

Use this matrix when changing [`excalidraw-diagram/SKILL.md`](../../excalidraw-diagram/SKILL.md), the discovery prompt, or the builder heuristics.

The goal is not "does a diagram get generated?" The goal is "does the Claude skill choose the right diagram, use the right evidence, and produce a readable result?"

## How To Use It

For each prompt:

1. Run the skill in Claude Code with the repo or sample prompt context needed.
2. Save the generated `.diagram.json`, `.excalidraw`, and preview PNG when available.
3. Score the run against the pass criteria below.
4. Record regressions before changing the prompt again.

## Pass Criteria

- The skill chooses the smallest useful diagram type.
- Important relationships are labeled.
- Nodes explain role and responsibility, not just names.
- The output is explicitly marked as codebase-accurate or conceptual.
- Large scopes split into overview plus detail rather than one crowded canvas.
- Validation passes.
- Preview rendering failure degrades cleanly when Playwright is unavailable.

## Evaluation Set

### 1. Conceptual Runtime Flow

Prompt:

```text
Create a diagram of the password reset flow. The browser calls the API gateway, which sends the request to the auth service. The auth service looks up the user in PostgreSQL, writes a reset token to Redis, and sends an email through SendGrid.
```

Expected behavior:

- Chooses a `dynamic` diagram.
- Uses `layout: flow`.
- Numbers the main interactions.
- Distinguishes service, database, and external provider roles.

Failure smells:

- Unlabeled arrows.
- Generic boxes with no descriptions.
- Container or architecture view chosen instead of runtime flow.

### 2. Codebase-Backed Existing Flow

Prompt:

```text
Explain the authentication flow in this repo with a diagram. Use the actual services, projects, and data stores from the codebase.
```

Expected behavior:

- Triggers discovery before writing the spec.
- Uses discovered names from code instead of placeholders.
- States when evidence is incomplete and where it inferred the rest.

Failure smells:

- Invented services not found in the repo.
- Ignores namespaces, projects, or real boundaries.
- Claims codebase accuracy without evidence.

### 3. High-Level Architecture Overview

Prompt:

```text
Generate an architecture overview for a SaaS platform with web app, API gateway, billing service, notification worker, PostgreSQL, Redis, and Stripe.
```

Expected behavior:

- Chooses `architecture` or `container`, not `dynamic`.
- Uses grouped layers with a readable legend.
- Shows only relationships that help explain the platform.

Failure smells:

- Sequence numbers in a static architecture view.
- Every possible dependency included.
- Mixed runtime and structural concerns in one diagram.

### 4. Component View Inside One Service

Prompt:

```text
Show a component diagram for the auth service only: controllers, token issuer, password hasher, session store adapter, and user repository.
```

Expected behavior:

- Chooses `component`.
- Keeps scope inside one service boundary.
- Avoids pulling unrelated infrastructure into the main canvas.

Failure smells:

- System-wide view produced instead of service internals.
- External systems dominate the diagram.

### 5. Large Scope Must Split

Prompt:

```text
Diagram our entire order lifecycle from storefront through checkout, payment, fraud, inventory, shipping, notifications, analytics, refunds, and support handoff.
```

Expected behavior:

- Produces an overview first.
- Splits dense phases into follow-up detail diagrams or offers to do so.
- Keeps each output readable.

Failure smells:

- One giant crowded canvas.
- More than one core narrative forced into a single flow.

### 6. Ambiguous Request Should Stay Small

Prompt:

```text
Visualize how login works.
```

Expected behavior:

- Defaults to the smallest useful runtime story.
- Does not expand into a full platform architecture unless the user asks.

Failure smells:

- Over-scoped diagram with unrelated systems.
- Missing explanation of chosen scope.

### 7. Decision Branching

Prompt:

```text
Create a diagram for checkout authorization where the payment service either captures the payment on success or returns the user to the checkout page on failure.
```

Expected behavior:

- Uses a meaningful decision node.
- Places yes/no or success/failure branches clearly.
- Keeps labels readable near branch arrows.

Failure smells:

- Branches shown as plain unlabeled arrows.
- Decision diamond used for a trivial linear step.

### 8. Preview Failure Fallback

Prompt:

```text
Generate a simple diagram for a client calling an API and saving to Postgres.
```

Expected behavior:

- Still produces spec plus `.excalidraw` when Playwright is missing.
- Reports that preview rendering was skipped, not that generation failed.

Failure smells:

- Treats preview failure as total failure.
- Omits artifact paths from the final report.

### 9. Multi-View Scenario Pack

Prompt:

```text
Document the payment system end to end. I want an overview of all services plus a focused flow for the checkout path.
```

Expected behavior:

- Selects `scenario-pack` mode.
- Builds one shared model with all entities.
- Emits at least two artifacts: an overview and a checkout flow.
- Uses deterministic artifact naming: `{slug}-{view_id}.excalidraw`.
- Both artifacts share consistent entity IDs and labels.

Failure smells:

- Only one artifact produced.
- Entities renamed or re-IDed between views.
- Auto-split fires but produces unintelligible fragments.

### 10. Evidence-Aware Codebase Discovery

Prompt:

```text
Diagram the authentication flow in this repo. Show which parts are code-derived and which are inferred.
```

Expected behavior:

- Triggers codebase discovery.
- Tags entities and relationships with `evidence_source` (code/inferred/user-specified) and `confidence`.
- Evidence legend or notes appear in the rendered output.
- Report explicitly states how many entities are code-derived vs inferred.

Failure smells:

- All entities marked with the same evidence source.
- Evidence metadata present in spec but invisible in output.
- Report omits evidence summary.

### 11. Mermaid Export

Prompt:

```text
Generate a Mermaid version of the order checkout flow for our pull request description.
```

Expected behavior:

- Produces Mermaid text output alongside or instead of `.excalidraw`.
- Uses the same compiled view data as the Excalidraw builder.
- Mermaid text is valid and renders in GitHub PR previews.
- Edge styles map correctly (dashed for async, solid for sync).

Failure smells:

- Mermaid text generated from separate prompt output instead of compiled views.
- Invalid Mermaid syntax that fails to render.
- Node IDs or labels differ from the Excalidraw version.

### 12. Deployment/Infrastructure View

Prompt:

```text
Show a deployment diagram of our Kubernetes cluster with the API pods, worker pods, Redis, and PostgreSQL on their respective nodes.
```

Expected behavior:

- Selects `deployment` diagram kind.
- Uses host, container-runtime, network, and database roles.
- Groups by infrastructure topology (nodes, namespaces).
- Deploy edges show where services run.

Failure smells:

- Runtime/dynamic flow instead of deployment topology.
- Missing infrastructure grouping.
- Generic service roles instead of deployment-specific roles.

### 13. Drill-Down Continuity

Prompt:

```text
First show me the whole system overview, then drill into the auth service internals.
```

Expected behavior:

- Produces an overview artifact and a drill-down artifact.
- The auth service entity ID is consistent across both views.
- The drill-down shows internal components not visible in the overview.
- Report notes which overview entities have drill-down views.

Failure smells:

- Drill-down repeats the overview instead of showing internals.
- Entity IDs change between views.
- No cross-reference between overview and drill-down artifacts.

## Suggested Release Gate

Before merging prompt changes:

- Run at least one conceptual flow prompt.
- Run at least one codebase-backed prompt.
- Run one oversized prompt to verify splitting behavior.
- Run one case with preview rendering unavailable.
- Run one multi-view scenario pack prompt (eval 9).
- Run one evidence-aware discovery prompt (eval 10).
- Run one Mermaid export prompt (eval 11).
