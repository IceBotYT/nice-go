# Nice G.O.

[![PyPI](https://img.shields.io/pypi/v/nice-go?style=flat-square)](https://pypi.python.org/pypi/nice-go/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nice-go?style=flat-square)](https://pypi.python.org/pypi/nice-go/)
[![PyPI - License](https://img.shields.io/pypi/l/nice-go?style=flat-square)](https://pypi.python.org/pypi/nice-go/)
[![codecov](https://codecov.io/github/IceBotYT/nice-go/graph/badge.svg?token=CR93ZO1FNN)](https://codecov.io/github/IceBotYT/nice-go)
[![Coookiecutter - Wolt](https://img.shields.io/badge/cookiecutter-Wolt-00c2e8?style=flat-square&logo=cookiecutter&logoColor=D4AA00&link=https://github.com/woltapp/wolt-python-package-cookiecutter)](https://github.com/woltapp/wolt-python-package-cookiecutter)


---

**Documentation**: [https://IceBotYT.github.io/nice-go](https://IceBotYT.github.io/nice-go)

**Source Code**: [https://github.com/IceBotYT/nice-go](https://github.com/IceBotYT/nice-go)

**PyPI**: [https://pypi.org/project/nice-go/](https://pypi.org/project/nice-go/)

---

Control various Nice garage door and gate products

## Installation

```sh
pip install nice-go
```

## Development

* Clone this repository
* Requirements:
  * [Poetry](https://python-poetry.org/)
  * Python 3.9+
* Create a virtual environment and install the dependencies

```sh
poetry install
```

* Activate the virtual environment

```sh
poetry shell
```

### Testing

```sh
pytest
```

### Documentation

The documentation is automatically generated from the content of the [docs directory](https://github.com/IceBotYT/nice-go/tree/master/docs) and from the docstrings
 of the public signatures of the source code. The documentation is updated and published as a [Github Pages page](https://pages.github.com/) automatically as part each release.

### Releasing

Trigger the [Draft release workflow](https://github.com/IceBotYT/nice-go/actions/workflows/draft_release.yml)
(press _Run workflow_). This will update the changelog & version and create a GitHub release which is in _Draft_ state.

Find the draft release from the
[GitHub releases](https://github.com/IceBotYT/nice-go/releases) and publish it. When
 a release is published, it'll trigger [release](https://github.com/IceBotYT/nice-go/blob/master/.github/workflows/release.yml) workflow which creates PyPI
 release and deploys updated documentation.

### Pre-commit

Pre-commit hooks run all the auto-formatting (`ruff format`), linters (e.g. `ruff` and `mypy`), and other quality
 checks to make sure the changeset is in good shape before a commit/push happens.

You can install the hooks with (runs for each commit):

```sh
pre-commit install
```

Or if you want them to run only for each push:

```sh
pre-commit install -t pre-push
```

Or if you want e.g. want to run all checks manually for all files:

```sh
pre-commit run --all-files
```

---

This project was generated using the [wolt-python-package-cookiecutter](https://github.com/woltapp/wolt-python-package-cookiecutter) template.
