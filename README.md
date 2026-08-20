# 🌙 Liara - Privacy-First AI Assistant

<div align="center">

![Version](https://img.shields.io/badge/version-2.7.2-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-00C7B7.svg)
![React](https://img.shields.io/badge/React-19.2+-61DAFB.svg)

**A self-hosted, privacy-first AI personal assistant with 4D memory, web search, and UNSC-inspired design**

[Features](#-features) • [Installation](#-installation) • [Architecture](#-architecture) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🎯 Overview

Liara is a comprehensive AI assistant platform built for privacy-conscious users who want complete control over their data. With multi-model AI support, semantic memory, and a stunning Halo/UNSC-inspired interface, Liara brings enterprise-grade AI capabilities to your personal infrastructure.

### ✨ Key Highlights

- 🤖 **Multi-Model AI** - Support for 8+ Ollama models (llama3.2, qwen2.5, deepseek, etc.)
- 🧠 **4D Memory System** - Semantic search with Neo4j graphs + PostgreSQL + Redis
- 🔒 **Privacy-First** - Self-hosted, no cloud, GDPR-compliant
- 🌐 **Web Search** - DuckDuckGo, Wikipedia, Weather, News integration
- 💬 **Guest Mode** - Chat without registration (streaming SSE)
- 📱 **Mobile-First** - Touch-optimized responsive design (44px+ targets)
- 🎨 **UNSC Design** - Glassmorphism, cyan glows, command console aesthetic
- 🔧 **Admin Panel** - Full system management, user control, monitoring

---

## 🚀 Features

See [FEATURES.md](./FEATURES.md) for complete feature list.

### Core AI Capabilities

- **Streaming SSE** - Real-time responses via Server-Sent Events
- **Context-Aware** - 20-message sliding window with semantic recall
- **Intent Detection** - Automatic command recognition (tasks, events, notes, search)
- **Multi-User** - Full user isolation with role-based access (Admin/User/Guest)

### 4D Memory System
- 📊 **Semantic Memory** - 384-dim embeddings (sentence-transformers)
- 🔗 **Graph Relations** - Neo4j relationship tracking
- ⏰ **Temporal Index** - PostgreSQL time-series data
- 💾 **Session Context** - Redis 20-message window

### Productivity Features
- ✅ **Tasks** - Things/Todoist-style task management
- 📅 **Calendar** - Month/Week/Day views with natural language creation
- 📝 **Notes** - Tree-structured knowledge base with auto-categorization

### Mobile-First Design (v2.7.2+)
- 📱 44px+ Touch Targets (iOS/Android compliant)
- 🖱️ Responsive layouts (480px/768px/1024px breakpoints)
- 💬 Sticky chat input, overlay sidebar
- 🌓 Dark/Light mode with 40+ CSS variables

---

## 🛠️ Tech Stack

**Backend**: FastAPI, Python 3.11+, PostgreSQL (pgvector), Neo4j, Redis, Ollama  
**Frontend**: React 19.2+, Vite 7.2, xterm.js, react-markdown  
**Infrastructure**: Nginx, systemd, Docker (optional)

---

## 📦 Installation

### Prerequisites

```bash
# System Requirements
- Ubuntu 22.04+ / Debian 12+
- 8GB RAM minimum (16GB recommended)
- 50GB disk space
- Python 3.11+, Node.js 20+
- PostgreSQL 15+, Neo4j 5.x, Redis 7.x, Ollama 0.1.x
```

### Quick Start

```bash
# 1. Clone
git clone https://github.com/yourusername/liara.git
cd liara

# 2. Backend
cd app
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
python init_db.py

# 3. Frontend
cd ../frontend
npm install
npm run build
sudo cp -r dist/* /var/www/liara/

# 4. Configure services (PostgreSQL, Neo4j, Redis, Ollama)
# See DEPLOYMENT_GUIDE_v2.7.0.md for details

# 5. Start
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Docker**: `docker-compose up -d`

See [DEPLOYMENT_GUIDE_v2.7.0.md](./DEPLOYMENT_GUIDE_v2.7.0.md) for detailed instructions.

---

## 🏗️ Architecture

```
┌───────────────────────────────────────────┐
│         Nginx (Port 80)                   │
│         Reverse Proxy & SSL               │
└───────────┬─────────────────┬─────────────┘
            │                 │
            ▼                 ▼
    ┌──────────────┐  ┌──────────────────┐
    │  React       │  │  FastAPI         │
    │  Frontend    │  │  Backend         │
    └──────────────┘  └─────────┬────────┘
                                │
            ┌───────────────────┼────────────┐
            ▼                   ▼            ▼
    ┌──────────────┐  ┌──────────────┐  ┌────────┐
    │ PostgreSQL   │  │ Neo4j        │  │ Redis  │
    │ + pgvector   │  │ Graph DB     │  │ Cache  │
    └──────────────┘  └──────────────┘  └────────┘
            │
            ▼
    ┌─────────────────────────────────────┐
    │     Ollama AI Runtime               │
    │  llama3.2, qwen2.5, deepseek, etc.  │
    └─────────────────────────────────────┘
```

---

## 📚 Documentation

### Main Docs
- [FEATURES.md](./FEATURES.md) - Complete feature list
- [DEPLOYMENT_GUIDE_v2.7.0.md](./DEPLOYMENT_GUIDE_v2.7.0.md) - Deployment instructions
- [CHANGELOG.md](./CHANGELOG.md) - Version history

### Technical Docs
- [4D_MEMORY_SYSTEM.md](./docs/4D_MEMORY_SYSTEM.md) - Memory architecture
- [API.md](./docs/API.md) - API documentation
- [NLP_SYSTEM.md](./docs/NLP_SYSTEM.md) - Intent detection & NLP
- [TERMINAL_PTY_v3.0.md](./docs/TERMINAL_PTY_v3.0.md) - Terminal system

### Design Docs
- [DESIGN_SYSTEM.md](./docs/DESIGN_SYSTEM.md) - Design guidelines
- [RESPONSIVE_DESIGN_v2.7.2.md](./RESPONSIVE_DESIGN_v2.7.2.md) - Mobile-first design
- [THEME_SYSTEM.md](./docs/THEME_SYSTEM.md) - Dark/Light mode

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/yourusername/liara.git
cd liara && cd app
python -m venv ../venv && source ../venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Code Style**: Python (Black, flake8), JavaScript (ESLint), CSS (BEM, CSS variables)

---

## 📄 License

MIT License - see [LICENSE](./LICENSE)

---

## 🙏 Acknowledgments

Ollama • FastAPI • React • Neo4j • PostgreSQL • Halo/UNSC Design Inspiration

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/liara/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/liara/discussions)

---

## 🗺️ Roadmap

### v3.0 (Planned)
- Voice I/O with Whisper
- Image generation (Stable Diffusion)
- Plugin system
- Mobile apps (iOS/Android)
- Multi-language support

### v2.8 (Next)
- PWA support (offline mode)
- Push notifications
- Swipe gestures

See [ROADMAP_V3.md](./docs/ROADMAP_V3.md) for details.

---

<div align="center">

**Built with ❤️ for privacy-conscious users**

[⬆ Back to Top](#-liara---privacy-first-ai-assistant)

</div>
