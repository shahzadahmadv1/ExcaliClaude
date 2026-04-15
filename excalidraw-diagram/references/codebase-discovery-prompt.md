# Codebase Discovery for Diagram Generation

You are exploring a codebase to gather the information needed to generate an accurate architecture or flow diagram.

## User's Request

{{USER_REQUEST}}

## Solution/Project Path

{{SOLUTION_PATH}}

## Your Task

Explore the codebase thoroughly and return a structured summary of the REAL components, their relationships, and data flows relevant to the user's request.

### What to Search For

1. **Entry points** — controllers, gRPC services, API endpoints, message handlers related to the topic
2. **Core orchestrators** — main feature/service classes that coordinate the flow
3. **Sub-components** — evaluators, validators, processors, clients that are called by the orchestrator
4. **External integrations** — third-party API clients, database repositories, message queues
5. **Data models** — key DTOs, domain models, configuration classes
6. **Flow sequence** — the order in which components are called (look at the orchestrator method body)
7. **Ownership and boundaries** — namespace, project, or folder structure that reveals team ownership or trust boundaries
8. **Runtime and deployment** — Dockerfiles, Kubernetes manifests, deployment configs, environment variables that reveal where components run
9. **Interaction direction** — whether external systems are inbound callers, downstream providers, or async backbone infrastructure

### Search Strategy

- Start with the solution/project file to understand project structure
- Search for keywords from the user's request (e.g., "fraud", "fingerprint", "blocklist")
- Follow the call chain from entry point → orchestrator → sub-components
- Read orchestrator methods to understand the sequence/phases

### Output Format

Return your findings in this EXACT format:

## Components Found

| Name | Type | File Path | Role | Evidence | Confidence | Owner | Boundary | Runtime |
|------|------|-----------|------|----------|------------|-------|----------|---------|
| (actual class name) | (Service/Evaluator/Client/Repository/Model/Config) | (file path) | (what it does in 1 line) | (code/inferred) | (high/medium/low) | (team or unknown) | (internal/external/shared) | (environment or unknown) |

### Evidence and Confidence Guide

For each component and relationship, record:

- **Evidence**: `code` if you found it directly in source code (class definition, import, call site). `inferred` if you deduced it from naming conventions, folder structure, config files, or patterns without a direct code reference. Never use `code` unless you can point to a specific file and line.
- **Confidence**: `high` if the code path is clear and unambiguous. `medium` if the component exists but its role or connections are partially unclear. `low` if the component is mentioned in comments, config, or docs but not confirmed in running code.
- **Owner**: team name, namespace, or project folder that suggests ownership. Use `unknown` if not determinable.
- **Boundary**: `internal` for components within the system boundary. `external` for third-party services or APIs. `shared` for components used across multiple systems.
- **Runtime**: deployment target (e.g., `kubernetes`, `lambda`, `vm`, `browser`). Use `unknown` if not determinable from the codebase.
- **Interaction direction**: note whether external systems initiate requests into the system, receive outbound calls, or serve as async transport so overview layouts can place them correctly.

## Flow Sequence

1. (Step 1 description — which component does what) [evidence: code/inferred] [confidence: high/medium/low]
2. (Step 2 description) [evidence: code/inferred] [confidence: high/medium/low]
...

## Data Flows

- (Component A) → (Component B): (what data/request flows between them) [evidence: code/inferred] [confidence: high/medium/low]
- ...

## External Systems

- (System name): (how it's integrated, e.g., "Fingerprint.com API called via FingerprintClient") [boundary: external] [evidence: code/inferred]
- ...

## Ownership and Boundaries

- (Component or group): owned by (team/namespace), boundary: (internal/external/shared)
- ...

## Runtime and Deployment

- (Component or group): runs on (environment), discovered from (file/config)
- ...

## Key Decision Points

- (Describe any branching logic, short-circuits, or conditional flows)

## Evidence Gaps

- (List any components or relationships where evidence is weak or missing)
- (Note anything you could NOT confirm from code that would need user verification)

Be specific. Use actual class names, method names, and file paths from the code. Do NOT invent or generalize. When evidence is missing, say so explicitly — do not fill in gaps with assumptions.
