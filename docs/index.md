# labctl

**Local dev labs without the nonsense.**

labctl creates small, connected, machine-like development environments
using containers. No Docker Compose files, no networking config, no YAML
sprawl. One command per machine.

## The idea

You want a Linux box with Node installed. Or a Postgres database your API
can talk to by name. Or three machines on the same network so you can test
a microservice setup. labctl makes that a few commands instead of a
side-quest into container orchestration.

## What it looks like

```bash
# Create two machines on the same network
labctl create api --template node
labctl create db  --template postgres

# They can already resolve each other by name
labctl shell api
curl http://db:5432  # just works

# See everything running
labctl list

# Done for the day
labctl destroy api
labctl destroy db
```

## Core principles

- **Machines, not containers.** You think in terms of dev machines, not
  Docker implementation details.
- **Connected by default.** Every machine lands on a shared network with
  DNS. Bare hostnames work out of the box.
- **Zero config for common cases.** Templates handle the Dockerfile, ports,
  and volumes. You just pick a name and go.
- **Docker labels as state.** No local state files, no database. Docker
  itself is the source of truth.

## Current status

labctl is in active development. **MVP-0** (create, list, shell, destroy)
is complete and working. Templates, lifecycle commands, and VS Code
integration are next.

## Next steps

Head to the [Quickstart](quickstart.md) to install labctl and create
your first machine in under two minutes.
