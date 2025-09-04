# rs3-contracts (MIT)

Contrats stables pour l'écosystème RoadSimulator3 :
- Interfaces (`Stage`, `ContextSpec`, `Result`)
- Schéma dataset (YAML)
- Types partagés

## Installation (editable)
```bash
pip install -e ".[dev]"
```

## Versioning
SemVer : breaking = major, ajout compatible = minor, patch = corrections.

## Usage (ex.)
```py
from rs3_contracts.api import Stage, ContextSpec, Result
```