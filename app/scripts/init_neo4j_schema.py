"""
🌌 Neo4j Schema Initialization for 4D Memory System

Erstellt Constraints und Indexes für optimale Graph-Performance.
"""

from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_neo4j_schema(
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "liara_neo4j_2025"
):
    """
    Erstellt Constraints und Indexes für Neo4j 4D Memory
    """
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        logger.info("Creating Neo4j constraints...")
        
        # ====================================================================
        # CONSTRAINTS (Uniqueness + Existence)
        # ====================================================================
        
        constraints = [
            # User
            """
            CREATE CONSTRAINT user_id_unique IF NOT EXISTS
            FOR (u:User) REQUIRE u.user_id IS UNIQUE
            """,
            
            # Message
            """
            CREATE CONSTRAINT message_unique IF NOT EXISTS
            FOR (m:Message) REQUIRE (m.user_id, m.message_id) IS UNIQUE
            """,
            
            # Concept (text + user_id muss unique sein)
            """
            CREATE CONSTRAINT concept_unique IF NOT EXISTS
            FOR (c:Concept) REQUIRE (c.text, c.user_id) IS UNIQUE
            """,
            
            # Entity
            """
            CREATE CONSTRAINT entity_unique IF NOT EXISTS
            FOR (e:Entity) REQUIRE (e.text, e.type, e.user_id) IS UNIQUE
            """,
            
            # Task
            """
            CREATE CONSTRAINT task_unique IF NOT EXISTS
            FOR (t:Task) REQUIRE (t.user_id, t.task_id) IS UNIQUE
            """,
            
            # Note
            """
            CREATE CONSTRAINT note_unique IF NOT EXISTS
            FOR (n:Note) REQUIRE (n.user_id, n.note_id) IS UNIQUE
            """,
            
            # Event
            """
            CREATE CONSTRAINT event_unique IF NOT EXISTS
            FOR (e:Event) REQUIRE (e.user_id, e.event_id) IS UNIQUE
            """,
            
            # Mood
            """
            CREATE CONSTRAINT mood_unique IF NOT EXISTS
            FOR (m:Mood) REQUIRE (m.user_id, m.timestamp) IS UNIQUE
            """
        ]
        
        for constraint in constraints:
            try:
                session.run(constraint)
                # Extract node type from constraint
                node_type = constraint.split('FOR (')[1].split(':')[1].split(')')[0].strip()
                logger.info(f"✓ Created constraint for {node_type}")
            except Exception as e:
                if "already exists" in str(e) or "equivalent" in str(e):
                    logger.debug(f"Constraint already exists: {e}")
                else:
                    logger.error(f"Failed to create constraint: {e}")
        
        logger.info("\nCreating Neo4j indexes...")
        
        # ====================================================================
        # INDEXES (Performance)
        # ====================================================================
        
        indexes = [
            # User timestamps
            """
            CREATE INDEX user_created IF NOT EXISTS
            FOR (u:User) ON (u.created_at)
            """,
            
            """
            CREATE INDEX user_last_active IF NOT EXISTS
            FOR (u:User) ON (u.last_active)
            """,
            
            # Message timestamps
            """
            CREATE INDEX message_timestamp IF NOT EXISTS
            FOR (m:Message) ON (m.timestamp)
            """,
            
            """
            CREATE INDEX message_role IF NOT EXISTS
            FOR (m:Message) ON (m.role)
            """,
            
            # Concept fields
            """
            CREATE INDEX concept_mention_count IF NOT EXISTS
            FOR (c:Concept) ON (c.mention_count)
            """,
            
            """
            CREATE INDEX concept_created IF NOT EXISTS
            FOR (c:Concept) ON (c.created_at)
            """,
            
            # Entity types
            """
            CREATE INDEX entity_type IF NOT EXISTS
            FOR (e:Entity) ON (e.type)
            """,
            
            # Task fields
            """
            CREATE INDEX task_created IF NOT EXISTS
            FOR (t:Task) ON (t.created_at)
            """,
            
            # Note fields
            """
            CREATE INDEX note_created IF NOT EXISTS
            FOR (n:Note) ON (n.created_at)
            """,
            
            # Event fields
            """
            CREATE INDEX event_start_time IF NOT EXISTS
            FOR (e:Event) ON (e.start_time)
            """,
            
            # Mood fields
            """
            CREATE INDEX mood_timestamp IF NOT EXISTS
            FOR (m:Mood) ON (m.timestamp)
            """
        ]
        
        for index in indexes:
            try:
                session.run(index)
                # Extract index name
                index_name = index.split('INDEX ')[1].split(' IF')[0].strip()
                logger.info(f"✓ Created index: {index_name}")
            except Exception as e:
                if "already exists" in str(e) or "equivalent" in str(e):
                    logger.debug(f"Index already exists: {e}")
                else:
                    logger.error(f"Failed to create index: {e}")
        
        logger.info("\n✅ Neo4j schema initialization complete!")
        
        # Display current schema
        logger.info("\nCurrent constraints:")
        result = session.run("SHOW CONSTRAINTS")
        for record in result:
            logger.info(f"  - {record.get('name', 'Unknown')}")
        
        logger.info("\nCurrent indexes:")
        result = session.run("SHOW INDEXES")
        for record in result:
            logger.info(f"  - {record.get('name', 'Unknown')}")
    
    driver.close()


if __name__ == "__main__":
    print("=== Initializing Neo4j Schema for 4D Memory ===\n")
    initialize_neo4j_schema()
    print("\n✅ Done! Neo4j is ready for 4D Memory operations.")
