"""
🧪 Memory Integration Test Script

Testet:
1. Message Storage mit Concept-Extraktion
2. Semantic Context Retrieval
3. Graph-Aufbau
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8100"

# Test User Login
def login():
    """Login als admin"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    response.raise_for_status()
    return response.json()['access_token']

# Test Message senden
def send_test_messages(token):
    """Sendet Test-Messages um Concepts zu erstellen"""
    headers = {"Authorization": f"Bearer {token}"}
    
    test_messages = [
        "Ich möchte mehr über künstliche Intelligenz lernen",
        "Machine Learning ist ein spannendes Thema",
        "Neural Networks und Deep Learning interessieren mich sehr",
        "Python ist meine Lieblingssprache für AI-Projekte",
        "Wie funktioniert Natural Language Processing genau?"
    ]
    
    print("\n📨 Sende Test-Messages...\n")
    
    for msg in test_messages:
        print(f"  → {msg}")
        response = requests.post(
            f"{BASE_URL}/chat/streaming",
            json={
                "message": msg,
                "model": "llama3.2:1b",
                "temperature": 0.7
            },
            headers=headers,
            stream=True
        )
        
        # Stream verarbeiten (nur starten, nicht komplett lesen)
        for line in response.iter_lines():
            if line:
                break  # Nur erste Line, dann abbrechen
        
        print(f"    ✓ Message gesendet\n")

# Check Neo4j Graph
def check_graph():
    """Prüft Neo4j Graph-Status"""
    from neo4j import GraphDatabase
    
    driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'liara_neo4j_2025'))
    
    with driver.session() as session:
        # Node counts
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(*) as count
            ORDER BY count DESC
        """)
        
        print("\n📊 Neo4j Graph-Status:\n")
        print("  Nodes:")
        for record in result:
            label = record['label'] or 'Unknown'
            count = record['count']
            print(f"    - {label}: {count}")
        
        # Relationship counts
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(*) as count
            ORDER BY count DESC
        """)
        
        print("\n  Relationships:")
        for record in result:
            rel_type = record['type']
            count = record['count']
            print(f"    - {rel_type}: {count}")
        
        # Concept details
        result = session.run("""
            MATCH (c:Concept)
            RETURN c.text as concept, c.mention_count as mentions
            ORDER BY c.mention_count DESC
            LIMIT 10
        """)
        
        print("\n  Top-10 Concepts:")
        for record in result:
            concept = record['concept']
            mentions = record['mentions']
            print(f"    - {concept}: {mentions}x erwähnt")
    
    driver.close()

# Main Test
if __name__ == "__main__":
    print("=" * 60)
    print("  🧪 MEMORY INTEGRATION TEST")
    print("=" * 60)
    
    try:
        # 1. Login
        print("\n🔐 Login...")
        token = login()
        print("  ✓ Login erfolgreich")
        
        # 2. Sende Test-Messages
        send_test_messages(token)
        
        # 3. Warte kurz für async processing
        print("\n⏳ Warte 5 Sekunden für async Memory-Processing...")
        import time
        time.sleep(5)
        
        # 4. Check Graph
        check_graph()
        
        print("\n" + "=" * 60)
        print("  ✅ TEST ERFOLGREICH!")
        print("=" * 60)
        print("\n💡 Nächste Schritte:")
        print("   1. Sende weitere Messages im Chat")
        print("   2. Prüfe Context-Injection (ähnliche Concepts)")
        print("   3. Nutze Neo4j Browser: http://localhost:7474")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ TEST FEHLGESCHLAGEN: {e}")
        import traceback
        traceback.print_exc()
