# SentinelGraph AI: Dual-Database Architecture

## 1. Executive Summary

SentinelGraph AI implements a specialized **Hybrid Dual-Database Architecture** combining a relational database (**PostgreSQL**) and a labeled property graph database (**Neo4j AuraDB**). Each database fulfills a distinct, non-overlapping architectural responsibility within the digital public safety intelligence platform:

1. **PostgreSQL (System of Record)**: Serves as the authoritative, transactional source of truth. It stores raw incident reports, legal case references, triage metadata, reporter identities, case status, audit timestamps, and scalar risk assessments under strict ACID transactional guarantees.
2. **Neo4j AuraDB (Fraud Intelligence Knowledge Graph)**: Serves as the connected entity intelligence layer. It models entities (phone numbers, UPI IDs, bank accounts, emails, organizations, persons, locations, URLs) extracted from complaints and evaluates topological connections, multi-hop linkages, fraud rings, and co-occurrence patterns.

```
┌────────────────────────────────────────────────────────┐
│               PostgreSQL (Relational)                  │
│  - System of Record / Transactional Source of Truth    │
│  - Raw Complaint Texts, Metadata, Status, Auditing     │
│  - ACID Durability & Relational Constraints            │
└──────────────────────────┬─────────────────────────────┘
                           │
             (1) Transactional Commit
             (2) Gemini Entity Extraction
             (3) Graph Build & Save
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                Neo4j AuraDB (Graph)                    │
│  - Fraud Intelligence Knowledge Graph                  │
│  - Nodes: Complaint + 8 Extracted Entity Types         │
│  - Edges: MENTIONS                                     │
│  - Topological Link Analysis & Fraud Ring Detection    │
│  - Deterministic XAI Timeline & Evidence Generation    │
└────────────────────────────────────────────────────────┘
```

### Comparative Architectural Matrix

| Dimension | PostgreSQL (Relational) | Neo4j AuraDB (Property Graph) |
| :--- | :--- | :--- |
| **Primary Role** | Transactional System of Record & Audit Store | Fraud Network Topology & Link Analysis |
| **Data Scope** | Complaints, raw narrative text, triage states, timestamps | Fraud entities, identifiers, and multi-hop connections |
| **Data Model** | Relational tables, typed columns, check constraints, ENUMs | Labeled Property Graph (`(:Complaint)-[:MENTIONS]->(:Entity)`) |
| **Access Patterns** | Primary key lookups, paginated filters, text search | Multi-hop graph traversals, shortest paths, connected rings |
| **Driver / Interface** | Async SQLAlchemy 2.0 (`asyncpg`) | Neo4j Async Driver (`AsyncGraphDatabase`) |
| **Schema Management** | Strict schema migrations managed via Alembic | Application-level node & relationship schema enforcement |
| **Consistency Scope** | ACID transactions with service-managed commit/rollback | Idempotent Cypher `MERGE` inside atomic transactions |

---

## 2. PostgreSQL Relational Architecture

### 2.1 Database Engine & Async Access
* **Engine**: PostgreSQL 16+ accessed via asynchronous I/O.
* **ORM & Toolkit**: SQLAlchemy 2.0 async dialect using the high-performance `asyncpg` driver (`postgresql+asyncpg://`).
* **Session Lifecycle**: Database sessions are instantiated through `async_sessionmaker` configured in [`app/db/database.py`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/db/database.py) with `expire_on_commit=False` and `autoflush=False`.
* **FastAPI Integration**: The `get_db()` dependency yields an isolated `AsyncSession` per HTTP request scope, guaranteeing clean session lifecycle management.

### 2.2 Connection Pooling
The async engine initializes a persistent connection pool with production settings loaded from [`app/core/config.py`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/core/config.py):

| Setting | Default Value | Description |
| :--- | :--- | :--- |
| `DB_POOL_SIZE` | `10` | Base number of persistent database connections maintained in the pool |
| `DB_MAX_OVERFLOW` | `20` | Maximum number of transient connections allowed beyond `DB_POOL_SIZE` |
| `DB_POOL_TIMEOUT` | `30` | Seconds to wait before timing out when acquiring a connection from a saturated pool |
| `DB_POOL_RECYCLE` | `1800` | Seconds (30 minutes) before recycling connections to prevent stale connection drops |
| `pool_pre_ping` | `True` | Emits a lightweight `SELECT 1` ping before checkout to ensure connection liveness |
| `pool_reset_on_return` | `"rollback"` | Explicitly rolls back uncommitted transactions before returning connections to the pool |

