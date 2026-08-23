"""
🌌 LIARA 4D Memory - Neo4j Graph Service
Dimension 4: Relational Layer

Manages knowledge graph in Neo4j for complex relationship tracking.
"""

from neo4j import GraphDatabase
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Neo4jGraphService:
    """Service for managing Neo4j knowledge graph"""
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", 
                 password: str = "liara_neo4j_2025"):
        """
        Initialize Neo4j connection
        
        Args:
            uri: Neo4j bolt URI
            user: Database user
            password: Database password
        """
        self.uri = uri
        self.user = user
        self._driver = None
        self._password = password
        logger.info(f"Initializing Neo4jGraphService: {uri}")
    
    @property
    def driver(self):
        """Lazy load the Neo4j driver"""
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self._password))
                logger.info("Neo4j driver connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise
        return self._driver
    
    def close(self):
        """Close Neo4j connection"""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")
    
    def initialize_schema(self):
        """
        Create constraints and indexes for the graph schema
        """
        with self.driver.session() as session:
            # Constraints for uniqueness
            constraints = [
                "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
                "CREATE CONSTRAINT message_unique IF NOT EXISTS FOR (m:Message) REQUIRE (m.user_id, m.message_id) IS UNIQUE",
                "CREATE CONSTRAINT task_unique IF NOT EXISTS FOR (t:Task) REQUIRE (t.user_id, t.task_id) IS UNIQUE",
                "CREATE CONSTRAINT note_unique IF NOT EXISTS FOR (n:Note) REQUIRE (n.user_id, n.note_id) IS UNIQUE",
                "CREATE CONSTRAINT event_unique IF NOT EXISTS FOR (e:Event) REQUIRE (e.user_id, e.event_id) IS UNIQUE",
                "CREATE CONSTRAINT mood_unique IF NOT EXISTS FOR (m:Mood) REQUIRE (m.user_id, m.timestamp) IS UNIQUE",
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"Created constraint: {constraint.split('FOR')[1].split('REQUIRE')[0].strip()}")
                except Exception as e:
                    logger.debug(f"Constraint already exists or error: {e}")
            
            # Indexes for performance
            indexes = [
                "CREATE INDEX user_timestamp IF NOT EXISTS FOR (u:User) ON (u.created_at)",
                "CREATE INDEX message_timestamp IF NOT EXISTS FOR (m:Message) ON (m.timestamp)",
                "CREATE INDEX task_timestamp IF NOT EXISTS FOR (t:Task) ON (t.created_at)",
                "CREATE INDEX mood_timestamp IF NOT EXISTS FOR (m:Mood) ON (m.timestamp)",
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    logger.info(f"Created index: {index.split('FOR')[1].strip()}")
                except Exception as e:
                    logger.debug(f"Index already exists or error: {e}")
        
        logger.info("Neo4j schema initialization complete")
    
    def create_user_node(self, user_id: int, username: str, properties: Optional[Dict] = None):
        """Create or update user node"""
        with self.driver.session() as session:
            query = """
            MERGE (u:User {user_id: $user_id})
            SET u.username = $username,
                u.updated_at = datetime()
            SET u += $properties
            RETURN u
            """
            session.run(query, user_id=user_id, username=username, properties=properties or {})
            logger.info(f"Created/updated user node: {username} (ID: {user_id})")
    
    def create_content_node(self, content_type: str, content_id: int, user_id: int, 
                           properties: Dict):
        """
        Create content node (Message, Task, Note, Event)
        
        Args:
            content_type: Type of content (Message, Task, Note, Event)
            content_id: ID of the content
            user_id: User ID
            properties: Additional properties for the node
        """
        with self.driver.session() as session:
            query = f"""
            MATCH (u:User {{user_id: $user_id}})
            MERGE (c:{content_type} {{user_id: $user_id, {content_type.lower()}_id: $content_id}})
            SET c += $properties
            MERGE (u)-[:CREATED]->(c)
            RETURN c
            """
            session.run(query, user_id=user_id, content_id=content_id, properties=properties)
            logger.debug(f"Created {content_type} node: {content_id}")
    
    def delete_user_memory(self, user_id: int) -> int:
        """
        Delete all graph memory for a user (Concept/Message/Task/Note/Event/
        Mood/User nodes and their relationships) - used by the "Erinnerungen
        löschen" preference action. All node types created by this service
        carry a user_id property regardless of label, so a single property
        match covers them without needing to enumerate every label.

        Returns the number of nodes deleted.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n {user_id: $user_id})
                DETACH DELETE n
                RETURN count(n) as deleted
            """, user_id=user_id)
            deleted = result.single()["deleted"]
            logger.info(f"Deleted {deleted} Neo4j nodes for user {user_id}")
            return deleted

    def get_last_assistant_message_id(self, user_id: int, session_id: int) -> Optional[int]:
        """
        Find the most recent assistant Message node in a specific
        conversation - used to retroactively tag it with an outcome
        signal once the user's next message arrives.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (m:Message {user_id: $user_id, session_id: $session_id, role: 'assistant'})
                RETURN m.message_id as message_id
                ORDER BY m.timestamp DESC
                LIMIT 1
            """, user_id=user_id, session_id=session_id).single()
            return result["message_id"] if result else None

    def tag_message_outcome(self, user_id: int, message_id: int, outcome_sentiment: str, outcome_score: float):
        """
        Tag an assistant Message node with a lightweight outcome signal -
        the sentiment of the user's next message, used as a proxy for
        "how did this response land". Capture-only: nothing currently
        reads this back to change behavior.
        """
        with self.driver.session() as session:
            session.run("""
                MATCH (m:Message {user_id: $user_id, message_id: $message_id})
                SET m.outcome_sentiment = $outcome_sentiment,
                    m.outcome_score = $outcome_score,
                    m.outcome_tagged_at = datetime()
            """, user_id=user_id, message_id=message_id,
                outcome_sentiment=outcome_sentiment, outcome_score=outcome_score)

    def create_mood_node(self, user_id: int, timestamp: str, mood: str, energy_level: int,
                        properties: Optional[Dict] = None):
        """Create mood node and link to user"""
        with self.driver.session() as session:
            query = """
            MATCH (u:User {user_id: $user_id})
            CREATE (m:Mood {
                user_id: $user_id,
                timestamp: datetime($timestamp),
                mood: $mood,
                energy_level: $energy_level
            })
            SET m += $properties
            MERGE (u)-[:EXPERIENCED]->(m)
            RETURN m
            """
            session.run(query, user_id=user_id, timestamp=timestamp, mood=mood, 
                       energy_level=energy_level, properties=properties or {})
            logger.debug(f"Created mood node: {mood} at {timestamp}")
    
    def create_relationship(self, source_type: str, source_id: int, 
                           target_type: str, target_id: int,
                           relation_type: str, user_id: int,
                           properties: Optional[Dict] = None):
        """
        Create relationship between two nodes
        
        Args:
            source_type: Source node type
            source_id: Source node ID
            target_type: Target node type
            target_id: Target node ID
            relation_type: Type of relationship
            user_id: User ID
            properties: Additional relationship properties
        """
        with self.driver.session() as session:
            query = f"""
            MATCH (source:{source_type} {{user_id: $user_id, {source_type.lower()}_id: $source_id}})
            MATCH (target:{target_type} {{user_id: $user_id, {target_type.lower()}_id: $target_id}})
            MERGE (source)-[r:{relation_type}]->(target)
            SET r += $properties
            SET r.created_at = datetime()
            RETURN r
            """
            session.run(query, user_id=user_id, source_id=source_id, target_id=target_id,
                       properties=properties or {})
            logger.debug(f"Created relationship: {source_type}→{relation_type}→{target_type}")
    
    def link_content_to_mood(self, content_type: str, content_id: int, 
                            mood_timestamp: str, user_id: int,
                            caused_by: bool = False):
        """
        Link content to mood (either caused by content or influenced content)
        
        Args:
            content_type: Type of content
            content_id: Content ID
            mood_timestamp: Mood timestamp
            user_id: User ID
            caused_by: If True, content CAUSED mood; if False, mood INFLUENCED content
        """
        with self.driver.session() as session:
            if caused_by:
                relation = "CAUSED_MOOD"
                query = f"""
                MATCH (c:{content_type} {{user_id: $user_id, {content_type.lower()}_id: $content_id}})
                MATCH (m:Mood {{user_id: $user_id, timestamp: datetime($mood_timestamp)}})
                MERGE (c)-[r:{relation}]->(m)
                SET r.detected_at = datetime()
                RETURN r
                """
            else:
                relation = "INFLUENCED_BY_MOOD"
                query = f"""
                MATCH (c:{content_type} {{user_id: $user_id, {content_type.lower()}_id: $content_id}})
                MATCH (m:Mood {{user_id: $user_id, timestamp: datetime($mood_timestamp)}})
                MERGE (c)-[r:{relation}]->(m)
                SET r.detected_at = datetime()
                RETURN r
                """
            
            session.run(query, user_id=user_id, content_id=content_id, 
                       mood_timestamp=mood_timestamp)
            logger.debug(f"Linked {content_type} to mood: {relation}")
    
    def find_related_content(self, content_type: str, content_id: int, user_id: int,
                            max_depth: int = 2, limit: int = 10) -> List[Dict]:
        """
        Find related content using graph traversal
        
        Args:
            content_type: Type of content to start from
            content_id: Content ID
            user_id: User ID
            max_depth: Maximum depth for graph traversal
            limit: Maximum number of results
            
        Returns:
            List of related content nodes with relationship info
        """
        with self.driver.session() as session:
            query = f"""
            MATCH path = (source:{content_type} {{user_id: $user_id, {content_type.lower()}_id: $content_id}})
                        -[*1..{max_depth}]-(related)
            WHERE related:Message OR related:Task OR related:Note OR related:Event
            WITH related, relationships(path) as rels, length(path) as distance
            RETURN DISTINCT 
                labels(related)[0] as type,
                properties(related) as properties,
                distance,
                [r in rels | type(r)] as relationship_chain
            ORDER BY distance
            LIMIT $limit
            """
            result = session.run(query, user_id=user_id, content_id=content_id, limit=limit)
            
            related = []
            for record in result:
                related.append({
                    'type': record['type'],
                    'properties': dict(record['properties']),
                    'distance': record['distance'],
                    'relationship_chain': record['relationship_chain']
                })
            
            logger.info(f"Found {len(related)} related items for {content_type}:{content_id}")
            return related
    
    def find_mood_patterns(self, user_id: int, days: int = 7) -> List[Dict]:
        """
        Analyze mood patterns and what triggers them
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            List of mood patterns with triggers
        """
        with self.driver.session() as session:
            query = """
            MATCH (u:User {user_id: $user_id})-[:EXPERIENCED]->(m:Mood)
            WHERE m.timestamp > datetime() - duration({days: $days})
            OPTIONAL MATCH (trigger)-[:CAUSED_MOOD]->(m)
            RETURN 
                m.mood as mood,
                m.energy_level as energy,
                m.timestamp as timestamp,
                labels(trigger)[0] as trigger_type,
                properties(trigger) as trigger_properties
            ORDER BY m.timestamp DESC
            """
            result = session.run(query, user_id=user_id, days=days)
            
            patterns = []
            for record in result:
                patterns.append({
                    'mood': record['mood'],
                    'energy': record['energy'],
                    'timestamp': str(record['timestamp']),
                    'trigger_type': record['trigger_type'],
                    'trigger_properties': dict(record['trigger_properties']) if record['trigger_properties'] else None
                })
            
            return patterns
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """
        Get user's model preferences and interaction patterns
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with preference data
        """
        with self.driver.session() as session:
            query = """
            MATCH (u:User {user_id: $user_id})
            OPTIONAL MATCH (u)-[pref:PREFERS_MODEL]->(model:Model)
            RETURN u, collect({model: model.name, weight: pref.weight}) as preferences
            """
            result = session.run(query, user_id=user_id).single()
            
            if result:
                return {
                    'user': dict(result['u']),
                    'model_preferences': result['preferences']
                }
            return {}
    
    def record_model_preference(self, user_id: int, model_name: str, weight: float = 1.0):
        """
        Record or update user's preference for a specific model
        
        Args:
            user_id: User ID
            model_name: Name of the model
            weight: Preference weight (higher = more preferred)
        """
        with self.driver.session() as session:
            query = """
            MATCH (u:User {user_id: $user_id})
            MERGE (m:Model {name: $model_name})
            MERGE (u)-[p:PREFERS_MODEL]->(m)
            SET p.weight = p.weight + $weight,
                p.last_used = datetime()
            RETURN p
            """
            session.run(query, user_id=user_id, model_name=model_name, weight=weight)
            logger.info(f"Updated model preference: {model_name} for user {user_id}")


# Singleton instance
_neo4j_service: Optional[Neo4jGraphService] = None


def get_neo4j_service() -> Neo4jGraphService:
    """Get singleton instance of Neo4jGraphService"""
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jGraphService()
        _neo4j_service.initialize_schema()
    return _neo4j_service


def close_neo4j_service():
    """Close Neo4j connection"""
    global _neo4j_service
    if _neo4j_service:
        _neo4j_service.close()
        _neo4j_service = None
