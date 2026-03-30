# labctl

[![CI](https://github.com/maccalsa/labctl/actions/workflows/ci.yml/badge.svg)](https://github.com/maccalsa/labctl/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Local dev labs without the nonsense.**

labctl creates small, connected, machine-like development environments
using containers — without needing Docker Compose, networking knowledge,
or complex configuration.

**[Documentation](https://maccalsa.github.io/labctl)**

## Requirements

- Python 3.11+
- Docker (running)

## Install

### Recommended: pipx

```bash
pipx install git+https://github.com/maccalsa/labctl.git
```

### Alternative: pip

```bash
pip install git+https://github.com/maccalsa/labctl.git
```

### Verify

```bash
labctl --version
```

## Usage

```bash
# Create a dev machine
labctl create my-dev

# See what's running
labctl list

# Jump into a shell
labctl shell my-dev

# Tear it down
labctl destroy my-dev
```

Machines land on a shared network and resolve each other by name:

```bash
labctl create api
labctl create db --template postgres

labctl shell api
ping db    # just works
```

## Development

```bash
git clone https://github.com/maccalsa/labctl.git
cd labctl
pip install -e ".[dev]"

make test      # run tests
make lint      # check linting
make format    # auto-format
```

## Security

labctl is a local development tool. It assumes a trusted local environment.
Do not expose labctl-managed machines to untrusted networks.

## License

MIT
