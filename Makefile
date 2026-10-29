.PHONY: \
	all \
	check \
	clean \
	format \
	tests \
	verify

all: check tests verify

check:
	black --check --line-length 100 tests
	flake8 --max-line-length 100 tests
	mypy tests

format:
	black --line-length 100 tests

tests:
	pytest --verbose tests

verify:
	qed verify specs/ctf.spec.toml

clean:
	rm --force --recursive .mypy_cache
	rm --force --recursive .pytest_cache
	rm --force --recursive tests/__pycache__
