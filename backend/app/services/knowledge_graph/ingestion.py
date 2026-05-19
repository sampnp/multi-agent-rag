"""
Upserts extracted entities and relationships into Neo4j.
Uses MERGE to deduplicate nodes across multiple document ingestions.
Timestamps on all nodes and relationships.
"""
import time


async def ingest(doc_id: str, doc_name: str, extraction: dict, driver) -> dict:
    """
    Persist entities and relationships extracted from a document.
    Returns counts of nodes and relationships written.
    """
    if not driver:
        return {"nodes": 0, "relationships": 0}

    entities = extraction.get("entities", [])
    relationships = extraction.get("relationships", [])
    now = time.time()

    nodes_written = 0
    rels_written = 0

    async with driver.session() as session:
        # 1. Upsert Document node
        await session.run(
            "MERGE (d:Document {doc_id: $doc_id}) "
            "ON CREATE SET d.name = $name, d.created_at = $ts "
            "ON MATCH SET d.name = $name",
            doc_id=doc_id, name=doc_name, ts=now,
        )

        # 2. Upsert entity nodes (MERGE on name, label-specific)
        for e in entities:
            label = e["type"]
            await session.run(
                f"MERGE (n:{label} {{name: $name}}) "
                "ON CREATE SET n.description = $desc, n.created_at = $ts "
                "ON MATCH SET n.description = CASE WHEN $desc <> '' THEN $desc ELSE n.description END",
                name=e["name"], desc=e["description"], ts=now,
            )
            nodes_written += 1

        # 3. Document MENTIONS entity
        for e in entities:
            label = e["type"]
            await session.run(
                f"MATCH (d:Document {{doc_id: $doc_id}}) "
                f"MATCH (n:{label} {{name: $name}}) "
                "MERGE (d)-[r:MENTIONS]->(n) "
                "ON CREATE SET r.created_at = $ts",
                doc_id=doc_id, name=e["name"], ts=now,
            )

        # 4. Upsert extracted relationships
        for r in relationships:
            fl, tl = r["from_type"], r["to_type"]
            rel = r["relation"]
            await session.run(
                f"MERGE (a:{fl} {{name: $from_name}}) "
                "ON CREATE SET a.created_at = $ts "
                f"MERGE (b:{tl} {{name: $to_name}}) "
                "ON CREATE SET b.created_at = $ts "
                f"MERGE (a)-[r:{rel}]->(b) "
                "ON CREATE SET r.created_at = $ts, r.weight = 1 "
                "ON MATCH SET r.weight = r.weight + 1",
                from_name=r["from"], to_name=r["to"], ts=now,
            )
            rels_written += 1

    return {"nodes": nodes_written, "relationships": rels_written}