### 2.3 `incidents` Table
The `incidents` table (mapped to the [`Incident`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/models/incident.py) ORM model) is the single concrete relational table in the database:

| Column Name | SQL Type | Python / Enum Type | Nullable | Default / Constraints | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `UUID` | `uuid.UUID` | No | Primary Key (`uuid.uuid4`) | Unique incident identifier |
| `title` | `VARCHAR(255)` | `str` | No | &mdash; | Brief title / subject of the report |
| `description` | `TEXT` | `str` | No | &mdash; | Unstructured narrative describing the incident |
| `reporter_type` | `ENUM` (`reporter_type_enum`) | [`ReporterType`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/models/enums.py) | No | Values: `citizen`, `police`, `bank`, `cyber_cell`, `other` | Origin classification of the reporter |
| `source` | `ENUM` (`incident_source_enum`) | [`IncidentSource`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/models/enums.py) | No | Values: `web_portal`, `mobile_app`, `api`, `bulk_import` | Ingestion channel |
| `status` | `ENUM` (`incident_status_enum`) | [`IncidentStatus`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/models/enums.py) | No | Server default: `'new'`, Values: `new`, `processing`, `analyzed`, `under_investigation`, `resolved`, `closed` | Lifecycle stage of the incident |
| `priority` | `ENUM` (`priority_enum`) | [`Priority`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/models/enums.py) | No | Server default: `'medium'`, Values: `low`, `medium`, `high`, `critical` | Triage priority rating |
| `scam_category` | `ENUM` (`scam_category_enum`) | [`ScamCategory`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/models/enums.py) | Yes | Values: `digital_arrest`, `upi_fraud`, `phishing`, `qr_scam`, `identity_theft`, `investment_fraud`, `other`, `unknown` | Categorized fraud scheme |
| `ai_summary` | `TEXT` | `str | None` | Yes | Comment: `"AI-generated fraud summary"` | Synthesized summary generated during processing |
| `risk_score` | `FLOAT` | `float | None` | Yes | Check constraint: `0.0 <= risk_score <= 1.0` | Scalar fraud risk score |
| `graph_node_id` | `VARCHAR(100)` | `str | None` | Yes | Indexed | Informal cross-reference identifier to Neo4j node (e.g. `complaint:<uuid>`) |
| `case_reference` | `VARCHAR(100)` | `str | None` | Yes | Comment: `"External reference identifier (e.g., FIR, Bank Complaint ID)"` | External legal or institutional reference ID |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `datetime` | No | Server default: `now()` | UTC creation timestamp (timezone-aware) |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `datetime` | No | Server default: `now()`, auto-updated on edit | UTC last update timestamp (timezone-aware) |

### 2.4 Keys, Constraints & Indexes
* **Primary Key**: `pk_incidents` on `id` (`UUID`).
* **Foreign Keys**: **None**. The relational schema is streamlined to a single table; relationships between complaints and entities are modeled in the property graph rather than via relational join tables.
* **Check Constraints**:
  * `ck_incidents_check_risk_score_range`: Enforces `risk_score >= 0 AND risk_score <= 1`.
* **Explicit B-Tree Indexes**:
  * `idx_incident_status` on `(status)`: Optimizes state-based filtering and triage queues.
  * `idx_incident_priority` on `(priority)`: Speeds up priority-ranked queue retrieval.
  * `idx_incident_created` on `(created_at)`: Accelerates chronological ordering and pagination.
  * `ix_incidents_graph_node_id` on `(graph_node_id)`: Facilitates lookup by graph reference.
* **Naming Conventions**: A centralized naming convention registry is defined on SQLAlchemy [`metadata`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/db/base.py) ensuring deterministic constraint and index naming across migrations (`ix_...`, `uq_...`, `ck_...`, `fk_...`, `pk_...`).

