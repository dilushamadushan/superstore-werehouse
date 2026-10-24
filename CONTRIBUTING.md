# Contributing to the Superstore Warehouse Project

Thanks for your interest in improving this warehouse project.

## Project goals
This project is designed to demonstrate an end-to-end data warehouse workflow using:
- PostgreSQL / Supabase
- Python
- SQLAlchemy
- Pandas
- ETL and analytics processing

The focus is on clean warehouse design, data transformation, and BI reporting.

## How to contribute

### 1. Fork or clone the repository
Create a working copy of the project on your machine.

### 2. Set up the environment
Follow the setup steps in the documentation:
- [docs/setup-guide.md](docs/setup-guide.md)
- [docs/project-overview.md](docs/project-overview.md)

Create a local `.env` file using the template in `.env.example`.

### 3. Work on a focused change
Keep pull requests small and focused. Good examples include:
- fixing ETL logic
- improving warehouse validation
- adding tests
- fixing documentation issues
- improving query correctness

### 4. Validate before submitting
Run the relevant tests and smoke checks before you open a pull request.

Example:

```bash
python -m unittest discover -s tests -p "test_*.py"
python main.py
```

### 5. Submit a clean pull request
Include:
- a clear title
- a short summary of the change
- what was tested
- any notes on environment or setup

## Coding expectations
- Keep functions clear and readable
- Prefer small, reusable logic blocks
- Maintain the project’s warehouse architecture
- Avoid hardcoding production secrets
- Respect the existing file structure and naming conventions

## Documentation standards
When changing behavior, update the relevant documents in the docs folder:
- [docs/README.md](docs/README.md)
- [docs/project-overview.md](docs/project-overview.md)
- [docs/setup-guide.md](docs/setup-guide.md)
- [docs/upgrade-plan.md](docs/upgrade-plan.md)

## Good contribution ideas
- Add ETL validation checks
- Improve star schema correctness
- Add unit tests for the SQL layer
- Refine reporting or query output
- Improve the project documentation

## Questions or suggestions
If you are unsure about a contribution, start by opening a discussion or issue. Clear, focused changes are preferred over large unrelated updates.
