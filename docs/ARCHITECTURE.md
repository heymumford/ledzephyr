# Architecture

## Layers

```
Presentation (CLI) ← Application ← Infrastructure
    ↑                    ↑
    └── Domain ←─────────┘
```

- **Domain**: Business entities and rules (no external deps)
- **Application**: Use cases and orchestration
- **Infrastructure**: External integrations (APIs, files)
- **Presentation**: User interfaces (CLI)

## Rules

- Dependencies point inward toward Domain
- Inner layers cannot depend on outer layers
- Use protocols/interfaces for dependencies

## Validation

```bash
poetry run python scripts/check-dependencies.py    # Boundary violations
poetry run python scripts/validate-interfaces.py   # Protocol compliance
poetry run python scripts/check-architecture.py    # Clean architecture
poetry run python scripts/measure-coupling.py      # Coupling metrics
```