### 2.5 Repository & Transaction Architecture
* **[`BaseRepository[ModelType]`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/repositories/base.py)**: Generic data-access abstraction providing `get_by_id`, `require`, `get_all`, `first`, `find_by`, `create`, `update`, `delete`, `count`, and `exists`.
* **[`IncidentRepository`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/repositories/incident.py)**: Domain-specific queries including `get_by_status`, `get_by_priority`, `get_by_scam_category`, `get_by_case_reference`, `get_recent`, `get_processing_queue`, `get_high_risk`, and case-insensitive keyword `search`.
* **Service-Owned Transaction Boundaries**: The repository layer executes database statements and flushes them to the session without committing. The service layer ([`IncidentService`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/services/incident_service.py)) explicitly owns transaction boundaries:
  ```python
  try:
      incident = await self._repository.create(incident_data)
      await self._session.commit()
  except Exception:
      await self._session.rollback()
      raise
  ```

### 2.6 Alembic Migrations
* **Configuration**: Managed via [`alembic.ini`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/alembic.ini) and [`alembic/env.py`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/alembic/env.py).
* **Driver Strategy**: Migrations run synchronously using `postgresql+psycopg2` via the dynamically computed `settings.SYNC_DATABASE_URL`, bypassing async event loop overhead during CLI migrations.
* **Current Schema Revision**:
  * [`3d3cf359c2a1_create_incidents_table.py`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/alembic/versions/3d3cf359c2a1_create_incidents_table.py): Base revision creating the `incidents` table, 5 custom ENUM types, check constraints, primary key, and indexes.
* **Schema Evolution**: All relational database modifications require explicit Alembic migration scripts tested against autogeneration comparison flags (`compare_type=True`, `compare_server_default=True`).

---

## 3. Neo4j AuraDB Property Graph Architecture

### 3.1 Graph Model
Neo4j AuraDB persists the Fraud Intelligence Graph. The graph consists of 9 distinct node labels defined in [`GraphLabel`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/graph/models.py) and constructed by [`GraphBuilder`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/graph/builder.py):

| Node Label | ID Prefix Format | Example ID | Primary Properties |
| :--- | :--- | :--- | :--- |
| `Complaint` | `complaint:<uuid>` | `complaint:3d3cf359-0000-...` | `id`, `complaint_id`, `lookup_value`, `created_at` (ISO 8601 string) |
| `Phone` | `phone:<value>` | `phone:+919876543210` | `id`, `value`, `confidence`, `lookup_value` |
| `UPI` | `upi:<value>` | `upi:fraudster@okhdfcbank` | `id`, `value`, `confidence`, `lookup_value` |
| `Email` | `email:<value>` | `email:support@fake-refund.com` | `id`, `value`, `confidence`, `lookup_value` |
| `URL` | `url:<value>` | `url:https://phishing-portal.xyz` | `id`, `value`, `confidence`, `lookup_value` |
| `BankAccount` | `bank:<value>` | `bank:987654321098` | `id`, `value`, `confidence`, `lookup_value` |
| `Organization` | `org:<value>` | `org:Cyber Crime Branch Police` | `id`, `value`, `confidence`, `lookup_value` |
| `Person` | `person:<value>` | `person:Rajesh Sharma` | `id`, `value`, `confidence`, `lookup_value` |
| `Location` | `location:<value>` | `location:New Delhi` | `id`, `value`, `confidence`, `lookup_value` |

* **Deterministic Node IDs**: Node IDs use a standardized `<prefix>:<normalized_value>` schema, ensuring that identical entities extracted from separate complaints resolve to the exact same graph node.
* **`lookup_value` Property**: Every node stores a `lookup_value` property indexed for polymorphic search across different node types without requiring label-specific queries.

### 3.2 Relationship Model

> **Important**: `MENTIONS` is the **only** relationship type currently persisted in Neo4j.

The topological structure connects `Complaint` nodes directly to extracted entity nodes:

```text
(Complaint)-[:MENTIONS]->(Entity)
```

```
(c1:Complaint {id: "complaint:abc"}) ──[:MENTIONS]──► (e1:Phone {id: "phone:+919876543210"})
                                                              ▲
(c2:Complaint {id: "complaint:xyz"}) ──[:MENTIONS]────────────┘
```

#### Multi-Hop Graph Traversal
Multi-hop fraud network intelligence is evaluated entirely by traversing multiple `MENTIONS` relationships across shared entities:
* **Shared Entity Detection**: `(c1:Complaint)-[:MENTIONS]->(e)<-[:MENTIONS]-(c2:Complaint)`
* **Fraud Ring Discovery**: Discovered by traversing connected paths of arbitrary depth `MATCH (entity)-[*0..6]-(connected)` through interconnected complaint and entity nodes.
* **Analytical Concepts vs Persisted Types**: Concepts such as suspect associations, co-conspirator networks, financial flow traces, or "reported in" lineages are computed dynamically by query traversals and deterministic reasoning engines; they are **not** separate persisted relationship types in Neo4j.

