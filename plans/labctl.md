# Plan: labctl

> Source PRD: `plan/plan.md`
> Decisions register: `plan/plan-review.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **CLI**: `labctl` via Typer. `pyproject.toml` console script entry point.
- **Runtime**: Docker only via `docker-py`. `ContainerRuntime` Protocol
  defines the backend interface; only `DockerRuntime` is implemented.
- **Network**: Single shared `labctl-net` (Docker user-defined bridge).
  Docker built-in DNS for machine-to-machine resolution. Bare hostnames
  (`api-dev`, `db-dev`) — no `.local` suffix.
- **State**: Docker labels are the source of truth. Every managed container
  carries `labctl.managed=true`, `labctl.machine=<name>`,
  `labctl.template=<tpl>`, `labctl.network=labctl-net`. No local state
  files for machine inventory.
- **Templates**: Each template is a directory (`Dockerfile`,
  `devcontainer.json`, `template.toml`). Built-in templates ship as
  package data, copied to `~/.labctl/templates/` on first use. User-custom
  templates go in the same directory.
- **Ports**: Template-defined container ports mapped to dynamic host ports.
  `labctl ports` discovers mappings. `--port` overrides/supplements.
- **Volumes**: No bind mount by default. Data service templates declare
  named volumes in `template.toml`. `labctl destroy` warns about volumes;
  `--volumes` flag deletes them.
- **Shell access**: `labctl shell <name>` via `docker exec -it`. No SSH.
- **IDE**: VS Code only via `labctl code <name>` (runs
  `code --remote containers+<id> /workspace`).
- **Config**: `~/.labctl/config.toml` for user preferences.
- **Host OS**: Linux + macOS. Windows deferred.
- **Security**: Trusted local environment. Root in containers. Documented
  posture, no hardening for MVP.

---

## Phase 0: Scaffold (complete)

**User stories**: As a developer, I can install labctl and see `--help`.

### What was built

Repo structure with `pyproject.toml`, Typer CLI entry point with stub
commands (`create`, `list`, `destroy`, `shell`), `ContainerRuntime`
Protocol, smoke tests, ruff linting, Makefile.

### Acceptance criteria

- [x] `pip install -e ".[dev]"` succeeds
- [x] `labctl --help` exits 0 and shows all commands
- [x] `pytest` passes (6 smoke tests)
- [x] `ruff check` clean

---

## Phase 1: DockerRuntime + network bootstrap

**User stories**: As a developer, labctl can talk to my Docker daemon and
manage a shared network for my machines.

### What to build

Implement the `DockerRuntime` class that satisfies the `ContainerRuntime`
Protocol using `docker-py`. On any operation that needs the network,
ensure `labctl-net` exists (create if missing, no-op if present). Include
a `docker_available()` health check that gives a clear error if Docker
isn't running.

The runtime should be injectable — commands receive it as a dependency so
tests can substitute a mock or a real Docker connection.

### Acceptance criteria

- [ ] `DockerRuntime` implements all methods on `ContainerRuntime`
- [ ] `create_network("labctl-net")` is idempotent (safe to call twice)
- [ ] `network_exists("labctl-net")` returns correct bool
- [ ] Health check raises a clear `LabctlError` when Docker is unreachable
- [ ] Integration tests pass against a real Docker daemon
- [ ] Unit tests pass with mocked `docker.DockerClient`

---

## Phase 2: `labctl create` with blank template

**User stories**: As a developer, I can create a named dev machine with one
command and it appears as a running container on the shared network.

### What to build

Wire the `create` CLI command to `DockerRuntime`. Ship a `blank` template
(ubuntu:24.04, bash, curl, git pre-installed). At creation:

1. Ensure `labctl-net` exists.
2. Build or pull the template image.
3. Create the container with labels (`labctl.managed=true`,
   `labctl.machine=<name>`, `labctl.template=blank`,
   `labctl.network=labctl-net`).
4. Attach to `labctl-net` with the machine name as the hostname.
5. Publish template-defined ports to dynamic host ports.
6. Start the container.

Reject duplicate names with a clear error.

### Acceptance criteria

- [ ] `labctl create foo` creates a running container named `labctl-foo`
- [ ] Container has all four labels set correctly
- [ ] Container is on `labctl-net` with hostname `foo`
- [ ] `docker inspect` shows published ports
- [ ] Duplicate name gives a clear error, not a stack trace
- [ ] `blank` template builds successfully
- [ ] Integration test: create → inspect → verify labels and network

---

## Phase 3: `labctl list` + `labctl destroy`

**User stories**: As a developer, I can see all my machines and remove ones
I no longer need.

### What to build

**list**: Query Docker for containers with `labctl.managed=true`. Display
a rich table with columns: name, template, status (running/stopped),
ports, created. Handle the empty case gracefully ("No machines found").

**destroy**: Remove the container by name. If the machine has named
volumes, warn the user and require `--volumes` to delete them too.
If `--force` is passed, skip confirmation. Error clearly if the machine
doesn't exist.

### Acceptance criteria

- [ ] `labctl list` shows a table with name, template, status, ports
- [ ] `labctl list` with no machines prints a helpful empty message
- [ ] `labctl destroy foo` removes the container
- [ ] `labctl destroy foo --volumes` also removes named volumes
- [ ] `labctl destroy nonexistent` gives a clear error
- [ ] Integration test: create → list (appears) → destroy → list (gone)

---

## Phase 4: `labctl shell`

**User stories**: As a developer, I can drop into an interactive shell
inside any running machine.

### What to build

Wire the `shell` command to `DockerRuntime.exec_interactive`. Default
command is `/bin/bash`, falling back to `/bin/sh` if bash isn't available.
Error clearly if the machine doesn't exist or isn't running.

**MVP-0 is complete after this phase.** The core machine lifecycle
(create → list → shell → destroy) works end-to-end.

### Acceptance criteria

- [ ] `labctl shell foo` opens an interactive bash session
- [ ] Falls back to `/bin/sh` if bash isn't available
- [ ] Error on nonexistent machine
- [ ] Error on stopped machine (with suggestion: "run `labctl start foo`")
- [ ] Integration test: create → shell (run `echo hello`) → verify output

---

## Phase 5: Template engine

**User stories**: As a developer, I can create machines from language and
service templates so I don't have to configure anything.

### What to build

Template loading system:

1. On first `create` that uses a template, copy built-in templates from
   package data to `~/.labctl/templates/` if not already present.
2. Parse `template.toml` for metadata: name, description, default ports,
   default volumes, base image.
3. Build images from `Dockerfile` in the template directory, tagged
   `labctl-<template>:latest`.
4. User-custom templates in `~/.labctl/templates/` are discovered
   automatically.

Ship 6 templates:

| Template | Base | Ports | Volumes |
|----------|------|-------|---------|
| `blank` | ubuntu:24.04 | — | — |
| `python` | python:3.12-slim | 8000 | — |
| `node` | node:22-slim | 3000 | — |
| `go` | golang:1.23 | 8080 | — |
| `postgres` | postgres:17 | 5432 | `labctl-<name>-data:/var/lib/postgresql/data` |
| `redis` | redis:7 | 6379 | `labctl-<name>-data:/data` |

Each includes a `devcontainer.json` for VS Code integration (Phase 7).

### Acceptance criteria

- [ ] `labctl create db --template postgres` creates a working Postgres
- [ ] `labctl create api --template node` creates a container with node
- [ ] All 6 templates build and start successfully
- [ ] `template.toml` is parsed for ports and volumes
- [ ] Postgres machine's data survives destroy/recreate (named volume)
- [ ] Unknown template name gives a clear error listing available ones
- [ ] Custom template in `~/.labctl/templates/my-tpl/` is discovered
- [ ] Integration test: create with each template → verify running

---

## Phase 6: Lifecycle + observability

**User stories**: As a developer, I can stop/start machines, see their
port mappings, and tail their logs.

### What to build

**start/stop**: Wrap `DockerRuntime.start`/`stop`. Error if machine
doesn't exist. `start` on a running machine is a no-op. `stop` on a
stopped machine is a no-op.

**ports**: Query `docker inspect` for port mappings. Display a table:
`container_port → host_port`. If no ports are mapped, say so.

**logs**: Wrap `DockerRuntime.logs`. Support `--follow` (streams) and
`--tail N` (last N lines, default 100).

### Acceptance criteria

- [ ] `labctl stop foo` stops a running machine
- [ ] `labctl start foo` starts a stopped machine
- [ ] `labctl start foo` on a running machine is a silent no-op
- [ ] `labctl ports foo` shows `container_port → localhost:host_port`
- [ ] `labctl ports foo` on a machine with no ports says "no ports mapped"
- [ ] `labctl logs foo` shows last 100 lines
- [ ] `labctl logs foo --follow` streams live output
- [ ] `labctl logs foo --tail 20` shows last 20 lines

---

## Phase 7: VS Code integration + config

**User stories**: As a developer, I can open any machine in VS Code with
one command, and configure my default preferences.

### What to build

**code**: Run `code --remote containers+<container-id> /workspace`.
Check that `code` is on PATH first — if not, give a clear error with
install instructions. Each template's `devcontainer.json` is already
inside the container (placed during Phase 5 image build).

**config**: Create `~/.labctl/config.toml` on first run with commented-out
defaults. Support at minimum:

```toml
# default_template = "blank"
# editor = "code"
```

`labctl create` uses `default_template` when `--template` is omitted.

**MVP-1 is complete after this phase.**

### Acceptance criteria

- [ ] `labctl code foo` opens VS Code attached to the container
- [ ] Clear error if VS Code isn't installed
- [ ] `devcontainer.json` is present inside the container at
      `/workspace/.devcontainer/devcontainer.json`
- [ ] `~/.labctl/config.toml` is created with commented defaults
- [ ] `default_template` config is respected by `labctl create`
- [ ] Integration test: create → code (verify `code` CLI invoked with
      correct args, mocked)
