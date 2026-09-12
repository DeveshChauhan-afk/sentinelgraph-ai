# 🔒 SentinelGraph AI: Security Posture, Invariants & Controls

## 1. Executive Summary & Honest Disclosure

> [!CAUTION]
> **Authentication is NOT implemented in SentinelGraph AI v1.**
> The `/api/v1/auth/` endpoint is an explicit `"Coming soon"` placeholder.
> Do **NOT** assume the existence of JWT, OAuth2, Bearer tokens, or API key validation in the current release.

In its current state, all public REST endpoints (including complaint registration, graph inspection, and report generation) are accessible to any caller with network connectivity to the API port. SentinelGraph AI v1 is engineered as an open analytical platform suitable for hackathon demonstrations, local laboratory evaluations, and internal sandbox testing.

However, while user authentication is deferred to the enterprise hardening milestone, the platform implements comprehensive **defense-in-depth security controls** across its data validation, credential management, containerization, and database access layers.

---

## 2. Implemented Defense-in-Depth Controls

```
┌────────────────────────────────────────────────────────────────────────┐
│                   IMPLEMENTED SECURITY DEFENSE LAYERS                  │
├───────────────────────┬────────────────────────────────────────────────┤
│ Layer                 │ Implemented Security Mechanism                 │
├───────────────────────┼────────────────────────────────────────────────┤
│ Ingress & Transport   │ Nginx baseline security headers, CORS origin   │
│                       │ whitelisting, Gzip compression limits          │
├───────────────────────┼────────────────────────────────────────────────┤
│ API & Schema          │ Pydantic V2 strict type validation, parameter  │
│                       │ bounds, regex sanitization, X-Request-ID trace │
├───────────────────────┼────────────────────────────────────────────────┤
│ Credential Protection │ Pydantic SecretStr obscuring secrets in logs   │
│                       │ and debug dumps; no plaintext key persistence  │
├───────────────────────┼────────────────────────────────────────────────┤
│ Database Access       │ 100% Parameterized Cypher & SQL queries;       │
│                       │ complete elimination of string formatting      │
├───────────────────────┼────────────────────────────────────────────────┤
│ Runtime & Container   │ Non-root container execution (appuser:10001);  │
│                       │ multi-stage minimal build images               │
├───────────────────────┼────────────────────────────────────────────────┤
│ AI Execution Safety   │ Bounded timeouts (wait_for), retry limits,     │
│                       │ thread offloading, zero direct DB access       │
└───────────────────────┴────────────────────────────────────────────────┘
```

---

## 3. Credential Protection & `SecretStr`

Application secrets are managed via [`app/core/config.py`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/core/config.py) using Pydantic's [`SecretStr`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/core/config.py):
* `GEMINI_API_KEY`: Protected as `SecretStr`.
* `NEO4J_PASSWORD`: Protected as `SecretStr`.
* `DATABASE_PASSWORD`: Protected as `SecretStr`.

### Prevention of String Leaks
Pydantic's `SecretStr` overrides the `__str__` and `__repr__` methods to output `**********`. If a developer or exception handler inadvertently logs the configuration object or prints an exception traceback, raw credentials are never leaked into console logs, Loguru sinks, or Prometheus metrics:
```python
# Safe retrieval only at driver initialization:
driver = AsyncGraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD.get_secret_value()),
)
```

---

## 4. SQL & Cypher Injection Prevention

### 4.1 Parameterized Relational Queries
The relational data layer utilizes SQLAlchemy 2.0 async ORM models exclusively. No raw string interpolation (`f"SELECT * FROM incidents WHERE ..."` ) exists anywhere in the codebase. All queries are compiled to parameterized SQL statements executed via `asyncpg`.

### 4.2 Parameterized Cypher Queries
All Cypher queries in [`GraphRepository`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/graph/repository.py) pass user-supplied entity identifiers strictly as query parameters (`$value`, `$entity_value`, `$id`):

```python
query = """
MATCH (target {lookup_value: $entity_value})
OPTIONAL MATCH (target)<-[:MENTIONS]-(c1:Complaint)
RETURN c1.complaint_id AS complaint_id
"""
result = await session.run(query, entity_value=entity_value)
```
* Malicious inputs (e.g. `'; DROP ALL NODES; //`) are treated strictly as literal string values and cannot alter the Cypher AST or execute injection attacks.

---

## 5. Input Validation & Bounds Enforcement

All API payloads pass through Pydantic V2 schemas before executing any application code:
* **UUID Validation**: Path parameters for complaints are strictly validated as RFC 4122 UUIDs.
* **Pagination Bounds**: Query parameters like `limit` and `skip` enforce strict boundaries (`ge=1`, `le=100`, `ge=0`) to prevent denial-of-service (DoS) memory exhaustion attacks.
* **Traversal Depth Limits**: Subgraph visualization queries enforce `ge=1, le=5` to prevent unbounded graph traversals from starving Neo4j memory.
* **Risk Score Validation**: Both PostgreSQL check constraints (`ck_incidents_check_risk_score_range`) and Pydantic validators enforce `0.0 <= risk_score <= 1.0`.

---

## 6. Container Runtime Hardening

The production backend image ([`backend/Dockerfile`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/Dockerfile)) enforces strict container security standards:

```dockerfile
# Create a dedicated non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup --create-home appuser

# Set proper ownership
COPY --chown=appuser:appgroup . .
USER appuser
```

* **Non-Root Execution**: The application runs under UID `10001` (`appuser`). If an attacker were to exploit a zero-day vulnerability in a Python library, they would have zero root privileges on the underlying host operating system.
* **Minimal Attack Surface**: Multi-stage build copies only the compiled virtual environment from the builder stage, omitting compiler toolchains (`gcc`, `build-essential`) from the final runtime image.

---

## 7. Edge & Ingress Security (Nginx)

The Nginx reverse proxy enforces baseline HTTP security headers on all incoming traffic:

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

* **Clickjacking Protection**: `SAMEORIGIN` prevents malicious sites from embedding the analyst console inside an invisible iframe.
* **MIME Sniffing Prevention**: `nosniff` prevents browsers from misinterpreting text files as executable JavaScript.
* **Reflected XSS Filter**: Activates browser-native XSS filtering protections.

---

## 8. Enterprise Hardening Roadmap

For production deployment within government law enforcement networks or financial institutions, the following security capabilities must be implemented:

1. **OAuth2 / OIDC Authentication**:
   * Integration with enterprise identity providers (Keycloak, Okta, Azure AD).
   * Replacement of `/api/v1/auth/` placeholder with JWT Bearer token verification middleware.
2. **Role-Based Access Control (RBAC)**:
   * Enforce granular permissions: `analyst:read`, `investigator:create`, `admin:configure`, `auditor:view_governance`.
3. **Immutable Audit Logging**:
   * Ship structured `X-Request-ID` logs to an append-only, tamper-proof log repository (e.g. AWS CloudWatch with S3 Object Lock, or Elasticsearch).
4. **Mutual TLS (mTLS)**:
   * Encrypt intra-service communication between Nginx, FastAPI, PostgreSQL, and Neo4j using mTLS certificates.
5. **Dynamic Secret Management**:
   * Retrieve database and Gemini credentials from HashiCorp Vault or AWS Secrets Manager with automated key rotation.
