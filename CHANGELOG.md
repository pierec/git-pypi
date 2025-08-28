# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## v1.0.0

### Changed
* *BREAKING CHANGE!* `git-pypi-run` no longer accepts `--git-repo / -r`
  parameter. Instead, repository information should solely come from the config
  file.

* *BREAKING CHANGE!* Added support for configuring multiple repositories. The
  change necessiated backwards-incompatible changes in the TOML config file.
  Consult the [README.md](./README.md) for details. 

* Added support for specifying git remote URI in the config. Such repositories
  will be automatically cloned on service start, if not cloned already.

* Git repositories are now refreshed (via `git fetch --tags`) prior to checking
  for packages.

### Fixed
* Git repositories with submodules are now correctly handled. Previously and
  error would be raised during checkout. Internally, all git operations are now
  made using `subprocess` calls to `git` command, with checkout being handled
  via a `git worktree` command.

## v0.5.0

### Added

* `git-pypi-run` now supports a `--version` flag. If set, the script shall
  print `git-pypi` version and exit.

## v0.4.0

### Added

* Added support for serving packages from a predefined local directory. This
  feature is intended for vendoring in packages in the repository. The feature
  is off by default. Set `local-packages-dir-path` (default: ` null`) config
  option to enable.

## v0.3.0

### Changed

* Produce a nicer error message if building an artifact succeeded without
  producing a file in an expected location.

## v0.2.1

### Fixed

* Updated the project classifiers to reflect Python version compatibility.

## v0.2.0

### Changed

* The package is now compatible with Python 3.10.

## v0.1.0

The inaugural version. Hello world!

### Added

* Implemented `git-pypi` - a basic Python Package Index serving packages based on a git
  repository contents.
* Added `git-pypi-configure` CLI command for creating an example `pypi` config.
* Added `git-pypi-run` CLI command for running the `git-pypi` server.
