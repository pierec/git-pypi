import logging
import typing as t
from textwrap import dedent

import falcon
import jinja2

from git_pypi.config import DEFAULT_CONFIG, Config
from git_pypi.exc import PackageNotFoundError
from git_pypi.git_package_index import GitPackageIndex

logger = logging.getLogger(__name__)

URI: t.TypeAlias = str


class ProjectResource:
    def __init__(
        self,
        git_package_index: GitPackageIndex,
        fallback_index_url: URI | None = None,
    ) -> None:
        self._git_package_index = git_package_index
        self._fallback_index_url = fallback_index_url

        jinja_env = jinja2.Environment(
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._template = jinja_env.from_string(
            dedent(
                """
            <html>
                <body>
                    <h1>Links for {{project}}</h1>
                    {% for file, href in links %}
                        <a href="{{href}}">{{file}}</a><br>
                    {% endfor %}
                </body>
            </html>
            """
            ).strip()
        )

    def on_get(
        self,
        request: falcon.Request,
        response: falcon.Response,
        project_name: str,
    ) -> None:
        package_file_names = self._git_package_index.list_packages(project_name)

        if not package_file_names:
            if self._fallback_index_url:
                raise falcon.HTTPMovedPermanently(
                    f"{self._fallback_index_url}/{project_name}/"
                )
            else:
                raise falcon.HTTPNotFound

        html = self._template.render(
            {
                "project": project_name,
                "links": [(fn, f"/packages/{fn}") for fn in package_file_names],
            }
        )

        response.status_code = 200
        response.content_type = falcon.MEDIA_HTML
        response.text = html


class PackageResource:
    def __init__(self, git_package_index: GitPackageIndex) -> None:
        self._git_package_index = git_package_index

    def on_get(
        self,
        request: falcon.Request,
        response: falcon.Response,
        file_name: str,
    ) -> None:
        try:
            file_path = self._git_package_index.get_package_by_file_name(file_name)
        except PackageNotFoundError as e:
            raise falcon.HTTPNotFound from e

        response.status_code = 200
        response.content_type = "application/octet-stream"
        response.content_length = file_path.stat().st_size
        response.stream = file_path.open("rb")


class HealthResource:
    def on_get(self, request: falcon.Request, response: falcon.Response) -> None:
        response.status_code = 200
        response.media = {}


def create_app(config: Config = DEFAULT_CONFIG) -> falcon.App:
    app = falcon.App()
    app.req_options.strip_url_path_trailing_slash = True

    git_package_index = GitPackageIndex.from_config(config)
    app.add_route(
        "/simple/{project_name}",
        ProjectResource(
            git_package_index,
            fallback_index_url=config.fallback_index_url,
        ),
    )
    app.add_route(
        "/packages/{file_name}",
        PackageResource(git_package_index),
    )
    app.add_route(
        "/health",
        HealthResource(),
    )

    return app
