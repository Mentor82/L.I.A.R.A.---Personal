# AI Transparency Statement

**LIARA - Digital Companion**  
**Version:** 3.0.0  
**Last Updated:** December 6, 2025  
**Compliance:** EU AI Act (Minimal Risk Classification)

---

## ⚠️ Important Notice: This is an AI System

**LIARA is an Artificial Intelligence System.** All responses, suggestions, and generated content are produced by machine learning algorithms, not by human intelligence.

---

## 🤖 What is LIARA?

LIARA (Learning, Intuitive, Adaptive, Responsive Assistant) is an **open-source AI companion** that uses:
- **Large Language Models (LLMs)** for conversational AI
- **Embedding Models** for semantic understanding
- **Sentiment Analysis** for emotional context
- **Image Generation** (optional, if Stable Diffusion enabled)

### Key Characteristics:
- ✅ **100% Local Processing** - All AI runs on your server
- ✅ **No Cloud Dependencies** - No data sent to OpenAI, Google, etc.
- ✅ **Open Source** - Fully auditable code
- ✅ **Privacy-First** - No tracking, no data sales

---

## 🧠 How LIARA Works

### 1. Large Language Models (LLMs)

**Technology:** Ollama (local inference engine)  
**Models Used:** Mistral, Llama, Qwen, Phi, Gemma, etc. (user-selectable)

