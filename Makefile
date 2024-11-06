test:
	hatch run test -vv
.PHONY: test

test-update-snapshots:
	hatch run test -vv --snapshot-update
.PHONY: test

fmt:
	hatch run lint:fmt
.PHONY: fmt

check:
	hatch run lint:check
	hatch run types:check
.PHONY: check

requirements.txt: pyproject.toml
	@hatch run pip-compile \
	  --upgrade \
	  --generate-hashes \
	  -o requirements.txt \
	  pyproject.toml

build:
	@hatch clean
	@hatch build
.PHONY: build

bump-version-%:
	@hatch version $*
.PHONY: bump-version-%

print-project-version:
	@hatch version
.PHONY: print-version

git-push-tag:
	@TAG="v$$(make print-project-version)"; \
	git ls-remote --exit-code origin "refs/tags/$${TAG}" \
	  || { \
	    git tag -f "$${TAG}" \
	    && git push origin tag "$${TAG}"; \
	  };
.PHONY: git-push-tag
