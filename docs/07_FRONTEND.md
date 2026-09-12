# 💻 SentinelGraph AI: Analyst Console & Frontend Web Application

## 1. Frontend Technology Stack & Overview

The SentinelGraph AI analyst console is an enterprise Single Page Application (SPA) designed to provide fraud investigators with a responsive, single-pane operational workspace.

```
┌────────────────────────────────────────────────────────┐
│              FRONTEND STACK ARCHITECTURE               │
├───────────────────┬────────────────────────────────────┤
│ Framework         │ React 18.3 (Hooks, Functional UI)  │
│ Language          │ TypeScript 5.7 (Strict Types)      │
│ Build Tool        │ Vite 6.1 (ESM, Fast HMR)           │
│ Styling           │ Tailwind CSS 3.4 (Custom Theme)    │
│ Graph Rendering   │ Cytoscape.js 3.30 (Canvas & WebGL) │
│ Iconography       │ Lucide React 0.475                 │
│ Routing           │ Hash-based SPA Navigation          │
│ Ingress & Host    │ Nginx 1.27 Alpine (Reverse Proxy)  │
└───────────────────┴────────────────────────────────────┘
```

---

## 2. Hash Routing & Application Navigation

The frontend employs lightweight, robust **hash-based routing** (`window.location.hash`) managed in [`frontend/src/App.tsx`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/frontend/src/App.tsx). This eliminates server-side rewrite issues in diverse hosting environments (e.g. S3, GitHub Pages, Render, or sub-path proxies).

### The Three Operational Views

```
             ┌──────────────────────────────────────────┐
             │       SentinelGraph Analyst Console      │
             └────────────────────┬─────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Risk Overview   │    │   Investigate    │    │  AI Governance   │
│  (#risk-overview)│    │  (#investigate)  │    │  (#evaluation)   │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

1. **Risk Overview (`#risk-overview`)**:
   * Global fraud monitoring dashboard.
   * High-level metric cards: Total Complaints, Active Syndicates, High-Risk Entities, Shared Hubs.
   * Top connected entities table with degree centrality and direct "Investigate" action triggers.
   * Shared entity co-occurrence table and recent complaint ingestion stream.

2. **Investigation Workspace (`#investigate`)**:
   * Single-pane triage workspace for deep forensic analysis.
   * Target search bar with support for phone numbers, UPI VPAs, emails, bank accounts, or complaint IDs.
   * Quick-fill buttons for pre-configured demonstration scenarios.
   * Interactive **Cytoscape.js** topological graph visualization.
   * Reconstructed chronological **Complaint Timeline**.
   * Structured **Evidence Dossier** and **AI Executive Report** view.

3. **AI Governance & Guardrails Console (`#evaluation`)**:
   * Visual audit dashboard explaining the 3-Layer Guardrail Architecture.
   * Golden Scenario specification cards with ground-truth citation requirements.
   * Mathematical formulas for the five quality dimensions.
   * Real-time polling of Prometheus telemetry counters and latency histograms.

---

## 3. The Investigation Workspace & Cytoscape.js Visualization

The graph visualization component ([`CytoscapeGraph.tsx`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/frontend/src/components/investigation/CytoscapeGraph.tsx)) renders complex fraud topologies with high-performance Canvas rendering:

### 3.1 Graph Controls & Capabilities
* **Dynamic Traversal Depth**: Analysts can adjust graph exploration depth from $1$ to $5$ hops using a slider control.
* **Layout Algorithms**: Switchable layout engines:
  * `cose` (Compound Spring Embedder for organic organic cluster visualization).
  * `concentric` (Arranges high-degree entity hubs at the center).
  * `breadthfirst` (Hierarchical tree projection from investigated root).
  * `grid` (Structured tabular layout).
* **Viewport Navigation**: Zoom in/out, pan, bounding-box fit, and orientation reset.
* **Node Selection Drawer**: Clicking any node opens a slide-over inspection card displaying:
  * Entity label (`Phone`, `UPI`, `Complaint`, etc.);
  * Normalized ID and property metadata;
  * Confidence score;
  * Direct pivot button: "Set as Investigation Target".

### 3.2 Topological Visual Styling
Nodes and edges are styled according to semantic fraud categories:
* **Complaints**: Hexagonal or shield icons in indigo/blue.
* **Financial Nodes (UPI, Bank Account)**: Emerald green icons.
* **Communication Nodes (Phone, Email)**: Amber/orange icons.
* **Digital Nodes (URL)**: Rose red warning icons.
* **Edges (`MENTIONS`)**: Directed arrows with subtle opacity to highlight multi-complaint convergences.

---

## 4. Reconstructed Timeline & Evidence Dossier

The investigation workspace pairs graph topology with temporal and evidentiary views:

### 4.1 Chronological Timeline
* Reconstructs the multi-hop sequence of complaints connected to the investigated entity.
* Categorizes events: `FIRST_APPEARANCE`, `REUSE_EVENT`, `BURST_ACTIVITY`, `NETWORK_EXPANSION`.
* Displays elapsed days, dormant gaps, and velocity metrics.

### 4.2 AI Investigation Dossier
* Renders the certified `ProfessionalInvestigationReport`:
  * **Executive Summary**: Synthesized high-level overview.
  * **Risk Justification**: Plain-language explanation grounded in graph facts.
  * **Key Takeaways**: Bulleted critical findings.
  * **Structured Findings**: Cards with severity badges (`CRITICAL`, `HIGH`), confidence bars, and clickable citation links.
  * **Actionable Recommendations**: Clear containment actions (e.g., "Freeze UPI VPA `scammer@upi`", "Submit NCRP Advisory").
  * **Execution Telemetry**: Model name, inference latency, prompt hash, and token usage.

---

## 5. Centralized HTTP API Client Architecture

The frontend communicates with the backend via [`frontend/src/api/client.ts`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/frontend/src/api/client.ts):

### 5.1 Native Fetch with AbortController
```typescript
export async function apiFetch<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const url = resolveApiUrl(endpoint);
  const { timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  // Native fetch with error classification...
}
```

### 5.2 Dynamic Base URL Resolution
* If `VITE_API_URL` is set in the environment (e.g. `https://api.sentinelgraph.example.com`), requests are directed to that absolute host.
* If `VITE_API_URL` is omitted, the client uses **relative paths** (`/api/v1/...`). In development, Vite proxies requests to `localhost:8000`. In production, Nginx reverse-proxies them to `http://api:8000`.

### 5.3 60-Second Cold-Start Resilience
`DEFAULT_REQUEST_TIMEOUT_MS` is configured to `60000` (60 seconds). This accommodates cloud free-tier hosting platforms (such as Render or HuggingFace Spaces) where containers spin down during inactivity and require 30–50 seconds for cold starts.

---

## 6. Production Containerization & Nginx Configuration

The frontend is packaged using a multi-stage Docker build ([`frontend/Dockerfile`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/frontend/Dockerfile)):

```dockerfile
# Stage 1: Compile TypeScript & Build static assets with Vite
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: High-performance Nginx static web server
FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Reverse Proxy Architecture ([`frontend/nginx.conf`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/frontend/nginx.conf))
The Nginx configuration eliminates CORS complications by serving the frontend and proxying backend APIs on the exact same origin (`http://localhost:80`):

```nginx
# API Endpoints
location /api/ {
    proxy_pass http://api:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 90s;
}

# Operational Probes
location /health {
    proxy_pass http://api:8000;
}

# Prometheus Telemetry
location /metrics {
    proxy_pass http://api:8000;
}

# Single Page Application Fallback
location / {
    try_files $uri $uri/ /index.html;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}
```
