# Release downloads

Every PR runs theme, media, and packaging checks and uploads a preview artifact containing three files:

- `multi-pop-thor-rocknix-20261001.zip`: the installable theme, verified ARM64 frontend, licenses, bundled updater, and SHA-256 install manifest.
- `multi-pop-thor-source.zip`: the project sources plus the pinned public frontend source archive, SDL source, patches, and build-your-own instructions.
- `SHA256SUMS`: hashes of both downloads.

After a merge to `main`, the same workflow publishes these files as a GitHub Release tagged `build-<commit>`. Workflow runs on working branches cannot publish releases. Rerunning a published commit leaves the existing release intact. PR previews are retained for 30 days; merged releases remain available under [Releases](https://github.com/ballardcm/multi-pop-thor/releases).

## Verified frontend inputs

`frontend-build/release.json` selects a separate frontend release and pins the binary hash, firmware and frontend revisions, public source archives, and hashes of the frontend patches and compiler inputs. The separate frontend release is a maintainer input to packaging; users normally download the combined installable ZIP.

The initial frontend release is `frontend-rocknix-20261001-1`. Its assets are:

- `emulationstation-aarch64`
- `emulationstation-source-cada856d.tar.gz`
- `SDL2-2.32.10.tar.gz`
- `pugixml-source.tar.gz`

Packaging downloads those assets from this repository, checks their hashes, verifies ARM64 ELF identity, and checks the current compatibility report. The public upstream snapshot plus the current patches was checked against all 981 source files used for the tested frontend. Binary and source provenance remain separate from private integration configuration, runtime-library collections, and compiler caches.

Theme-only PRs reuse the verified frontend. A changed frontend patch or compiler input blocks packaging until a matching frontend is built, validated, and registered. This prevents a release from describing behavior its bundled binary does not implement.

## Refresh the frontend

Build from the [build-your-own instructions](../frontend-build/README.md), validate on the supported Thor firmware, and update the compatibility report with the actual binary hash and checks. Record the new public source archive hashes and build-input hashes in `frontend-build/release.json`; use a new frontend release tag rather than replacing assets under the old tag.

The corresponding frontend source and build support files must match the new binary. A different firmware needs a separately validated library set, descriptor, and installable asset name. Never mark the build as verified merely because compilation succeeded.

Register the candidate binary and matching source archives as a maintainer prerelease, and update the descriptor through a PR. Include the source commit in its notes. These inputs support PR previews; the combined user release is published only after the PR merges to main. The release workflow will then package that verified frontend. This maintainer action is required only when the frontend changes; ordinary theme, artwork, documentation, and tool PRs package automatically.

## Package locally

With all four frontend-input assets downloaded to `native-build/release-inputs`, run:

```sh
python3 \
  tools/package-release.py \
  --frontend native-build/release-inputs/emulationstation-aarch64 \
  --upstream-source native-build/release-inputs/emulationstation-source-cada856d.tar.gz \
  --sdl-source native-build/release-inputs/SDL2-2.32.10.tar.gz
```

Downloads are written under `dist/`. Packaging uses Git's tracked and nonignored source inventory; it rejects symlinks and keeps private files and compiled frontends out of the source ZIP. Fixed archive metadata makes repeated builds from the same inputs byte-identical. The ready-to-install ZIP conforms to the existing updater's archive contract.

GitHub's automatically generated repository source archives are still available, but they do not contain the frontend source snapshots added by our companion source ZIP. Use our named source ZIP when rebuilding a released frontend.
