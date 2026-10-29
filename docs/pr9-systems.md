# Additional system mappings

These systems were contributed to Multi Pop RG DS in [PR #9](https://github.com/ballardcm/multi-pop-rgds/pull/9) and ported here. The theme values were checked against `SYSTEM_THEME` in `config/emulators/*.conf` at the ROCKNIX `20261001` tag, the firmware this theme supports, but not yet against `es_systems.cfg` on an AYN Thor; whether a system appears on Thor also depends on which emulators ROCKNIX builds for that device. The palette filename is an internal asset name; the include condition must match the firmware’s theme value.

| ROCKNIX theme | Palette |
| --- | --- |
| channelf | channelf |
| odyssey2 | odyssey |
| fds | fds |
| msx2 | msx2 |
| megacd | megacd |
| supervision | supervision |
| scv | scv |
| megaduck | megaduck |
| n64dd | n64dd |
| pokemini | pokemini |
| doom | doom |
| tic80 | tic-80 |
| wasm4 | wasm4 |

Supervision is the Watara system; Super Cassette Vision is the separate Epoch system. Odyssey² and TIC-80 intentionally use palette filenames that differ from the firmware theme values.

The system illustrations and SVG logos are byte-identical to the RG DS theme. The cards and hero panels were regenerated with `tools/build-multi-pop-art.py`, so they carry the Thor label. Artwork credit and AI provenance are recorded in the project and installable READMEs and `multi-pop-thor/LICENSING.md`. The port was prepared with AI assistance (Claude Code).
