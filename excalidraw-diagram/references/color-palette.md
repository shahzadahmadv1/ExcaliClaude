# ExcaliClaude Color Palette

## Role-Based Colors

| Role | Background Fill | Stroke Color | Use For |
|------|----------------|--------------|---------|
| Client/Frontend | `#e3f2fd` | `#1e88e5` | Browser, mobile app, UI components |
| API/Gateway | `#fff3e0` | `#ef6c00` | REST API, GraphQL, load balancer |
| Service/Backend | `#e8f5e9` | `#43a047` | Microservices, workers, processors |
| Database/Storage | `#fce4ec` | `#e53935` | PostgreSQL, Redis, S3, file storage |
| External/3rd Party | `#f3e5f5` | `#8e24aa` | Stripe, Auth0, SendGrid, external APIs |
| Infrastructure | `#eceff1` | `#546e7a` | Kubernetes, Docker, CDN, networking |
| Decision / Branch | `#FFF3BF` | `#F59F00` | Decision points, gates, conditionals |

## Non-Role Colors

| Element | Color | Use For |
|---------|-------|---------|
| Arrows | `#495057` | All connections and flow lines |
| Text/Labels | `#1e1e1e` | All text content |
| Container borders | Same as role stroke, dashed | Group boundaries (e.g. "Frontend Layer") |
| Canvas background | `#ffffff` | Always white |

## Relationship Styles

| Relationship Kind | Stroke | Meaning |
|-------------------|--------|---------|
| `sync` | solid | Request/response or direct call |
| `async` | dashed | Event, queue, or asynchronous handoff |
| `read` | dotted | Query/read-heavy interaction |
| `write` | solid | Command/write interaction |
| `conditional-yes` | solid green | Positive branch from a decision |
| `conditional-no` | solid red | Negative branch from a decision |

## Styling Defaults

- `roughness: 1` (hand-drawn feel)
- `fillStyle: "solid"`
- `strokeWidth: 2`
- `fontFamily: 3` (Cascadia/monospace)
- `opacity: 100`
- Container rectangles: `roundness: { "type": 3 }`, `strokeStyle: "dashed"`, `backgroundColor: "transparent"`
