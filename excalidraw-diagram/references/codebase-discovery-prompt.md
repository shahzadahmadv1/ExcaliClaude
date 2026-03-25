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

### Search Strategy

- Start with the solution/project file to understand project structure
- Search for keywords from the user's request (e.g., "fraud", "fingerprint", "blocklist")
- Follow the call chain from entry point → orchestrator → sub-components
- Read orchestrator methods to understand the sequence/phases

### Output Format

Return your findings in this EXACT format:

## Components Found

| Name | Type | File Path | Role |
|------|------|-----------|------|
| (actual class name) | (Service/Evaluator/Client/Repository/Model/Config) | (file path) | (what it does in 1 line) |

## Flow Sequence

1. (Step 1 description — which component does what)
2. (Step 2 description)
...

## Data Flows

- (Component A) → (Component B): (what data/request flows between them)
- ...

## External Systems

- (System name): (how it's integrated, e.g., "Fingerprint.com API called via FingerprintClient")
- ...

## Key Decision Points

- (Describe any branching logic, short-circuits, or conditional flows)

Be specific. Use actual class names, method names, and file paths from the code. Do NOT invent or generalize.
