# General Rules

Binding on engine code, agent roles, and every run.

1. Inspect the environment before changing anything.
2. Never destroy existing user data.
3. Never overwrite an existing project without explicit evidence it belongs to this run.
4. Prefer simple, local, open-source tooling.
5. Do not install unnecessary infrastructure.
6. No Kubernetes, Docker, databases, RAG systems, multi-agent frameworks, or cloud infrastructure unless a concrete requirement demonstrates necessity.
7. Every significant operation must be reproducible.
8. Maintain an audit log.
9. Keep configuration separate from source code.
10. Fail closed rather than pretending success.
11. Never conflate an inference-call failure (timeout, throttling, rate limit, malformed response) with a verification failure. Log and handle as distinct failure classes.
12. Never let an autonomous retry loop consume unbounded inference quota. Cost/call budgets are as mandatory as retry-count budgets.
13. Never add a paid dependency, tier, or second model until an observed, logged constraint demonstrates the current one is insufficient. No pre-provisioning.
14. A test-count floor (Phase 8B) is a floor paired with a mandatory anti-triviality check, never a count to satisfy with shallow or duplicate tests. Count without genuine coverage does not satisfy this system's definition of done.

## Scope boundary (state to every client)

This engine verifies **TENCHNICAL FEASIBILITY** and produces a live GTM v1 surface. It does **NOT** verify market demand, business viability, legal compliance, or commercial success. "Verified" means "evidence-backed, working, live software," not "validated business." Never let RELEASE language imply otherwise.
