# Update terraform state to upgrade missing part when you are on OVH public cloud before Stein

[![Tests on push](https://github.com/nledez/terraform_updater/actions/workflows/tests.yml/badge.svg)](https://github.com/nledez/terraform_updater/actions/workflows/tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/nledez/terraform_updater/badge.svg?branch=main&service=github)](https://coveralls.io/github/nledez/terraform_updater?branch=main)

## Requirements

Install [Poetry](https://python-poetry.org/docs/#installation) (>=1.2.1)

## Install

```
poetry install --with tests --with dev
```

## Tests & dev

```
poetry shell
ptw --nobeep --ignore .venv --onpass "terminal-notifier -title '✅' -message 'OK' ; coverage html" --onfail "terminal-notifier -title '🚨' -message 'KO'" -- --cov=terraform_updater --cov=tests
# Or only:
poetry run pytest -vvvvv --cov=terraform_updater --cov=tests && poetry run coverage html
```
