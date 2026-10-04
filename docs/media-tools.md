# Separate game media tooling

The theme displays library media but does not ship it. These retained tools support a separate media workflow:

- `tools/fetch-color-pop-screenshots.py` stages public Libretro screenshots from an explicitly supplied library inventory. Its title matching stays within the selected system; optional local alias manifests must have provenance. It needs Pillow.
- `tools/package-color-pop-media.py` packages matching screenshot and metadata reports, and accepts video records only from a separately verified video manifest and exact-title candidate lists. It expects a local `color-pop-media-inventory.json` and `color-pop-media-staging/`; those files contain library details and are ignored by Git.
- `tools/install-color-pop-media.py` validates the manifest and assets and defaults to a dry run. Its bulk XML mode backs up game lists, preserves existing covers and user fields, stops the idle frontend for the merge, and restarts it afterward. Run this tool on the Thor.
- `tools/test-install-color-pop-media.py` exercises preservation and concurrency behavior with isolated fixtures: `python3 tools/test-install-color-pop-media.py`.

Use the bulk XML mode for persistent installation. Native API imports were visible during the earlier session but did not persist after the frontend restarted. The API modes remain in the source as historical implementation work; they need that saving issue resolved before use.

Metadata acquisition, video acquisition, visual video review, and device inventory generation have not yet been assembled into a complete reusable workflow here. Reports, ROM lists, media files, remote-device addresses, credentials, and backups are excluded. Preserve provider and creator credits with any independently acquired media.
