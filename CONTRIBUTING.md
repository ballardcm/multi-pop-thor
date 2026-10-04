# Contributing to Multi Pop

Pull requests are welcome for layouts, artwork, compatibility fixes, tools, and documentation. For a larger change, open an issue first so we can agree on its scope.

Create a branch and send a PR rather than pushing to `main`. GitHub protects `main`, including maintainer changes, and requires the packaging check to pass. PR previews let us test on a Thor before merging; merged changes receive an installable download and matching source download automatically.

Explain what changed and why, and describe your checks. Run `python3 tools/check-multi-pop.py`, `python3 tools/test-install-multi-pop-media.py`, and `python3 tools/test-package-release.py`. For device tests, include the hardware and firmware version and the behavior you checked. Frontend changes need a matching verified binary; see [release maintenance](docs/releases.md).

Keep ROMs, downloaded game media, credentials, personal device configuration, and local build caches out of the PR. Include editable sources for artwork and disclose AI assistance where relevant. Contributions to original Multi Pop material use the project's CC BY-NC-SA 4.0 terms; third-party components retain the exceptions in [LICENSING.md](multi-pop-thor/LICENSING.md).
