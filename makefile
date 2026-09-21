.PHONY: run test build

run:
	uv run mactop

test:
	uv run pytest

build:
	uv build
