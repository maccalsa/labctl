# DDEV Plan Review — Decision Tree & Open Questions

> Companion to `plan.md`. Tracks unresolved branches, hidden assumptions,
> and agreed decisions. Updated as branches are closed.

---

## Status Legend

| Tag | Meaning |
|-----|---------|
| `OPEN` | Unresolved — needs a decision |
| `AGREED` | Decision locked |
| `DEFERRED` | Explicitly punted with a trigger to revisit |

---

## Branch 1: Naming Collision — `AGREED`

**Issue:** "DDEV" is already a well-known open-source project
([ddev.readthedocs.io](https://ddev.readthedocs.io)) — a local PHP/Drupal
dev tool built on Docker. It has ~7k GitHub stars, active development, and
owns the `ddev` CLI command name.

**Impact:**
- Package name collision on PyPI / Homebrew / apt.
- SEO confusion — users will find the wrong project.
- Potential trademark / community friction.

**Recommendation:** Rename before writing any code. Candidates:
`devlab`, `labctl`, `machinedev`, `devmachine`, `labdev`. Pick something
that reinforces the "machine + lab" mental model from the spec.

**Depends on:** Nothing. This is a root decision — blocks packaging,
CLI entry point, docs, everything.

**Decision:** Rename to `labctl`. CLI command is `labctl`.
**Falsifies if:** Name collision discovered on PyPI/Homebrew, or user
testing reveals confusion with existing `kubectl`-style tooling.

---

## Branch 2: Container Runtime — `AGREED`

**Issue:** Plan lists "containerd (via nerdctl) OR Docker OR Podman"
behind an abstraction. But:

1. Which is the **primary target** for the MVP?
2. How deep is the abstraction? (Thin shim? Full interface with pluggable
   backends?)
3. Docker SDK for Python exists and is mature. nerdctl and Podman have no
   equivalent Python SDK — you'd shell out to their CLIs.

**Hidden assumption:** The plan treats these as interchangeable. They are
not — networking, volume semantics, and rootless behaviour differ
significantly.

**Recommendation:** MVP targets Docker only via the
[docker-py](https://docker-py.readthedocs.io/) SDK. Define a
`ContainerRuntime` protocol/interface from day one, but only implement the
Docker backend. Add nerdctl/Podman later behind the same interface.

**Depends on:** Nothing (root decision).

**Decision:** Docker only for MVP via `docker-py`. Define a
`ContainerRuntime` Protocol from day one (create, remove, list, start,
stop, exec, create_network, inspect, logs). Only implement `DockerRuntime`.
Podman/nerdctl are post-MVP behind the same interface.
**Falsifies if:** A significant chunk of the target audience doesn't
have Docker (e.g., Fedora users on Podman-only).

---

## Branch 3: Host OS Support — `AGREED`

**Issue:** Networking behaves fundamentally differently across:

- **Linux:** Docker runs natively. Containers are directly reachable from
  the host via bridge network IPs.
- **macOS / Windows:** Docker Desktop runs inside a Linux VM. Host cannot
  reach container IPs directly — only via published ports.

This means:
- `http://api-dev` from the host won't work on macOS without extra plumbing
  (e.g., `/etc/hosts` + port mapping, or a DNS proxy).
- `ssh python-dev` from the host also won't work without port publishing.

The spec's networking promise ("just use hostnames") is **only achievable
natively on Linux**. On macOS/Windows, it requires a host-side DNS
proxy or `/etc/hosts` manipulation plus port forwarding — which directly
contradicts the "zero complexity" goal.

**Recommendation:** Define clearly: are hostnames only resolvable
**between machines** (container-to-container), or also **from the host**?
If host-to-container, which OSes are in scope for MVP?

**Depends on:** Branch 2 (runtime choice affects networking model).

**Decision:** Linux + macOS for MVP. Windows deferred. Hostname resolution
is machine-to-machine only (Docker built-in DNS). Host-to-machine access
is via published ports discovered with `labctl ports <name>`. No host-side
DNS proxy or `/etc/hosts` manipulation.
**Falsifies if:** Users overwhelmingly demand host-to-container hostname
resolution, or Windows is a must-have for the target audience.

---

## Branch 4: DNS / Hostname Resolution Mechanism — `AGREED`

**Issue:** Plan says "internal DNS resolver" and "hostname-based routing"
but doesn't specify the mechanism.

Options:
1. **Docker's built-in DNS** — works container-to-container on user-defined
   networks. Free. Does NOT resolve from the host.
2. **Custom DNS container** (e.g., CoreDNS / dnsmasq sidecar) — more
   control, but adds an infrastructure dependency.
3. **`/etc/hosts` manipulation** on the host — fragile, requires root/sudo,
   platform-specific.
4. **mDNS / `.local` suffix** — conflicts with Avahi (Linux) and Bonjour
   (macOS). The `.local` TLD is reserved for mDNS (RFC 6762). Using it
   will cause resolution failures on systems with mDNS enabled.

**Hidden assumption:** The `.local` alias in the spec (`python-dev.local`)
will cause real problems. `.local` is not a free namespace.

**Recommendation:** Use Docker's built-in DNS for container-to-container
(free, reliable). Drop the `.local` suffix — use bare hostnames
(`python-dev`, `api-dev`). For host-to-container, defer to Branch 3's
decision.

**Depends on:** Branch 2, Branch 3.

**Decision:** Use Docker's built-in DNS on a user-defined network
(`labctl-net`). Bare hostnames only (`api-dev`, `db-dev`) — no `.local`
suffix (conflicts with mDNS / RFC 6762). No custom DNS container.
No `/etc/hosts` manipulation.
**Falsifies if:** A use case requires host-to-container name resolution
that can't be served by `labctl ports`.

---

## Branch 5: Port Mapping Strategy — `AGREED`

**Issue:** The spec says every machine exposes ports 80, 443, 22. But:

1. **Port conflicts:** You can't bind multiple containers to host port 80.
   The spec shows `localhost:49100` (dynamic ports) — but this contradicts
   "standard ports" and "zero cognitive load."
2. **Who publishes ports?** If hostnames work (Branch 4), containers don't
   need to publish ports for inter-machine traffic. But host access
   requires published ports.
3. **Port 22 / SSH:** If every container runs sshd and publishes port 22,
   you need unique host ports per machine. That's exactly the complexity
   the spec claims to eliminate.

**Recommendation:** Inter-machine traffic uses the Docker network (no port
publishing needed). Host access uses dynamic port mapping with a `ddev
ports` command to discover them. Don't promise "standard ports" — promise
"discoverable ports."

**Depends on:** Branch 3, Branch 4.

**Decision:** Inter-machine traffic uses the Docker network directly (no
port publishing). Host-to-machine uses template-defined container ports
mapped to dynamic host ports. `labctl ports <name>` discovers mappings.
`--port` flag overrides/supplements template defaults.
**Falsifies if:** Dynamic ports cause friction (e.g., tools that need
stable port numbers across restarts).

---

## Branch 6: SSH — Build or Drop for MVP? — `AGREED`

**Issue:** SSH is listed as MVP "must have," but it's non-trivial:

- Every template needs `sshd` installed and configured.
- Key generation + distribution per machine.
- Host-side SSH config management (`~/.ssh/config` entries).
- Port mapping per machine (see Branch 5).
- Security: auto-generated keys with no passphrase = risk if machines
  are exposed.

Meanwhile, `docker exec -it <name> /bin/bash` gives you a shell
instantly with zero setup. VS Code Remote Containers also doesn't use SSH —
it uses Docker exec under the hood.

**Question:** What user problem does SSH solve that `ddev shell <name>`
(wrapping `docker exec`) doesn't?

**Recommendation:** Replace SSH with `ddev shell <name>` for the MVP.
This removes sshd from images, eliminates key management, avoids port
conflicts, and works identically on all host OSes. Add SSH as a
later opt-in feature for users who need it (e.g., for tools that require
SSH transport).

**Depends on:** Nothing (but simplifies Branch 5 significantly).

**Decision:** Drop SSH from MVP. Replace with `labctl shell <name>`
wrapping `docker exec -it`. No sshd in images, no key management, no
port 22 conflicts. SSH becomes a post-MVP opt-in feature.
**Falsifies if:** A core use case emerges that strictly requires SSH
transport (e.g., IDE integration that can't use Docker exec).

---

## Branch 7: IDE Integration Mechanism — `AGREED`

**Issue:** `ddev ide open python-dev` "auto-detects editor" and opens the
container. But:

1. **VS Code Remote Containers** uses the Dev Containers extension, which
   needs a `devcontainer.json` either in the project or attached to the
   container. Opening is done via `code --remote` CLI.
2. **JetBrains Gateway** uses a completely different protocol (SSH or
   JetBrains-specific agent).
3. "Auto-detects editor" — by what mechanism? `$EDITOR`? Checking
   installed binaries? This is brittle.

**Hidden assumption:** The spec says "No manual devcontainer.json wiring"
but also says templates include `devcontainer.json`. These are in tension —
who writes the devcontainer.json, and where does it live?

**Recommendation:** MVP supports VS Code only via `code --remote
containers+<container-name> /workspace`. Skip JetBrains for now. Templates
include a `devcontainer.json` that ddev injects into the container at
create time. No auto-detection — explicit `ddev code <name>` command
that assumes VS Code.

**Depends on:** Branch 2 (runtime determines how VS Code attaches).

**Decision:** VS Code only for MVP via `labctl code <name>`. Runs
`code --remote containers+<container-id> /workspace`. Templates include
a `devcontainer.json` injected to `/workspace/.devcontainer/` at creation.
No editor auto-detection. JetBrains deferred. Clear error if VS Code
not found.
**Falsifies if:** Target users predominantly use JetBrains, or VS Code
drops/changes the `--remote` CLI interface.

---

## Branch 8: State Management — `AGREED`

**Issue:** State lives in `~/.ddev/machines/` etc. But:

1. **What's the source of truth?** The local state files, or the actual
   Docker state? These can drift (user runs `docker rm` directly).
2. **Format?** YAML, JSON, TOML, SQLite?
3. **Concurrency?** What if two `ddev` commands run simultaneously?
4. **What's stored?** Just machine names? Full config? Creation params
   for reproducibility?

**Recommendation:** Docker labels + container metadata *are* the source of
truth. Local state is a cache, rebuilt on demand by querying Docker.
Label containers with `ddev.machine=<name>`, `ddev.template=<template>`,
`ddev.network=ddev-net`, etc. This eliminates state drift entirely.

For config that can't be stored in labels (user preferences, defaults),
use a single `~/.ddev/config.toml`.

**Depends on:** Branch 2.

**Decision:** Docker is the source of truth. All labctl-managed containers
are labeled (`labctl.managed=true`, `labctl.machine=<name>`,
`labctl.template=<tpl>`, `labctl.network=labctl-net`). `labctl list`
queries Docker labels. No local machine state files. User preferences
only in `~/.labctl/config.toml`.
**Falsifies if:** Need to store metadata that can't fit in Docker labels
(e.g., complex machine relationships, lab groupings).

---

## Branch 9: Template Architecture — `AGREED`

**Issue:** Templates are "directories with Dockerfile + devcontainer.json
+ setup.sh." But:

1. **Where do they live?** Bundled in the Python package? `~/.ddev/templates/`?
   Downloaded from a registry?
2. **Are they user-customizable?** Can I add my own template?
3. **Versioning?** Templates evolve — how are updates shipped?
4. **What's in `setup.sh`?** Runs at build time or container start?
   What if it fails?

**Recommendation:** Ship built-in templates as package data inside the
Python package. Copy to `~/.ddev/templates/` on first run or `ddev init`.
Users can add custom templates to that directory. No remote registry for
MVP. `setup.sh` runs at container start (entrypoint wrapper), not build
time — keeps images cacheable.

**Depends on:** Branch 2, Branch 7 (devcontainer.json content).

**Decision:** Built-in templates ship as package data, copied to
`~/.labctl/templates/` on first use. Each template is a directory:
`Dockerfile`, `devcontainer.json`, `template.toml` (metadata: name,
description, default ports, default volumes). No `setup.sh` — all setup
goes in the Dockerfile. User-custom templates dropped into the same
directory. MVP ships 6 templates: `python`, `node`, `go`, `postgres`,
`redis`, `blank`. Templates versioned with the package — no remote
registry for MVP.
**Falsifies if:** Users need dynamic/parameterized templates (e.g.,
choosing Python version at create time) and static Dockerfiles can't
serve that.

---

## Branch 10: Language & Tooling — `AGREED`

**Issue:** The workspace is `python/ddev` (implying Python), but the plan
says "Go or Python + containerd/nerdctl."

**Tradeoffs:**

| | Python | Go |
|---|--------|------|
| Docker SDK | Excellent (`docker-py`) | Excellent (`docker/client`) |
| CLI framework | Click / Typer (great UX) | Cobra (industry standard) |
| Distribution | pip / pipx / brew | Single binary |
| Startup time | ~200ms (acceptable) | ~10ms (fast) |
| Target audience | Devs who use Python | Broader (ops, SRE) |

**Recommendation:** Python with Typer for the CLI. The `docker-py` SDK is
mature, the dev cycle is faster, and the workspace already signals Python.
Distribute via `pipx`. Single-binary distribution can come later via
PyInstaller / Nuitka if startup time matters.

**Depends on:** Nothing (root decision, but couples with Branch 2).

**Decision:** Python + Typer (CLI) + docker-py (runtime SDK). Distribute
via `pipx`. Package with `pyproject.toml` (modern Python packaging).
**Falsifies if:** docker-py can't support a needed runtime feature, or
startup latency exceeds ~500ms and becomes a UX issue.

---

## Branch 11: MVP Scope Reality Check — `AGREED`

**Issue:** The MVP "must have" list is:
- `create`, `list`, `destroy`
- shared network
- hostname resolution
- SSH access
- VS Code open

That's 6 significant features, several of which (SSH, hostname resolution,
VS Code integration) are individually non-trivial. An honest MVP timeline
for this scope is 4-8 weeks for a solo developer.

**Hidden assumption:** "Must have" implies all are needed for first usable
release. But a user can get value from just:
`create` + `list` + `destroy` + `shell` + shared network.

**Recommendation:** Slice the MVP into two phases:

**MVP-0 (1-2 weeks):** `create`, `list`, `destroy`, `shell` (via docker
exec), shared network (Docker user-defined network), container-to-container
hostname resolution (free with Docker DNS).

**MVP-1 (add 2-3 weeks):** VS Code integration, templates, `start`/`stop`,
`logs`, host-to-container discoverability (`ddev ports`).

Ship MVP-0 first. It's usable and validates the core "machine" abstraction.

**Depends on:** Branch 6 (SSH decision), Branch 7 (IDE decision).

**Decision:** Two-phase MVP.
**MVP-0 (tracer bullet, 1-2 weeks):** `create`, `list`, `destroy`,
`shell` — on `labctl-net` with Docker DNS. `blank` template only.
Docker labels as state. Proves the core "machine" abstraction.
**MVP-1 (flesh out, 2-3 weeks):** `code`, `ports`, `start`, `stop`,
`logs`. Full template set (python, node, go, postgres, redis, blank).
`~/.labctl/config.toml`.
**Falsifies if:** MVP-0 feedback reveals the machine abstraction
doesn't resonate without IDE integration or templates.

---

## Branch 12: Volume / Persistence Strategy — `AGREED`

**Issue:** The spec says machines are "disposable but reproducible."
The advanced example shows `--volume ./src:/app`. But:

1. **What's the default?** No volumes? A named Docker volume?
   A bind mount to CWD?
2. **Data persistence across destroy/create?** If I `ddev destroy db-dev`
   and recreate it, is my Postgres data gone?
3. **Working directory convention:** If I'm in `~/projects/myapp` and
   run `ddev create api-dev`, does it mount `~/projects/myapp` into the
   container?

**Recommendation:** Default: no bind mount (clean "machine"). Explicit
`--volume` flag for bind mounts. For data services (postgres, redis),
templates auto-create named Docker volumes so data survives
destroy/recreate. Document this clearly — "machines are disposable,
volumes are not."

**Depends on:** Branch 9 (template design determines volume defaults).

**Decision:** No bind mount by default — machines are clean slates.
User opts in via `--volume`. Data service templates (postgres, redis)
declare named volumes in `template.toml` (e.g.,
`labctl-<name>-data:/var/lib/postgresql/data`). Named volumes survive
destroy/recreate. `labctl destroy` warns about existing volumes;
`--volumes` flag deletes them. Dev templates (python, node, go, blank)
get no volumes by default.
**Falsifies if:** Majority of users expect auto-mounting CWD on create,
making the explicit flag too much friction.

---

## Branch 13: Security Model — `AGREED`

**Issue:** The spec doesn't define a security model. Questions:

1. Containers share a network — all ports are mutually visible. Acceptable?
2. SSH with auto-generated keys and no passphrase — what's the threat
   model? (These are local dev machines, so likely fine, but should be
   stated explicitly.)
3. Running as root inside containers? Or non-root by default?
4. Does ddev itself require root/sudo? (Docker group membership on
   Linux, Docker Desktop on macOS.)

**Recommendation:** State explicitly: "DDEV is a local development tool.
It assumes a trusted local environment. Containers run as root by default
(matching devcontainer convention). The Docker socket is required. No
security guarantees are made for exposed ports." This avoids scope creep
into hardening that doesn't serve the target user.

**Depends on:** Nothing.

**Decision:** Trusted local environment. Root in containers. Shared
network with full mutual visibility. Docker socket required. No
hardening for MVP. Document the posture in the README: "local dev tool,
do not expose to untrusted networks."
**Falsifies if:** Use case expands to shared/team environments where
isolation between developers' machines matters.

---

## Branch 14: "Lab" Concept — `DEFERRED`

**Issue:** The spec mentions `lab.yaml` export/import as "Later" but
references "dev lab" repeatedly as a core concept. There's no current
mechanism to group machines.

**Question:** Is a "lab" a first-class concept (named, with its own
lifecycle), or just a serialization format for a set of machines?

**Recommendation:** Defer the lab concept entirely from the MVP. For now,
all machines exist in a flat global namespace on the shared network. The
lab abstraction adds complexity (scoped networks? namespaced hostnames?
lab-level start/stop?) that should be designed after the core is proven.

**Depends on:** Branch 11 (MVP scope).

**Decision:** Deferred entirely from MVP. All machines live in a flat
global namespace on `labctl-net`. Revisit after core machine lifecycle
is proven.
**Falsifies if:** Users immediately ask "how do I group these?" or need
isolated networks per project.

---

## Dependency Graph

```
Branch 1 (Naming)          ← blocks everything external (packaging, docs)
Branch 2 (Runtime)         ← root technical decision
  ├── Branch 3 (Host OS)
  │     ├── Branch 4 (DNS)
  │     │     └── Branch 5 (Ports)
  │     └── Branch 7 (IDE)
  ├── Branch 8 (State)
  └── Branch 9 (Templates)
        └── Branch 12 (Volumes)
Branch 6 (SSH)             ← independent, simplifies 5 and 11
Branch 10 (Language)       ← root, couples with 2
Branch 11 (MVP Scope)      ← depends on 6, 7
Branch 13 (Security)       ← independent
Branch 14 (Lab Concept)    ← depends on 11
```

---

## Resolution Order (Recommended)

1. **Branch 1** — Naming (unblocks everything public-facing)
2. **Branch 10** — Language/tooling (unblocks implementation)
3. **Branch 2** — Container runtime (root technical decision)
4. **Branch 6** — SSH: build or drop (simplifies downstream)
5. **Branch 3** — Host OS scope
6. **Branch 4** — DNS mechanism
7. **Branch 5** — Port strategy
8. **Branch 8** — State management
9. **Branch 7** — IDE integration
10. **Branch 9** — Template architecture
11. **Branch 12** — Volume strategy
12. **Branch 13** — Security model
13. **Branch 11** — MVP scope (confirm after above decisions)
14. **Branch 14** — Lab concept (defer or define)
