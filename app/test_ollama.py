"""Test script for Liara Ollama integration."""
import sys
sys.path.insert(0, '/opt/liara/app')

from liara_engine.nlp.ollama_client import get_liara_client, ask_liara, ModelType
from liara_engine.nlp.model_router import ModelRouter

def test_connection():
    """Test Ollama connection."""
    print("🔌 Testing Ollama connection...")
    client = get_liara_client()
    
    if client.is_available():
        print("✅ Ollama is available!")
        models = client.list_models()
        print(f"✅ Found {len(models)} models installed")
        return True
    else:
        print("❌ Ollama is not available!")
        return False

def test_models():
    """Test different models."""
    print("\n🧪 Testing different models...\n")
    
    tests = [
        {
            "model_type": ModelType.INTENT,
            "message": "Zeig mir meine Aufgaben",
            "description": "Intent Recognition (llama3.2:1b)"
        },
        {
            "model_type": ModelType.CONVERSATION,
            "message": "Hallo Liara, wie geht's?",
            "description": "Conversation (llama3.2:3b)"
        },
        {
            "model_type": ModelType.CODE,
            "message": "Schreibe eine Python Funktion zum Addieren zweier Zahlen",
            "description": "Code Generation (phi3:mini)"
        }
    ]
    
    for test in tests:
        print(f"📝 {test['description']}")
        print(f"   Input: {test['message']}")
        
        response = ask_liara(
            message=test['message'],
            model_type=test['model_type']
        )
        
        print(f"   Output: {response[:100]}...")
        print()

def test_model_router():
    """Test automatic model selection."""
    print("\n🎯 Testing Model Router...\n")
    
    test_messages = [
        "Schreibe Python Code für FastAPI",
        "Was liegt heute an?",
        "Warum ist der Himmel blau?",
        "Übersetze Hello auf Deutsch"
    ]
    
    for msg in test_messages:
        model = ModelRouter.get_best_model(msg)
        print(f"Message: {msg}")
        print(f"→ Selected Model: {model}\n")

def main():
    """Run all tests."""
    print("=" * 60)
    print("🌙 LIARA OLLAMA INTEGRATION TEST")
    print("=" * 60)
    
    if not test_connection():
        print("\n❌ Cannot continue without Ollama connection")
        return
    
    test_models()
    test_model_router()
    
    print("=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
