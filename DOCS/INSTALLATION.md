# Installation

## Requirements

- **Python 3.10+**
- [Poetry](https://python-poetry.org/) (recommended) or `pip`
- *(Optional)* [Graphviz](https://graphviz.org/) — only required to render diagrams as images (`png`, `svg`, `pdf`).

## Install with Poetry

```bash
git clone https://github.com/MoisesTapia/tmac-ai.git
cd tmac-ai
poetry install
```

## Install with pip

```bash
git clone https://github.com/MoisesTapia/tmac-ai.git
cd tmac-ai

python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
pip install -e .
```

## Install Graphviz (optional)

Required only for image output formats in `tmac diagram`:

```bash
# macOS
brew install graphviz

# Debian / Ubuntu
apt-get install graphviz
```

## Verify the installation

```bash
tmac --version
tmac --help
```

You should see the TMAC version and the list of available subcommands (`scan`, `plan`, `diagram`).