**How it works:**
1. You send a message to LIARA
2. The message is processed through a transformer-based neural network
3. The model predicts the most likely next words based on:
   - Training data (general knowledge from internet text)
   - Conversation context (your previous messages)
   - System prompts (LIARA's personality and guidelines)
4. The response is generated token-by-token (word-by-word)

**Limitations:**
- ❌ May produce factually incorrect information ("hallucinations")
- ❌ Limited by training data cutoff (typically 2023 or earlier)
- ❌ Cannot access real-time internet data (unless web search enabled)
- ❌ May reflect biases present in training data

**Explainability:**
- Responses are **probabilistic** - the model chooses the most likely continuation
- No single "reason" for a specific response - it's based on statistical patterns
- You can ask "Why did you say that?" and LIARA will explain its reasoning

### 2. Semantic Memory (Embeddings)

**Technology:** sentence-transformers (all-MiniLM-L6-v2 or similar)

**How it works:**
1. Your conversations are converted to **768-dimensional vectors** (embeddings)
2. These vectors capture semantic meaning (not just keywords)
3. LIARA stores these in a **Neo4j graph database**
4. When you ask something, LIARA finds similar past conversations using **cosine similarity**

**What this means:**
- LIARA "remembers" context from previous chats
- It can find related information even if different words are used
- Example: "Tell me about my trip to Paris" → finds memories with "vacation," "France," "travel"

**Limitations:**
- Memory is **associative**, not perfect recall
- May retrieve irrelevant memories if embeddings are similar
- **Consent required** - this feature must be explicitly enabled

### 3. Sentiment Analysis

**Technology:** transformers (DistilBERT or similar)

**How it works:**
1. Each message is analyzed for emotional tone
2. Classification into: Positive, Negative, Neutral
3. Confidence score (e.g., 85% positive)
4. Stored as mood data for tracking over time

**What this means:**
- LIARA can detect if you're happy, sad, frustrated, etc.
- It adapts responses to your emotional state
- You can view mood trends over time

**Limitations:**
- Not perfect - may misclassify sarcasm or complex emotions
- Based on text only - cannot see facial expressions or hear tone
- **Consent required** - must be explicitly enabled

### 4. Image Generation (Optional)

**Technology:** Stable Diffusion (local model)

**How it works:**
1. You provide a text prompt (e.g., "a sunset over mountains")
2. The prompt is encoded into embeddings
3. A diffusion model iteratively denoises random noise into an image
4. The result matches the semantic meaning of your prompt

**Limitations:**
- May produce unexpected or distorted results
- Cannot guarantee specific details (e.g., exact number of fingers)
- Requires significant GPU resources
- **Optional** - must be enabled in configuration

---

## 🎯 EU AI Act Compliance

### Risk Classification: **Minimal Risk**

LIARA is classified as a **minimal risk AI system** because it:
- ✅ Does NOT make high-risk decisions (no credit scoring, employment, law enforcement)
- ✅ Does NOT use biometric identification
- ✅ Does NOT target vulnerable groups (children, disabled persons)
- ✅ Does NOT use manipulative techniques

### Transparency Requirements Met:

#### ✅ AI System Disclosure
- LIARA clearly identifies itself as an AI
- No impersonation of humans
- Explicit labeling on all pages

#### ✅ AI-Generated Content Labeling
- All responses marked as "AI-Generated"
- Footer on chat interface: "💬 AI-Generated Response"
- Image watermarks (if Stable Diffusion enabled)

#### ✅ Explainability
- This document explains how LIARA works
- Users can ask for reasoning behind responses
- Model information visible in Settings

#### ✅ No Manipulation
- No dark patterns
- No emotional exploitation
- No subliminal messaging
- Clear opt-in/opt-out for all features

#### ✅ Human Oversight
- You control all aspects of LIARA
- Can disable any feature
- Can delete all data
- Self-hosted = full control

---

## 🚫 What LIARA Does NOT Do

### Prohibited Uses:

❌ **LIARA MUST NOT be used for:**
- High-risk decision-making (credit scoring, hiring, legal judgments)
- Biometric identification or surveillance
- Social scoring or profiling
- Critical infrastructure control without human oversight
- Medical diagnosis without professional consultation
- Legal advice (not a substitute for a lawyer)

### Ethical Boundaries:

LIARA will refuse to:
- Generate harmful, illegal, or dangerous content
- Impersonate real people without disclosure
- Provide medical advice beyond general information
- Make decisions that require human judgment (e.g., "Should I divorce my spouse?")

---

## 🔍 How to Verify AI Transparency

### 1. Check the Model

Go to **Settings > System Config > Model Configuration**:
- See which LLM is currently active (e.g., `mistral:latest`)
- View model parameters (temperature, context length)
- Switch to different models

### 2. Inspect Embeddings

Go to **Memory View** (if semantic memory enabled):
- See all stored memory nodes
- View embedding vectors (768 numbers)
- Understand similarity scores

### 3. View Sentiment Data

Go to **Mood Tracking** (if sentiment enabled):
- See sentiment classifications over time
- View confidence scores
- Export data as CSV

### 4. Audit Logs

Go to **Settings > Privacy Settings > Export Data**:
- Download all your data as JSON
- Includes: chats, memories, sentiment, timestamps
- Fully machine-readable

---

## 📊 Performance Metrics

### Accuracy Expectations:

| Task | Typical Accuracy | Notes |
|------|------------------|-------|
| **Conversational Responses** | 70-90% helpful | Depends on model size and prompt quality |
| **Factual Recall** | 60-80% accurate | May hallucinate facts - verify critical info |
| **Sentiment Analysis** | 75-85% accurate | Struggles with sarcasm and nuance |
| **Semantic Memory** | 80-95% relevant | Retrieval quality depends on embedding model |
| **Image Generation** | Varies widely | Highly subjective, depends on prompt |

### Limitations:

- **Training Cutoff**: LLMs don't know events after ~2023
- **No Internet Access**: Cannot browse web (unless web search enabled)
- **Context Window**: Limited memory within a single chat (typically 4K-32K tokens)
- **Bias**: May reflect biases in training data (gender, cultural, political)

---

## 🛡️ Safety Measures

### Content Filtering

LIARA uses:
- ✅ **Input filtering**: Blocks obviously harmful prompts
- ✅ **Output filtering**: Prevents generation of dangerous content
- ✅ **User reporting**: Report problematic responses (if multi-user setup)

### Privacy Safeguards

- ✅ **Local processing**: No data leaves your server
- ✅ **Encryption**: HTTPS/TLS for all connections
- ✅ **Hashed passwords**: bcrypt with salt
- ✅ **Session management**: JWT tokens, 1-hour expiry

### Data Minimization

- ✅ **Opt-in features**: Memory, sentiment, location all require consent
- ✅ **Auto-delete**: Configurable retention (7-365 days)
- ✅ **No third-party sharing**: Zero data sales or sharing

---

## 🌍 Responsible AI Principles

LIARA adheres to:

1. **Transparency**: Clear disclosure of AI nature and capabilities
2. **Fairness**: No intentional discrimination or bias
3. **Privacy**: User data never leaves their control
4. **Accountability**: Operators are responsible for their use of LIARA
5. **Safety**: Content filtering and ethical boundaries
6. **Human Control**: Users can override, disable, or delete anything

---

## 📋 For Developers: Technical Details

### Model Architecture

**LLM Stack:**
```
User Input → Tokenization → Transformer Layers (12-80) → Softmax → Token Generation
```

**Embedding Stack:**
```
Text → Tokenization → BERT-like Encoder → Mean Pooling → L2 Normalization → 768D Vector
```

**Sentiment Stack:**
```
Text → Tokenization → DistilBERT → Classification Head → Softmax → [Positive, Negative, Neutral]
```

### Training Data Sources

**LLMs (Ollama models):**
- Common Crawl (web scrapes)
- Wikipedia
- Books (e.g., BookCorpus)
- GitHub code (for code-capable models)
- Academic papers (ArXiv, PubMed)

**Embedding Models:**
- SentenceBERT datasets
- Paraphrase mining datasets
- Question-answer pairs

**Sentiment Models:**
- IMDb reviews
- Twitter sentiment datasets
- Product reviews

### Inference Configuration

**Default Settings:**
```python
{
  "temperature": 0.7,        # Creativity vs determinism
  "top_p": 0.9,              # Nucleus sampling
  "max_tokens": 2048,        # Maximum response length
  "context_window": 4096,    # How much chat history to include
  "stream": true             # Token-by-token streaming
}
```

---

## 🆘 Reporting Issues

### If LIARA Produces Harmful Content:

1. **Stop using the feature** that produced it
2. **Screenshot the conversation** (for documentation)
3. **Report via GitHub Issues**: [Your GitHub URL]
4. **Adjust content filter settings** in System Config

### If You Notice Bias:

1. **Document the bias** (save examples)
2. **Report via GitHub Discussions**
3. **Consider switching models** (different LLMs have different biases)

### For Safety Concerns:

If LIARA is being used in a way that could cause harm:
- **Report to instance operator** (if not you)
- **Disable dangerous features** (e.g., internet access, image generation)
- **Review system logs** for unauthorized access

---

## 📞 Contact for AI Ethics Concerns

**LIARA Open Source Project:**  
GitHub: https://github.com/[your-repo]  
AI Ethics Discussions: https://github.com/[your-repo]/discussions/categories/ai-ethics

**Your Instance Operator:**  
[Operator Name]  
[Operator Email]

---

## 📜 Legal Notice

**This is a minimal risk AI system under the EU AI Act.**

**Operator Responsibilities:**
- Ensure LIARA is not used for prohibited purposes
- Provide users with this transparency statement
- Maintain human oversight for critical decisions
- Comply with applicable AI regulations

**User Responsibilities:**
- Understand that LIARA is an AI, not a human
- Verify critical information independently
- Do not rely on LIARA for high-risk decisions
- Report problematic behavior

---

**Version:** 3.0.0  
**Last Updated:** December 6, 2025  
**Compliance:** EU AI Act (Title III, Chapter 2 - Minimal Risk Systems)
