# 🏺 Git Archaeologist

**AI-powered code archaeology — dig through your repository's history to answer questions no one else can.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Why Git Archaeologist?

Every codebase has a story — buried in commit messages, scattered across branches, and locked inside the minds of people who left the team years ago. **Git Archaeologist** uses large language models to excavate that story, so you can stop guessing and start *knowing*.

---

## ✨ Features

### 🔍 Ask Questions About Code
Point Git Archaeologist at any file, function, or module and ask natural-language questions:

> *"Why was the retry logic added to `payment_gateway.py`?"*
> *"What was the original design intent behind the caching layer?"*

It cross-references commit history, diffs, and commit messages to synthesize a clear, sourced answer.

### 👤 Find Domain Experts
Need to understand the billing system? Git Archaeologist analyzes commit ownership, review patterns, and code churn to identify the people who know each part of the codebase best — ranked by expertise and recency.

### 💥 Track Refactor Impact
Before you rename a core abstraction or restructure a package, see what the ripple effects look like. Git Archaeologist maps dependency and change-propagation patterns to estimate the blast radius of proposed refactors.

### 📊 Analyze PR Patterns
Surface insights from pull request history:

- **Review bottlenecks** — who's drowning in review requests?
- **Merge velocity trends** — is the team slowing down?
- **Hotspot detection** — which files are changed most frequently, by whom, and why?
- **Cross-team coupling** — where do different teams' changes collide?

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/git-archaeologist.git
cd git-archaeologist

# Install with pip
pip install -e .
```

### Configuration

Set your LLM provider credentials:

```bash
# OpenAI (default)
export GIT_ARCH_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# Or use any OpenAI-compatible endpoint
export GIT_ARCH_LLM_BASE_URL=https://your-endpoint/v1
export GIT_ARCH_LLM_MODEL=gpt-4o
```

### Run

```bash
# Interactive Q&A on the current repo
git-archaeologist ask "Why was the rate limiter introduced in the API module?"

# Identify domain experts for a path
git-archaeologist experts src/payments/

# Analyze refactor blast radius
git-archaeologist impact src/models/user.py

# PR pattern analysis
git-archaeologist pr-stats --since 2025-01-01
```

---

## 🧱 Architecture

```
┌─────────────────────────────────────────────────┐
│                  CLI / API Layer                 │
├─────────────┬──────────────┬────────────────────┤
│  Ask Engine │ Expert Finder│ Impact & PR Analyzer│
├─────────────┴──────────────┴────────────────────┤
│              Git History Mining (gitpython)      │
├─────────────────────────────────────────────────┤
│              LLM Synthesis & Embeddings          │
├─────────────────────────────────────────────────┤
│              Repository Index (SQLite / in-mem)  │
└─────────────────────────────────────────────────┘
```

| Layer | Responsibility |
|---|---|
| **CLI / API** | User-facing interface (CLI + optional REST API) |
| **Ask Engine** | Retrieves relevant history, feeds context to LLM, returns sourced answers |
| **Expert Finder** | Computes ownership & expertise scores from commit and review data |
| **Impact Analyzer** | Builds change-propagation graphs from historical co-change patterns |
| **PR Analyzer** | Aggregates and surfaces pull request metrics and trends |
| **Git Mining** | Efficient git history traversal via `gitpython` with caching |
| **LLM Layer** | Pluggable — supports OpenAI, Anthropic, local models via LiteLLM |
| **Index** | Optional SQLite cache for large repos to avoid re-scanning |

---

## 📖 Usage Examples

### Interactive Mode

```bash
git-archaeologist repl
```

```
🏺 Git Archaeologist REPL — ask anything about this codebase
   Type 'exit' to quit.

> Who knows the most about the authentication subsystem?
Based on the last 24 months of commits, the top contributors to
src/auth/ are:
  1. Alice Chen — 47 commits, last active 3 weeks ago
  2. Bob Martinez — 31 commits, last active 2 months ago
  ...

> Why did we switch from Redis to Memcached for session storage?
The switch was introduced in PR #1842 (merged 2025-08-14) by Carol Wu.
The commit message cites "reduced operational complexity and cost at our
current scale." The preceding incident (INC-3401) involved Redis memory
pressure during peak traffic...
```

### Programmatic API

```python
from git_archaeologist import GitArchaeologist

arch = GitArchaeologist(repo_path=".")

# Ask a question
answer = arch.ask("Why was the circuit breaker pattern added?")
print(answer.text)
print(answer.sources)  # list of commits, PRs, and files cited

# Find experts
experts = arch.find_experts("src/billing/", top_n=5)
for e in experts:
    print(f"{e.name}: {e.score:.2f} ({e.commit_count} commits)")

# Refactor impact
impact = arch.estimate_impact("src/models/user.py")
print(f"Estimated affected files: {len(impact.affected_files)}")
print(f"Risk level: {impact.risk_level}")
```

---

## ⚙️ Configuration

Create a `git-archaeologist.toml` in your repo root or `~/.config/git-archaeologist/config.toml`:

```toml
[llm]
provider = "openai"          # openai | anthropic | local
model = "gpt-4o"
max_context_tokens = 128000
temperature = 0.2

[analysis]
# How far back to look (default: full history)
max_history_months = 36
# Enable SQLite index for repos > 10k commits
cache_backend = "sqlite"
# Ignore patterns (globs)
ignore_paths = ["vendor/*", "node_modules/*", "*.lock"]

[experts]
# Decay factor for recency (0 = no decay, 1 = aggressive)
recency_decay = 0.3
# Minimum commits to qualify
min_commits = 5

[pr_analysis]
# Default time window
default_since = "6 months ago"
```

---

## 🧪 Development

```bash
# Clone and set up
git clone https://github.com/your-org/git-archaeologist.git
cd git-archaeologist
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=git_archaeologist --cov-report=term-missing

# Lint & format
ruff check .
ruff format .
```

### Project Structure

```
git-archaeologist/
├── src/git_archaeologist/
│   ├── __init__.py
│   ├── cli.py              # CLI entry points
│   ├── config.py           # Configuration loading
│   ├── ask.py              # Question-answering engine
│   ├── experts.py          # Domain expert finder
│   ├── impact.py           # Refactor impact analysis
│   ├── pr_analysis.py      # PR pattern analysis
│   ├── git_mining.py       # gitpython-based history extraction
│   ├── llm.py              # LLM abstraction layer
│   └── cache.py            # SQLite caching backend
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [gitpython](https://github.com/gitpython-developers/GitPython) — robust git repository interaction in Python
- [LiteLLM](https://github.com/BerriAI/litellm) — unified LLM provider interface
- The concept of *code archaeology* — understanding software by studying its history, not just its present

---

<p align="center">
  <em>Every commit tells a story. Git Archaeologist helps you read them all.</em>
</p>