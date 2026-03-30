# labctl

Local dev labs without the nonsense.

`labctl` creates small, connected, machine-like development environments
using containers — without needing Docker Compose, networking knowledge,
or complex configuration.

## Requirements

- Python 3.11+
- Docker (running)

## Install

```bash
pip install -e ".[dev]"
```

## Usage

```bash
labctl --help
labctl create api-dev --template node
labctl list
labctl shell api-dev
labctl destroy api-dev
```

## Development

```bash
make dev       # install with dev deps
make test      # run tests
make lint      # check linting
make format    # auto-format
```

## Security

labctl is a local development tool. It assumes a trusted local environment.
Do not expose labctl-managed machines to untrusted networks.
