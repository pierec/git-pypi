# git-pypi

[![PyPI - Version](https://img.shields.io/pypi/v/git-pypi.svg)](https://pypi.org/project/git-pypi)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/git-pypi.svg)](https://pypi.org/project/git-pypi)

-----

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Overview

`git-pypi` provides a `pip`-compatible package index server that serves
packages based on the contents of a git repository. The server implements a
subset of [Simple Repository API](https://packaging.python.org/en/latest/specifications/simple-repository-api/).

It is meant to be used in a monorepo scenario, where some packages housed in
the repository depend on others. When using `git-pypi` as the package index,
one can avoid specifying git package URIs explicitly.

The packages are indexed based on git tags. The service makes the following
assumptions about the git repository:

* tags adhere to the following format: `<package-name>/v<package-version>`,
* tags are accurate w.r.t. the actual package versions they represent,
* the repository layout is flat, e.g:

```
.
├── package-a/
│   ├── pyproject.toml
│   └── [...]
├── package-b/
│   ├── pyproject.toml
│   └── [...]
└── [...]
```

Only serving source distributions is supported at this time.

When a specific package (e.g. `package_a-1.2.3.tar.gz`) is requested by `pip`,
and the artifact is not already cached, the server will perform the following
operations:

1. Check out the package directory tree (and, optionally, additional trees as
   dictated by the server config) at the given tag (e.g. `package-a/v1.2.3`) to
   a temporary build directory.
2. Run the build command in the temporary build directory.
3. Copy the package artifact to the cache.
4. Remove the temporary build directory.
5. Return a HTTP 200 response containing the package contents.

Subsequent requests for the same package will use the cached version. Cached
items are keyed by the SHA1 of the commit, so re-tagging a commit will cause
the package to be built again (NB: your package manager of choice is probably
doing its own caching - something to watch out when re-tagging releases).
Cache is persistent between server runs.

If a suitable config option is set, `git-pypi` shall also serve packages
directly from a predefined directory. This can be used to vendor-in some
Python dependencies in the repository. In the unlikely case of a naming
conflict between "git" and "vendored" packages, the former take precedence.

## Installation

```console
pipx install git-pypi
```

## Usage

After installation, `git-pypi` provides the following CLI scripts.

### git-pypi-configure

Generates a default `git-pypi` configuration file.

```console
$ git-pypi-configure -h

usage: git-pypi-configure [-h] [--config CONFIG] [--force]

Generate a default git-pypi configuration file.

options:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        Config file path.
  --force, -f           Overwrite existing file.
```

### git-pypi-run

Runs the `git-pypi` server.

```console
$ git-pypi-run -h

usage: git-pypi-run [-h] [--git-repo GIT_REPO] [--host HOST] [--port PORT] [--config CONFIG] [--clear-cache] [--debug]

Run the git-pypi server.

options:
  -h, --help            show this help message and exit
  --git-repo GIT_REPO, -r GIT_REPO
                        Git repository path.
  --host HOST, -H HOST  Server host
  --port PORT, -p PORT  Server port
  --config CONFIG, -c CONFIG
                        Config file path.
  --clear-cache         Clear the package cache prior to starting.
  --debug               Enable debug logging.
```

## Configuration

By default, `git-pypi-run` will attempt to read a configuration file from
`~/.git-pypi/config.toml`. Should the file be missing, a default configuration
shall be used. The config file location can be overridden by using `-c` flag.

Sample configuration file:

```toml
# Directory where package artifacts can be found.
package-artifacts-dir-path = "dist"

# Cache directory location.
cached-artifacts-dir-path = "~/.git-pypi/cache/artifacts"

# The sdist package build command.
build-command = ["make", "build"]

# Extra trees to check out for building (besides the requested package).
# extra_checkout_paths = [".makefiles"]

# Fallback index URL used if a package cannot be found. Leave empty or null to
# disable the additional lookup.
fallback-index-url = "https://pypi.python.org/simple"

# A directory containing vendored packages, relative to the repository root.
# Set to null to disable looking up packages in the local dir.
local-packages-dir-path = "vendor"

[server]
host = "127.0.0.1"
port = 60100
threads = 4
timeout = 300
```

## Example Repository Layout

Below is an example monorepository layout that works well with `git-pypi`.

```
.
├── package-a/
│   ├── Makefile
│   ├── pyproject.toml
│   ├── src/
│   └── [...]
├── package-b/
│   ├── Makefile
│   ├── pyproject.toml
│   ├── src/
│   └── [...]
├── package-c/
│   ├── Makefile
│   ├── pyproject.toml
│   ├── src/
│   └── [...]
├── vendor/
│   ├── vendored_dep_a-3.0.0-py3-any.whl
│   ├── vendored_dep_b-0.1.1.tar.gz
│   └── vendored_dep_b-0.2.0.tar.gz
├── .config/
│   └── git-pypi.toml
├── Makefile
└── [...]
```

## Development

A makefile codifying several common tasks is available for developer's
conevenience.

```console
make fmt                    # format the code
make check                  # run static checks
make test                   # run tests
make test-update-snapshots  # run tests and update snapshots
make build                  # build a package
```

## License

`git-pypi` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
