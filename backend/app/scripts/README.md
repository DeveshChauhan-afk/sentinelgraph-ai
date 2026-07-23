# Demo Dataset

## Build Dataset

```bash
python scripts/build_demo_dataset.py
```

## Seed Dataset

```bash
python scripts/seed_demo_data.py
```

Make sure the FastAPI server is running before seeding.

The incidents will automatically:

- Pass validation
- Be stored in PostgreSQL
- Be analyzed by Gemini
- Populate Neo4j