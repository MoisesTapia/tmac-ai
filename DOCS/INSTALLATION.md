# Installation

## Requirements

- **Python 3.10+**
- *(Optional)* [Graphviz](https://graphviz.org/) — required only to render diagrams as images (`png`, `svg`, `pdf`).

---

## Option 1 — PyPI (recommended)

```bash
pip install tmac
tmac --version
```

## Option 2 — Poetry (development)

```bash
git clone https://github.com/MoisesTapia/tmac-ai.git
cd tmac-ai
poetry install
tmac --version
```

## Option 3 — pip editable (from source)

```bash
git clone https://github.com/MoisesTapia/tmac-ai.git
cd tmac-ai

python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
pip install -e .
tmac --version
```

## Option 4 — Docker

```bash
# Scan a locally mounted directory
docker run --rm \
  -v $(pwd)/infra:/scan:ro \
  -v $(pwd)/output:/out \
  tmac-security/tmac:latest scan --dir /scan --output /out/report.html

# Show help
docker run --rm tmac-security/tmac:latest --help
```

To build the image locally from the repository Dockerfile:

```bash
docker build -t tmac .
docker run --rm -v $(pwd)/infra:/scan tmac scan --dir /scan
```

## Option 5 — pre-commit hook

Add TMAC as a hook in your repository to scan `.tf` files before each commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/MoisesTapia/tmac-ai
    rev: v1.6.0
    hooks:
      - id: tmac
```

```bash
pip install pre-commit
pre-commit install
```

---

## Install Graphviz (optional)

Required only for image output formats (`png`, `svg`, `pdf`) in `tmac diagram`:

```bash
# macOS
brew install graphviz

# Debian / Ubuntu
sudo apt-get install graphviz

# Windows (Chocolatey)
choco install graphviz
```

---

## Verify the installation

```bash
tmac --version   # should print: TMAC, version 1.6.0
tmac --help      # lists subcommands: scan, plan, ci, diagram
```
