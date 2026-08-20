# Contributing to Liara

Thank you for considering contributing to Liara! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

---

## 🤝 Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity, experience level, nationality, personal appearance, race, religion, or sexual identity.

### Our Standards

**Positive behavior**:
- Using welcoming and inclusive language
- Respecting differing viewpoints
- Accepting constructive criticism
- Focusing on what's best for the community

**Unacceptable behavior**:
- Harassment, trolling, or insulting comments
- Personal or political attacks
- Public or private harassment
- Publishing others' private information

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Neo4j 5.x
- Redis 7.x
- Ollama 0.1.x
- Git

### Fork the Repository

```bash
# 1. Fork on GitHub (click Fork button)

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/liara.git
cd liara

# 3. Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/liara.git

# 4. Verify remotes
git remote -v
```

---

## 💻 Development Setup

### Backend

```bash
cd app
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt

# Install dev dependencies
pip install black flake8 pytest pytest-asyncio

# Init database
python init_db.py

# Run backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Run dev server
npm run dev

# Build for production
npm run build
```

### Configure Services

```bash
# PostgreSQL
sudo -u postgres psql
CREATE DATABASE liara_dev;
CREATE EXTENSION vector;

# Neo4j (use different port for dev)
# Edit /etc/neo4j/neo4j.conf
dbms.connector.bolt.listen_address=:7688

# Redis (use DB 1 for dev)
redis-cli SELECT 1

# Ollama
ollama serve
```

---

## 🛠️ How to Contribute

### Types of Contributions

1. **Bug Fixes** - Fix reported issues
2. **Features** - Add new functionality
3. **Documentation** - Improve docs, add examples
4. **Tests** - Add or improve test coverage
5. **Performance** - Optimize code, reduce latency
6. **Design** - UI/UX improvements

### Finding Issues

- Check [GitHub Issues](https://github.com/yourusername/liara/issues)
- Look for `good first issue` or `help wanted` labels
- Ask in [Discussions](https://github.com/yourusername/liara/discussions)

### Reporting Bugs

**Template**:
```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Screenshots
If applicable

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.11.5]
- Liara Version: [e.g., 2.7.2]
```

### Suggesting Features

**Template**:
```markdown
## Feature Description
Clear description of the feature

## Use Case
Why is this needed?

## Proposed Solution
How would it work?

## Alternatives Considered
Other approaches you've thought of
```

---

## 🎨 Code Style

### Python

- **Formatter**: Black (line length 88)
- **Linter**: flake8
- **Type Hints**: Encouraged
- **Docstrings**: Google style

```python
# Good example
from typing import List, Optional

def process_messages(
    messages: List[str],
    user_id: int,
    max_tokens: Optional[int] = None
) -> dict:
    """
    Process chat messages for a user.

    Args:
        messages: List of message strings
        user_id: User ID for context
        max_tokens: Optional token limit

    Returns:
        dict: Processed result with metadata

    Raises:
        ValueError: If messages list is empty
    """
    if not messages:
        raise ValueError("Messages cannot be empty")
    
    # Implementation
    return {"status": "success"}
```

**Run formatters**:
```bash
black app/
flake8 app/
```

### JavaScript/React

- **Formatter**: ESLint + Prettier
- **Style**: Functional components, hooks
- **Naming**: camelCase for variables, PascalCase for components

```javascript
// Good example
import { useState, useEffect } from 'react';

export default function ChatMessage({ message, timestamp }) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  return (
    <div className={`message ${isVisible ? 'visible' : ''}`}>
      <p>{message}</p>
      <span className="timestamp">{timestamp}</span>
    </div>
  );
}
```

**Run linter**:
```bash
npm run lint
npm run lint:fix
```

### CSS

- **Methodology**: BEM (Block__Element--Modifier)
- **Variables**: Use CSS custom properties
- **Mobile-First**: Design for mobile, enhance for desktop

```css
/* Good example */
.chat-message {
  padding: var(--mobile-padding);
  background: var(--color-bg-alt);
}

.chat-message__content {
  font-size: var(--mobile-text-base);
}

.chat-message--sent {
  align-self: flex-end;
}

@media (min-width: 768px) {
  .chat-message {
    padding: var(--space-lg);
  }
}
```

---

## 🧪 Testing

### Backend Tests

```bash
cd app
pytest tests/ -v

# With coverage
pytest --cov=app tests/

# Specific test
pytest tests/test_chat.py::test_stream_response
```

### Frontend Tests

```bash
cd frontend
npm run test

# With coverage
npm run test:coverage
```

### Manual Testing Checklist

- [ ] Chat streaming works
- [ ] Intent detection accurate
- [ ] Tasks CRUD operations
- [ ] Calendar events creation
- [ ] Notes tree navigation
- [ ] Mobile responsive (480px, 768px, 1024px)
- [ ] Dark/Light mode switch
- [ ] Admin panel accessible (admin role)
- [ ] Guest mode rate limiting

---

## 🔄 Pull Request Process

### 1. Create a Branch

```bash
git checkout -b feature/amazing-feature
# or
git checkout -b fix/bug-description
```

**Branch naming**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Test additions
- `chore/` - Maintenance tasks

### 2. Make Changes

- Write clean, documented code
- Follow code style guidelines
- Add tests for new features
- Update documentation

### 3. Commit

```bash
git add .
git commit -m "feat: add semantic search to notes"
```

**Commit message format** (Conventional Commits):
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

**Examples**:
```
feat(chat): add streaming SSE support
fix(auth): correct JWT expiration validation
docs(api): update endpoint documentation
style(css): apply mobile-first utilities
refactor(memory): optimize semantic search queries
test(chat): add integration tests for SSE
chore(deps): update React to 19.2.0
```

### 4. Push

```bash
git push origin feature/amazing-feature
```

### 5. Open Pull Request

- Go to GitHub and open a PR
- Fill out the PR template
- Link related issues (Fixes #123)
- Request review

**PR Template**:
```markdown
## Description
Clear description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Manual testing done
- [ ] Unit tests added
- [ ] Integration tests added

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests pass locally

## Screenshots
If applicable
```

### 6. Code Review

- Address reviewer comments
- Make requested changes
- Update PR description if needed

### 7. Merge

- Squash commits if needed
- Merge when approved
- Delete branch after merge

---

## 🌐 Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, general discussion
- **Pull Requests**: Code contributions

### Getting Help

1. Search existing issues/discussions
2. Check documentation
3. Ask in Discussions (don't open issues for questions)
4. Be respectful and patient

### Recognition

Contributors are recognized in:
- `CHANGELOG.md` - Major contributions
- GitHub Contributors page
- Release notes

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## ❓ Questions?

If you have questions about contributing, feel free to:
- Open a Discussion on GitHub
- Check existing documentation
- Reach out to maintainers

**Thank you for contributing to Liara! 🌙**
