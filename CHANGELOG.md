# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
