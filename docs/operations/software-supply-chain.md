# Software Supply Chain

Developer dependencies are generated with `pip-compile --generate-hashes --allow-unsafe --resolver=backtracking --output-file=requirements-dev.lock requirements-dev.in` and installed only with `python -m pip install --require-hashes --requirement requirements-dev.lock`. Review every dependency and hash update in code review.

The runtime is the approved immutable Chainguard Python 3.14 digest. The container gate verifies its SBOM, signature/provenance evidence, and rejects fixable Critical or High findings before release. No build or artifact is pushed from local verification.

The `postgres-integration-17` status name is retained as the compatibility floor: it uses the immutable PostgreSQL 17 official manifest digest for application integration tests. Cloud SQL production configuration uses PostgreSQL 18 because the infrastructure security baseline requires that supported major version. The database compatibility contract is PostgreSQL 17-or-newer; tests must remain compatible with the named 17 floor while migrations and production validation also cover Cloud SQL PostgreSQL 18 before rollout.
