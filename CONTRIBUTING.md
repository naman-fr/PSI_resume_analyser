# Contributing to PSI Candidate Intelligence Platform

First off, thank you for considering contributing to this enterprise open-source project! 

## 🚀 How to Contribute

### 1. Fork & Clone
Fork the repository on GitHub and clone it locally.
```bash
git clone https://github.com/YOUR_USERNAME/PSI_resume_analyser.git
cd PSI_resume_analyser
```

### 2. Create a Branch
Create a new branch for your feature or bugfix.
```bash
git checkout -b feature/amazing-ai-feature
```

### 3. Make Changes
Ensure your code adheres to our architecture (decoupled planes, LangGraph state management).
Run `ruff check .` to verify linting.

### 4. Run Tests
Ensure all FastAPI endpoints and LangGraph nodes pass existing tests.
```bash
pytest
```

### 5. Commit & Push
Follow conventional commits (e.g., `feat: added neo4j support`, `fix: resolved webRTC memory leak`).
```bash
git commit -m "feat: your amazing feature"
git push origin feature/amazing-ai-feature
```

### 6. Submit a Pull Request
Go to the original repository and open a Pull Request. Use the provided PR template to explain your architectural changes.
