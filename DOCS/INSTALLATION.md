# Installation

## Requirements

- **Python 3.10+**
- *(Optional)* [Graphviz](https://graphviz.org/) — required only to render diagrams as images (`png`, `svg`, `pdf`).

---

## Option 1 — From the repository (recommended)

```bash
pip install "https://github.com/MoisesTapia/tmac-ai/archive/main.tar.gz"   # pin a tag or commit SHA instead of main
tmac --version
```

> **Note:** the PyPI package named `tmac` is an **unrelated project** — do not
> `pip install tmac`. Install TMAC from this repository (pin a tag or commit SHA in CI).

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
pip install --require-hashes -r requirements.txt   # exact, hash-verified dependencies
pip install --no-deps -e .
tmac --version
```

## Option 4 — Docker

Build the image from the repository Dockerfile (dependencies are installed from the
hash-locked `requirements.txt`):

```bash
docker build -t tmac .

# Scan a locally mounted directory
docker run --rm \
  -v $(pwd)/infra:/scan:ro \
  -v $(pwd)/output:/out \
  tmac scan --dir /scan --output /out/report.html

# Show help
docker run --rm tmac --help
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
tmac --help      # lists subcommands: scan, cfn, plan, ci, diagram
```
