# Running tests

## Running tests in local QGIS environment 

You must have an environment with a version of QGIS is installed with
python support (which is available in most of the linux distributions).

Developpement should always take place in a python virtualenv: two ways
of achieving this are supported.

### Using [`uv`](https://docs.astral.sh/uv/)

uv is a great tool for managing dependencies an running tools from a
python virtual env.

First you must [install `uv`](https://docs.astral.sh/uv/getting-started/installation/).

#### Setting up the environment with uv

```
# Create a virtual env with access to system packages (required for using pyQGIS)
> uv venv --system-site-packages
# Update the project's environment
> uv sync --frozen   
```

Run the tests:
```
> make test
```

It always possible to activate the environment with `. ./.venv/bin/activate` for
using tool command directly (`pytest`, ...) or just run your command with
`uv run <command>`.


### Setting up the environment with python venv and pip

```
# Create a virtual env with access to system packages (required for using pyQGIS)
> python -m venv .venv --system-site-packages 
# Activate the environment
> . ./venv/bin/activate
# Update the project's environment
> pip install -r requirements/dev.txt
```

Run the tests:
```
> make test
```

Note that each time you want to do tasks in your environment you will have to
activate the environment.

### Using an existing environment 

You may always use an existing python environment. 

If you plan to use uv with it, juste add `UV_RUN=uv run --active` in your
`.localconfig.mk`.

## Running tests with docker

Tests are run in a docker QGIS image.

```
make docker-test [QGIS_VERSION=<version>]
```

## Enable WebDav and Postgresql tests

1. Copy `credentials.exemple.py` as `credentials.py`
1. Set the environment variables appropriately. 

Note that you may define your environment variables in your
`.localconfig.mk`:

```
export PG_HOST=...
...
```