### 3.3 Persistence & Idempotency
Graph persistence is executed in an atomic transaction via [`GraphRepository.save_graph`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/graph/repository.py). The repository uses Cypher `MERGE` statements to guarantee application-level idempotency:

1. **Node Merging**:
   ```cypher
   MERGE (n:<Label> {id: $id})
   SET n += $properties
   ```
   * If a node with the given `id` already exists, its properties (such as confidence or latest timestamps) are updated without creating duplicates.
2. **Relationship Merging**:
   ```cypher
   MATCH (source:<SourceLabel> {id: $source_id})
   MATCH (target:<TargetLabel> {id: $target_id})
   MERGE (source)-[r:MENTIONS]->(target)
   SET r += $properties
   ```
   * Ensures that redundant extraction of the same entity in a complaint does not create duplicate edges.

### 3.4 Graph Constraints & Indexes
* **Database Constraints**: Currently, **no DDL constraint creation commands** (e.g., `CREATE CONSTRAINT ... IF NOT EXISTS`) are executed programmatically in application startup or migrations.
* **Uniqueness Guarantees**: Uniqueness and deduplication are maintained at the application layer via deterministic ID prefixing (`<prefix>:<value>`) combined with Cypher `MERGE` queries. Application-level `MERGE` ensures deduplication during normal application flow, but is distinct from database-enforced schema uniqueness constraints.

### 3.5 Graph Query Patterns
[`GraphRepository`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/graph/repository.py) and [`GraphQueryService`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/graph/query_service.py) provide optimized Cypher query patterns supporting the investigation and XAI pipeline:

| Query Capability | Repository Method | Traversal Strategy |
| :--- | :--- | :--- |
| **Entity Lookup** | `find_entity(value)` | Matches node where `n.lookup_value = $value` |
| **Neighbor Expansion** | `find_neighbors(value)` | 1-hop bidirectional expansion `(entity)-[]-(neighbor)` |
| **Related Incidents** | `find_related_incidents(value)` | Traverses directly connected and 2-hop connected `Complaint` nodes |
| **Entity Risk Assessment** | `get_risk_metrics(value)` | Aggregates incident count, degree centrality, and counts by entity label |
| **Fraud Ring Discovery** | `find_fraud_ring(value)` | Variable-length path traversal `MATCH (entity)-[*0..6]-(connected)` to extract the complete connected component |
| **Shortest Path Analysis** | `find_shortest_path(src, tgt)` | Executes Cypher `shortestPath((source)-[*]-(target))` |
| **Shared Entity Analysis** | `get_shared_entities()` | Identifies entities connected to $\ge 2$ distinct `Complaint` nodes |
| **Timeline Reconstruction** | `get_connected_complaints()` | Traverses shared entity connections to collect chronological complaint timestamps for evolution modeling |
| **Network Statistics** | `get_network_summary()` | Aggregates total node and relationship counts partitioned by label |

---

## 4. Cross-Database Ingestion & Consistency

### 4.1 Ingestion Lifecycle

```
[Inbound Request: POST /api/v1/complaints]
                  │
                  ▼
   1. Persist to PostgreSQL
      - Create Incident record
      - Commit transaction (await session.commit())
                  │
                  ▼
   2. Asynchronous AI Entity Extraction
      - Pass description text to Gemini SDK
      - Extract phone numbers, UPI IDs, emails, etc.
                  │
                  ▼
   3. Transform to Graph Model
      - GraphBuilder creates GraphData (Nodes + MENTIONS Edges)
      - Formats deterministic node IDs (e.g. upi:user@okhdfc)
                  │
                  ▼
   4. Persist to Neo4j AuraDB
      - Atomic write transaction (session.execute_write)
      - Idempotent MERGE for nodes and relationships
```

