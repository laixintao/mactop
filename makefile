bump_patch:
	bumpversion patch

bump_minor:
	bumpversion minor

patch: bump_patch
	rm -rf dist
	poetry build
	poetry publish
