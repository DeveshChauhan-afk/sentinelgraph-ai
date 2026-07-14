import asyncio

from app.db.neo4j import connect_neo4j, disconnect_neo4j


async def main():
    await connect_neo4j()
    print("Neo4j connected successfully.")
    await disconnect_neo4j()


if __name__ == "__main__":
    asyncio.run(main())
