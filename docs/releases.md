# Release downloads

Every PR runs theme, media, and packaging checks and uploads a preview artifact containing three files:

- `multi-pop-thor-rocknix-20261001.zip`: the installable theme, verified ARM64 frontend, licenses, bundled updater, and SHA-256 install manifest.
- `multi-pop-thor-source.zip`: the project sources plus the pinned public frontend source archive, SDL source, patches, and build-your-own instructions.
- `SHA256SUMS`: hashes of both downloads.

Merging a PR does not publish anything. Releases are published manually from the reviewed default branch and use a date label such as **10.21.26.1**: month, day, two-digit year, and that day's release revision. `release-version.json` records the local date (America/Los_Angeles) and revision. Start a new date at 1 and increment the revision for additional releases that day. Coordinate the same label in Thor and RG DS when shipping them together. The first release under this scheme is 10.21.26.1.

The workflow retains immutable `build-<commit>` tags for updater compatibility, titles the release with the date label, and refuses to publish the same label under a different commit. The installable theme displays the label in Theme Configuration and its lower header. `version.json` also carries an integer ordering value for old updaters; this implementation detail is not the user-facing version. Packaging derives it deterministically from the full date and daily revision, making it newer than legacy Thor and RG DS releases.

PR previews are retained for 30 days and contain the configured upcoming date release. Published releases stay under [Releases](https://github.com/ballardcm/multi-pop-thor/releases). The source revision and archive checksums identify the exact build independently of its display label.

## Publish a release

Once everything meant for the release is merged, start the workflow on `main`:

```sh
gh workflow run release.yml \
  --repo ballardcm/multi-pop-thor \
  --ref main
```

Publishing reaches every Thor with Automatic updates turned on within about six hours, so test the last PR preview on a device before running it.

## Verified frontend inputs

`frontend-build/release.json` selects a separate frontend release and pins the binary hash, firmware and frontend revisions, public source archives, and hashes of the frontend patches and compiler inputs. The separate frontend release is a maintainer input to packaging; users normally download the combined installable ZIP.

The current frontend release is `frontend-rocknix-20261001-5`. The binaries from `-1` and `-2` were withdrawn because they had service keys compiled in; their source archives remain. Each release's assets are:

- `emulationstation-aarch64`
- `emulationstation-source-cada856d.tar.gz`
- `SDL2-2.32.10.tar.gz`
- `pugixml-source.tar.gz`

Packaging downloads those assets from this repository, checks their hashes, verifies ARM64 ELF identity, and checks the current compatibility report. The public upstream snapshot plus the current patches was checked against all 981 source files used for the tested frontend. Binary and source provenance remain separate from runtime-library collections and compiler caches. Frontend binaries contain no online-service keys; each Thor generates its own `integration.env` at activation.

Theme-only PRs reuse the verified frontend. A changed frontend patch or compiler input blocks packaging until a matching frontend is built, validated, and registered. This prevents a release from describing behavior its bundled binary does not implement.

## Refresh the frontend

Build from the [build-your-own instructions](../frontend-build/README.md), validate on the supported Thor firmware, and update the compatibility report with the actual binary hash and checks. Record the new public source archive hashes and build-input hashes in `frontend-build/release.json`; use a new frontend release tag rather than replacing assets under the old tag.

The corresponding frontend source and build support files must match the new binary. A different firmware needs a separately validated library set, descriptor, and installable asset name. Never mark the build as verified merely because compilation succeeded.

Register the candidate binary and matching source archives as a maintainer prerelease, and update the descriptor through a PR. Include the source commit in its notes. These inputs support PR previews; the combined user release is published only by a [manual run on main](#publish-a-release) after the PR merges. That run packages the verified frontend. This maintainer action is required only when the frontend changes; ordinary theme, artwork, documentation, and tool PRs package automatically.

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
