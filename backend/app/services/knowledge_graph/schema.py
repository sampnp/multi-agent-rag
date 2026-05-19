"""
Neo4j schema constants and constraint bootstrap.

Node labels  : Person, Organization, Project, Topic, Concept, Document
Relationships: MENTIONS, WORKS_ON, BELONGS_TO, RELATES_TO, DEPENDS_ON
"""

VALID_LABELS = {"Person", "Organization", "Project", "Topic", "Concept", "Document"}
VALID_RELATIONS = {"MENTIONS", "WORKS_ON", "BELONGS_TO", "RELATES_TO", "DEPENDS_ON"}

# Shown to the LLM when generating Cypher
SCHEMA_DESCRIPTION = """
Node labels and typical properties:
  Person         (name, description, created_at)
  Organization   (name, description, created_at)
  Project        (name, description, created_at)
  Topic          (name, description, created_at)
  Concept        (name, description, created_at)
  Document       (doc_id, name, created_at)

Relationship types (all have created_at):
  (Person)-[:WORKS_ON]->(Project)
  (Person)-[:BELONGS_TO]->(Organization)
  (Person)-[:MENTIONS]->(Topic|Concept)
  (Document)-[:MENTIONS]->(Person|Organization|Project|Topic|Concept)
  (Project)-[:RELATES_TO]->(Project|Topic|Concept)
  (Project)-[:DEPENDS_ON]->(Project)
  (Concept)-[:RELATES_TO]->(Concept|Topic)
  (Organization)-[:WORKS_ON]->(Project)
""".strip()


_CONSTRAINTS = [
    "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (n:Person) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT org_name IF NOT EXISTS FOR (n:Organization) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT project_name IF NOT EXISTS FOR (n:Project) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (n:Topic) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (n:Concept) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (n:Document) REQUIRE n.doc_id IS UNIQUE",
]


async def ensure_schema(driver) -> None:
    try:
        async with driver.session() as session:
            for stmt in _CONSTRAINTS:
                await session.run(stmt)
    except Exception:
        pass
