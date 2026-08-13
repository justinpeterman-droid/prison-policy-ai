# Software Supply Chain

Developer dependencies are generated with `pip-compile --generate-hashes --allow-unsafe --resolver=backtracking --output-file=requirements-dev.lock requirements-dev.in` and installed only with `python -m pip install --require-hashes --requirement requirements-dev.lock`. Review every dependency and hash update in code review.

The runtime is the approved immutable Chainguard Python 3.14 digest. The container gate verifies its SBOM, signature/provenance evidence, and rejects fixable Critical or High findings before release. No build or artifact is pushed from local verification.
