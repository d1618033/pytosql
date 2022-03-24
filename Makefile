do_format:
	black pytosql tests
	isort **/*.py

check_format:
	black --check pytosql tests
	isort **/*.py --check-only

lint:
	pylint pytosql tests
	mypy --install-types --non-interactive pytosql

