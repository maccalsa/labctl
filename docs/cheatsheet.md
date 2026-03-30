# Cheat Sheet

Copy-pasteable recipes for common labctl workflows.

## Single machine

### Create and jump in

```bash
labctl create dev
labctl shell dev
```

### See what's running

```bash
labctl list
```

### Tear it down

```bash
labctl destroy dev
```

---

## Multi-machine setup

### API + database

Create two machines. They resolve each other by name automatically.

```bash
labctl create api
labctl create db --template postgres
```

Verify connectivity from the API machine:

```bash
labctl shell api
ping db          # resolves via Docker DNS
curl db:5432     # reaches Postgres
exit
```

Clean up both:

```bash
labctl destroy api
labctl destroy db --volumes
```

### Three-tier setup

```bash
labctl create frontend --template node
labctl create backend  --template python
labctl create db       --template postgres
```

From any machine, the other two are reachable by name:

```bash
labctl shell backend
curl http://frontend:3000   # Node dev server
psql -h db -U postgres      # Postgres
exit
```

---

## Template shortcuts

| What you want | Command |
|---------------|---------|
| Blank Ubuntu box | `labctl create dev` |
| Node.js | `labctl create api --template node` |
| Python | `labctl create api --template python` |
| Go | `labctl create api --template go` |
| Postgres | `labctl create db --template postgres` |
| Redis | `labctl create cache --template redis` |

!!! note "Templates coming soon"
    The full template set (node, python, go, postgres, redis) ships in
    Phase 5. Currently only the `blank` template is available.

---

## Volumes and data persistence

Postgres and Redis templates create named volumes so data survives
container restarts.

```bash
# Destroy machine but keep data
labctl destroy db

# Destroy machine AND its data
labctl destroy db --volumes
```

---

## Quick reference

| Task | Command |
|------|---------|
| Install labctl | `pipx install git+https://github.com/maccalsa/labctl.git` |
| Create a machine | `labctl create NAME [-t TEMPLATE]` |
| List machines | `labctl list` |
| Open a shell | `labctl shell NAME` |
| Destroy a machine | `labctl destroy NAME [--volumes]` |
| Check version | `labctl --version` |
| Get help | `labctl --help` or `labctl COMMAND --help` |
