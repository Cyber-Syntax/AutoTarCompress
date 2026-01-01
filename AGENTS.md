# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## General Guidelines

1. KISS (Keep It Simple, Stupid): Aim for simplicity and clarity. Avoid unnecessary abstractions or metaprogramming.
2. DRY (Don't Repeat Yourself): Reuse code appropriately but avoid over-engineering. Each command handler has single responsibility.
3. YAGNI (You Aren't Gonna Need It): Always implement things when you actually need them, never when you just foresee that you need them.
4. ALWAYS use `ruff check <filepath>` on each Python file you modify to ensure proper linting and formatting:
    - Use `ruff check --fix <filepath>` to automatically fix any fixable errors.
    - Use `ruff format path/to/file.py` to format a specific file.
    - Use `ruff format path/to/code/` to format all files in `path/to/code` (and any subdirectories).
    - Use `ruff format` to format all files in the current directory.

## Testing Instructions

Critical: Run tests after any change to ensure nothing breaks.

```bash
# Run all tests:
uv run pytest
# Run specific test file:
uv run pytest tests/test_config.py
# Run specific test function:
uv run pytest tests/test_config.py::test_function_name
# Run with coverage
uv run pytest tests/python/ --cov=aps.<folder>.<module>
uv run pytest tests/cli/test_parser.py --cov=my_unicorn.cli.parser
```

## Code Style Guidelines

- Use built-in types: `list[str]`, `dict[str, int]`
- Use `%s` style formatting in logging statements
- Use `logger.exception("message")` in exception handlers to log stack traces

## Project Overview

**AutoTarCompress** is a Python 3.12+ CLI tool for automating the process of backup and compression.
It's backup the dirs that user written to config file while ignoring the dirs that user don't need - node_modules, **pycache** - or custom dirs that user want to ignore.
