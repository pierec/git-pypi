class GitPackageIndexError(Exception): ...


class BuilderError(GitPackageIndexError): ...


class GitError(GitPackageIndexError): ...


class PackageNotFoundError(GitPackageIndexError): ...
