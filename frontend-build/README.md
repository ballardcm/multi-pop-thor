# Build your own frontend

Normal installation uses the ready-to-install ZIP from [Releases](https://github.com/ballardcm/multi-pop-thor/releases); it already contains the patched frontend. These instructions are for rebuilding or modifying that frontend.

The supported target is **AYN Thor running ROCKNIX 20261001**, firmware revision `c445081a59518f37d9776e5412dd7b14910696f7`. The frontend source is [ROCKNIX/emulationstation-next](https://github.com/ROCKNIX/emulationstation-next), revision `cada856d86e3115fbbf0bce09dd761b0ee8fa9fd`, with the popup and navigation patches in `multi-pop-thor/frontend/`. Source archive checksums are pinned in `frontend-build/release.json`.

## Requirements

Use Python 3.9 or newer, OpenSSH, the `patch` command, and Docker with Linux ARM64 support. ARM Macs can run the builder natively; an x86 host needs Docker's ARM64 emulation configured. The Thor must be reachable through SSH with key authentication and have Python 3 and `readelf` available. Keep the device on the supported firmware while collecting its libraries.

On macOS, missing Python and patch can be installed with `brew install python patch`; Docker Desktop can be installed with `brew install --cask docker`. On Arch, the corresponding packages are `sudo pacman -S python openssh patch docker`. Start Docker and verify that your account can use it before building.

Extract `multi-pop-thor-source.zip` and open a terminal in its `multi-pop-thor-source` directory, or use a Git checkout. The source ZIP includes the pinned public frontend snapshot, its pinned pugixml submodule, and SDL 2.32.10 source; a Git checkout downloads those same inputs and checks their hashes.

## Build

From the repository or extracted source root, replace `THOR_IP` with the device's address:

```sh
python3 \
  frontend-build/build.py \
  --target root@THOR_IP
```

To reuse an open SSH connection, add its control socket:

```sh
python3 \
  frontend-build/build.py \
  --target root@THOR_IP \
  --ssh-option ControlPath=/path/to/thor-ssh-socket
```

The script checks source hashes, applies both patches, collects the matching runtime libraries from the Thor, builds the ARM64 Docker image, and compiles with network access disabled. It then checks the ELF metadata, target loader, and help command. The result is copied to `multi-pop-thor/frontend/emulationstation`; an adjacent `.build.json` records its hash and the checks performed. The build log defaults to `~/multi-pop-frontend-build.log`.

Public-source builds do not automatically reproduce ROCKNIX's compile-time online-service configuration. If you have upstream-authorized settings, an optional `--integration-env /path/to/local.env` supplies them through Docker's environment-file mechanism. The supported ready-to-install frontend preserves the tested firmware's existing integrations. Do not put local integration settings in Git or the source download.

Build inputs and compiler files stay under `frontend-build/private/build-your-own`. A second build must use a new `--work` directory so stale source or library inputs cannot be reused accidentally. Docker's build context excludes that private storage.

## Validate and distribute

The scripts check native dependencies and startup support; they do not certify controller behavior or a different firmware version. Verify both display positions, B navigation, savestates, L1/R1 paging, audio/video, controller mappings, and the integrations you use on the actual Thor before distributing a new frontend. For the touch candidate, also check swipes in both directions and tap selection in both carousels, small finger jitter, vertical drags, wake from sleep, opening a menu during a gesture, and the Disable Touchscreen setting. Confirm that Sway maps the lower touchscreen to DSI-1 and reports its events as enabled after activation and after reboot before evaluating the gesture thresholds. Run `python3 tools/test-thor-touch.py` for the local gesture regression checks.

Retain all frontend license notices. Ready-to-install releases must be accompanied by the matching public frontend source, patches, and build support files. Our source ZIP includes those materials together; firmware runtime libraries are collected locally and are not bundled in either download.

Changing a frontend patch does not silently reuse the old binary. [Release maintenance](../docs/releases.md) describes how to validate and register its replacement for PR packaging.
