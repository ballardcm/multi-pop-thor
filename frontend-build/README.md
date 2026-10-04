# Optional frontend build notes

The tested Thor frontend derives from [ROCKNIX/emulationstation](https://github.com/ROCKNIX/emulationstation), revision `cada856d86e3115fbbf0bce09dd761b0ee8fa9fd`, for ROCKNIX firmware revision `c445081a59518f37d9776e5412dd7b14910696f7` (20261001). The public changes are in [`../multi-pop-thor/frontend/thor-popup-placement.patch`](../multi-pop-thor/frontend/thor-popup-placement.patch) and [`../multi-pop-thor/frontend/thor-game-paging.patch`](../multi-pop-thor/frontend/thor-game-paging.patch).

Apply those patches to an unmodified checkout of that exact source revision. The retained Dockerfile and build scripts are reference support for an ARM64 Ubuntu 22.04 build. They expect the public upstream source under `/work/emulationstation-next-cada856d86e3115fbbf0bce09dd761b0ee8fa9fd`, matching ROCKNIX libraries under `/work/private/target-libs`, and public SDL 2.32.10 headers under `/work/private/SDL2-headers`. Those inputs and compiler output are deliberately untracked.

`read-target-libs.py` collects the target's shared libraries when run on the Thor. `collect-local-target-symbols.py` and `verify-artifact.sh` support dependency and loader checks in the build container. A finished binary belongs at `multi-pop-thor/frontend/emulationstation`, which Git ignores. Retain the frontend license notices alongside a locally built binary.

These files are not a complete release build workflow. Runtime collection, source acquisition, public header setup, patch application, container invocation, and validation still need to be made reproducible. The tested firmware build preserves bundled compile-time online-service credentials. Those values and scripts that copy them are excluded from this repository. Public-source builds alone do not reproduce its online-service configuration.

Use the shipped compatibility report as a record of the tested local frontend, not as certification of a new build. Check native library resolution, strong imported symbols, absence of added RPATH, controller mappings, both display positions, and actual device behavior before replacing the frontend.

The theme identifier is now `multi-pop-thor`. Apply the current paging patch when building the frontend so L1/R1 paging recognizes that identifier. The compatibility report records the renamed binary's hash and native checks. The earlier paging input harness results are retained separately; physical controller feedback on the renamed build is pending.
