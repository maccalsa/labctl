# CLI Reference

Every labctl command, its arguments, options, and examples.

## Global options

| Option | Short | Description |
|--------|-------|-------------|
| `--version` | `-V` | Show version and exit |
| `--help` | | Show help and exit |

```bash
labctl --version
labctl --help
```

---

## `labctl create`

Create a new dev machine from a template.

### Synopsis

```
labctl create NAME [--template TEMPLATE]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `NAME` | Yes | Name for the machine. Used as the container hostname and DNS name on the network. |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--template` | `-t` | `blank` | Template to use for the machine. |

### What happens

1. The template image is built (or reused if cached).
2. A container named `labctl-NAME` is created with management labels.
3. The container is attached to the `labctl-net` network with `NAME` as its DNS hostname.
4. The container starts.

### Examples

```bash
# Create a machine with the default (blank) template
labctl create my-dev

# Create a machine with a specific template
labctl create api --template node
labctl create db -t postgres
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Machine created successfully |
| 1 | Error (duplicate name, unknown template, Docker unavailable) |

---

## `labctl list`

Show all labctl-managed machines.

### Synopsis

```
labctl list
```

### Output columns

| Column | Description |
|--------|-------------|
| Name | Machine name (without the `labctl-` prefix) |
| Template | Template the machine was created from |
| Status | `running` or `exited` |
| Ports | Mapped ports in `container_port->host_port` format |

### Examples

```bash
# List all machines
labctl list

# Example output:
#   Machines
# ┏━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━┓
# ┃ Name ┃ Template ┃ Status  ┃ Ports       ┃
# ┡━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━┩
# │ api  │ node     │ running │ 3000→32768  │
# │ db   │ postgres │ running │ 5432→32769  │
# └──────┴──────────┴─────────┴─────────────┘
```

When no machines exist, prints "No machines found."

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success (even if no machines exist) |
| 1 | Error (Docker unavailable) |

---

## `labctl destroy`

Remove a dev machine.

### Synopsis

```
labctl destroy NAME [--volumes] [--force]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `NAME` | Yes | Machine to destroy. |

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--volumes` | | `false` | Also delete named volumes associated with the machine. |
| `--force` | `-f` | `false` | Skip confirmation. |

### Behavior

- Removes the container for the named machine.
- If the machine has named volumes (e.g. from a `postgres` template), labctl
  warns you and lists the volume names. Use `--volumes` to delete them too.
- If the machine doesn't exist, exits with a clear error.

### Examples

```bash
# Destroy a machine (volumes are preserved)
labctl destroy api

# Destroy a machine and its volumes
labctl destroy db --volumes

# Destroy without confirmation
labctl destroy api --force
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Machine destroyed |
| 1 | Error (machine not found, Docker unavailable) |

---

## `labctl shell`

Open an interactive shell inside a running machine.

### Synopsis

```
labctl shell NAME
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `NAME` | Yes | Machine to open a shell in. |

### Behavior

- Detects the best available shell: prefers `/bin/bash`, falls back to
  `/bin/sh`.
- Attaches an interactive session with a TTY.
- Propagates the shell's exit code.

### Examples

```bash
# Open a shell
labctl shell my-dev

# Run a quick command (via the shell)
labctl shell my-dev
> echo "hello from inside"
> exit
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Shell session exited cleanly |
| 1 | Error (machine not found, machine not running) |
| other | Propagated from the shell process |

!!! note "Machine must be running"
    If the machine is stopped, labctl tells you to start it first:
    `labctl start NAME` (available in a future release).