### 4.2 Failure Boundaries & Consistency Guarantees
* **PostgreSQL as Independent Anchor**: The PostgreSQL commit occurs *before* AI entity extraction and Neo4j graph persistence. Once the PostgreSQL transaction succeeds, the complaint is permanently stored.
* **Fault Isolation**: If Gemini entity extraction fails (`AIError`) or Neo4j persistence fails (`GraphError`), the failure is caught, logged with full stack context, and handled gracefully:
  ```python
  # app/services/incident_service.py
  try:
      entities = await self._entity_extraction_service.extract_entities(incident.description)
      await self._graph_service.build_and_persist(incident.id, incident.created_at, entities)
  except (AIError, GraphError):
      logger.exception("Downstream graph synchronization failed for incident '{}'.", incident.id)
  ```
  The PostgreSQL record is **not** rolled back, ensuring zero data loss for incoming public safety reports.
* **Distributed Consistency Model**: SentinelGraph AI utilizes an **application-orchestrated dual-write pattern with decoupled failure isolation**. There is no distributed 2-Phase Commit (2PC), distributed transaction manager, or asynchronous Outbox / Change Data Capture (CDC) pipeline.
* **Graph Recovery & Rebuilding**: To reconcile inconsistencies or rebuild the graph from scratch, the platform includes a dedicated recovery script ([`backend/app/scripts/rebuild_graph.py`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/scripts/rebuild_graph.py)). The script reads all complaints from PostgreSQL, clears Neo4j via `clear_graph()`, re-extracts entities, rebuilds all graph nodes and `MENTIONS` edges, and validates complaint timestamp parity.

---

## 5. Database Responsibility Boundaries

| Concern | PostgreSQL | Neo4j AuraDB |
| :--- | :---: | :---: |
| **Raw Complaint & Text Narrative Storage** | **Primary** (System of Record) | Not Stored |
| **Case Lifecycle & Status Tracking** | **Primary** (`status`, `priority`) | Not Stored |
| **External & Legal Reference Identifiers** | **Primary** (`case_reference`) | Not Stored |
| **Audit Timestamps (`created_at`, `updated_at`)** | **Primary** (Timezone-aware) | Secondary (`created_at` on Complaint node) |
| **Entity Extraction Confidence Scores** | Not Stored | **Primary** (`confidence` property on entity nodes) |
| **Entity-to-Complaint Relationships** | Informal (`graph_node_id`) | **Primary** (`MENTIONS` relationship) |
| **Multi-Hop Fraud Network Traversal** | Not Supported | **Primary** (Variable-length Cypher traversals) |
| **Fraud Ring & Connected Component Detection** | Not Supported | **Primary** (`find_fraud_ring` traversal) |
| **Shortest Path Link Analysis** | Not Supported | **Primary** (`shortestPath` queries) |
| **Shared Identifier Correlation** | Inefficient (Requires Text Scans) | **Primary** (Topological multi-complaint matching) |
| **Timeline Evolution Data Source** | Relational Source of Truth | **Graph Retrieval Source** (`get_connected_complaints`) |

---

## 6. Schema Evolution & Operational Notes

### 6.1 PostgreSQL Evolution Strategy
* Schema changes to PostgreSQL (such as adding columns, modifying ENUM definitions, or creating indexes) are strictly managed via **Alembic migration scripts** located in `backend/alembic/versions/`.
* Migrations must be executed via `alembic upgrade head` during deployment or container startup.
* Model definitions in `app/models/` must remain in 1:1 synchronization with Alembic revisions.

### 6.2 Neo4j Schema Behavior & Management
* The graph database operates under an application-governed schema model where labels and relationship types are enforced through Pydantic domain models ([`GraphLabel`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/graph/models.py) and [`RelationshipType`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/graph/models.py)).
* Idempotency is preserved across repeated ingestions via Cypher `MERGE` operations on standardized prefix IDs (`<prefix>:<value>`).

### 6.3 Disaster Recovery & Graph Rebuild
In the event of graph database corruption, database migration, or model adjustments:
1. PostgreSQL contains the complete historical record of all reported complaints.
2. The rebuild tool [`backend/app/scripts/rebuild_graph.py`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/scripts/rebuild_graph.py) can be run to wipe Neo4j and sequentially re-populate all graph nodes, `MENTIONS` edges, and complaint timestamps.

---

## 7. Related Documentation

* [`README.md`](../README.md): Project overview, quickstart instructions, and API routes.
* [`docs/ARCHITECTURE.md`](ARCHITECTURE.md): System architecture specification, middleware pipeline, observability, and containerization.
* [`AI_ARCHITECTURE.md`](AI_ARCHITECTURE.md): Deterministic Explainable AI (XAI) pipeline, evidence synthesis engine, prompt fingerprinting, and evaluation framework.
