# How to Run CodeDNA

## Quick Start

```bash
cd /Users/pavanc/Projects/codedna

# 1. Install Python package
pip install -e .

# 2. Create test file & add sample data
cat > test.py << 'EOF'
def hello():
    return 42
x0 = 0
x1 = 1
x2 = 2
x3 = 3
x4 = 4
x5 = 5
x6 = 6
x7 = 7
x8 = 8
x9 = 9
x10 = 10
x11 = 11
x12 = 12
x13 = 13
x14 = 14
EOF

python3 -c "
from codedna.classifier import Classifier, EditEvent
from codedna.models import AttributionLabel
from codedna.store import Store
from pathlib import Path
store = Store()
clf = Classifier()
events = [
    EditEvent(Path('test.py'), 1, 5, 'def hello():\n    return 42\n', '', 1000, 500, None),
    EditEvent(Path('test.py'), 6, 20, '\n'.join([f'    x{i} = {i}' for i in range(15)]), '', 2000, 10, 'copilot'),
]
attrs = clf.classify_batch(events)
store.add_batch(attrs)
print('Added', len(attrs), 'attributions')
"

# 3. Run CLI commands
codedna scan . --format summary
codedna ratio test.py
codedna headers test.py --on
codedna verify test.py
```

---

## VS Code Extension

### Install
```bash
# Option 1: If 'code' command is in PATH
code --install-extension /Users/pavanc/Projects/codedna/extension/codedna-0.1.0.vsix

# Option 2: Full path (macOS)
/Applications/Visual\ Studio\ Code.app/Contents/Resources/app/bin/code --install-extension /Users/pavanc/Projects/codedna/extension/codedna-0.1.0.vsix

# Option 3: Manual
# 1. Open VS Code
# 2. Cmd+Shift+P → "Extensions: Install from VSIX"
# 3. Select extension/codedna-0.1.0.vsix
```

### Usage
- Open any workspace
- Status bar (bottom right) shows live H/AI ratio
- Gutter decorations: 🟢 Human, 🔵 AI-generated, 🟠 AI-modified, 🟣 Ambiguous
- Commands (`Cmd+Shift+P`):
  - `CodeDNA: Show Attribution Report` (also `Cmd+Shift+C`)
  - `CodeDNA: Show H/AI Ratio`
  - `CodeDNA: Toggle Provenance Headers`
  - `CodeDNA: Open Settings`

---

## IPC Server (for extension)

```bash
# Basic
codedna server

# With LLM classifier (requires API key)
export CODEDNA_API_KEY="sk-ant-..."  # Anthropic
# or
export OPENAI_API_KEY="sk-..."       # OpenAI
codedna server --llm
```

---

## Web Dashboard

### Terminal 1: Backend API
```bash
cd /Users/pavanc/Projects/codedna/dashboard/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8081 --reload
```

### Terminal 2: Frontend
```bash
cd /Users/pavanc/Projects/codedna/dashboard/frontend
npm run dev
# Open http://localhost:5173 (proxies to :8081)
```

### Production Build
```bash
cd /Users/pavanc/Projects/codedna/dashboard/frontend
npm run build  # Outputs to dist/
```

---

## Running Tests

```bash
# Core Python tests
cd /Users/pavanc/Projects/codedna
python3 -m pytest core/tests/ -v

# Extension
cd /Users/pavanc/Projects/codedna/extension
npm run compile
npm run package

# Dashboard frontend
cd /Users/pavanc/Projects/codedna/dashboard/frontend
npm run build

# Evaluation script
cd /Users/pavanc/Projects/codedna
python3 evals/retry_eval.py
```

---

## CI / GitHub Actions

The workflow at `.github/workflows/ci.yml` runs on every push:
- Core tests (Python)
- Extension compile + lint + package
- Dashboard frontend build
- AI-ratio gate (fails if AI > 30%)

---

## Configuration

### VS Code Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `codedna.enabled` | `true` | Enable tracking |
| `codedna.pythonPath` | `python` | Python interpreter path |
| `codedna.showStatusBar` | `true` | Show H/AI ratio in status bar |
| `codedna.showGutterDecorations` | `true` | Show gutter colors |
| `codedna.autoWriteHeaders` | `false` | Write headers on save |

### Environment Variables
| Variable | Purpose |
|----------|---------|
| `CODEDNA_API_KEY` | Anthropic API key for LLM classifier |
| `OPENAI_API_KEY` | OpenAI API key for LLM classifier |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `code: command not found` | Install shell command: VS Code → Cmd+Shift+P → "Shell Command: Install 'code' command in PATH" |
| `NotImplementedError` on server shutdown | Known issue with `writer.wait_closed()` — works fine, just Ctrl+C to exit |
| `headers: file does not exist` | File must exist on disk — create it first |
| Extension not tracking | Check `codedna.enabled` setting, ensure `codedna server` is running |

---

## Project Structure

```
/Users/pavanc/Projects/codedna/
├── core/                    # Python package (codedna-core)
│   ├── src/codedna/         # Source modules
│   └── tests/               # Unit tests
├── extension/               # VS Code extension (TypeScript)
│   ├── src/                 # Extension source
│   └── out/                 # Compiled JS
├── dashboard/
│   ├── backend/             # FastAPI server
│   └── frontend/            # React + Vite
├── evals/                   # Evaluation scripts
├── .github/workflows/ci.yml # CI pipeline
├── pyproject.toml           # Python package config
├── README.md                # Documentation
├── LICENSE                  # MIT license
└── RUN.md                   # This file
```

---

## License

MIT © CodeDNA Contributors