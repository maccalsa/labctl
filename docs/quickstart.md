# Quickstart

Get labctl installed and create your first dev machine in under two
minutes.

## Prerequisites

- **Python 3.11+** &mdash; check with `python3 --version`
- **Docker** &mdash; running and accessible (`docker info` should work)
- **pipx** (recommended) &mdash; install with `pip install --user pipx`

## Install

### Recommended: pipx (isolated, one command)

```bash
pipx install git+https://github.com/maccalsa/labctl.git
```

This installs `labctl` into its own virtualenv and puts it on your
`$PATH`. No conflicts with other Python packages.

### Alternative: pip

```bash
pip install git+https://github.com/maccalsa/labctl.git
```

### Verify

```bash
labctl --version
# labctl 0.1.0
```

## Your first machine

### 1. Create a machine

```bash
labctl create my-dev
```

This pulls the `blank` template (Ubuntu 24.04 with bash, curl, and git),
builds the image, and starts a container named `labctl-my-dev` on the
shared `labctl-net` network.

### 2. See it running

```bash
labctl list
```

You'll see a table with your machine's name, template, status, and any
mapped ports.

### 3. Jump in

```bash
labctl shell my-dev
```

You're now inside the machine with a bash shell. Poke around, install
things, run code. When you're done, `exit` to return.

### 4. Clean up

```bash
labctl destroy my-dev
```

The container is removed. If the machine had named volumes, labctl tells
you they still exist and how to remove them.

## Two machines that talk to each other

Every labctl machine lands on the same Docker network (`labctl-net`) with
DNS resolution by name.

```bash
labctl create api
labctl create backend

# From inside 'api', you can reach 'backend' by hostname
labctl shell api
ping backend    # resolves immediately
exit

# Tear them both down
labctl destroy api
labctl destroy backend
```

## What's next

- See every command and option in the [CLI Reference](cli-reference.md)
- Browse common workflows in the [Cheat Sheet](cheatsheet.md)
