# Sidebar logo acknowledgments and source record

Thank you to **HVR88**, **Rookervik**, **Nils Bonenberger**, the **RetroPie Carbon contributors**, and the original brand designers. This theme benefits from their work; it does not claim to have created these identities.

## HVR88's Monochrome Gaming Logos

[Monochrome (Retro) Gaming Logos](https://github.com/HVR88/Monochrome-Gaming-Logos) supplies most of the platform marks and all manufacturer marks in this catalog. HVR88 built the collection to support [Pegasus Frontend](https://pegasus-frontend.org/) and [PlayingKarrde's GameOS](https://github.com/PlayingKarrde/gameOS). Please explore those projects and consider contributing, helping their maintainers, or spreading the word.

The creator expressly permits use in collections and projects and asks for a note and link back. The [unmodified upstream readme](notices/monochrome-README.md) preserves that permission, the attribution request, and its third-party copyright/trademark disclaimer. The repository does not supply a conventional blanket license; we do not invent one or relicense the underlying brand marks as Multi Pop originals.

## RetroPie Carbon

[Carbon](https://github.com/RetroPie/es-theme-carbon), by Rookervik and contributors and based on Nils Bonenberger's Simple theme, supplies the NES, Game Boy Color, and Master System wordmarks. The [unmodified Carbon readme](notices/carbon-readme.txt) retains its full attribution and terms. Its heading names CC BY-NC-SA 2.0 while its included public-license text names 4.0; both are preserved verbatim rather than silently corrected. Carbon separately reserves its used logos and trademarks to their respective owners. Our adaptations remain noncommercial and share-alike to the extent those licensed rights apply, without claiming rights in the brands themselves.

[Fabrice Caruso’s expanded Carbon collection](https://github.com/fabricecaruso/es-theme-carbon) supplies the FinalBurn Neo phoenix wordmark. Its [original source notice](notices/carbon-fbneo-readme.txt) is also retained, with the exact revision and file hash in the catalog. Credit belongs to that project’s contributors and the original FBNeo identity owners.

## What Multi Pop changes

SVG geometry is retained, paint is normalized to white for the frontend's palette tint, and embedded descriptive metadata is removed from the renderable assets while source provenance is retained in [catalog.json](catalog.json). The Master System wordmark is isolated from Carbon's combined Sega/Master System mark, retaining ancestor transforms; Sega appears separately as the manufacturer. The builder does not rasterize, trace, or invent brand marks. Display scaling preserves aspect ratio.

Every file has a source repository, pinned commit, source path, source SHA-256, transform name, and generated SHA-256. Source notices also have recorded hashes. Original source downloads stay outside Git. Rebuild from a cache with:

```sh
python3 tools/build-multi-pop-logos.py --cache /tmp/multi-pop-logo-sources --fetch
python3 tools/build-multi-pop-art.py --palettes-only
```

Run these commands from the source repository. `--record-hashes` is reserved for intentional asset curation and review, not routine builds.

## Coverage and fallbacks

The initial catalog has 60 platform marks and 14 manufacturer marks. Text remains for generic collections/categories, and manufacturers with no suitable standalone mark in these sources: Panasonic, GCE, and Lexaloffle. All decisions are listed in the catalog's `fallbacks` section. Blank collection years stay blank, and uncommon/custom systems retain the default text layout.

The Nintendo, Sega, Sony, Atari, and other names and marks are used for identification. No affiliation, endorsement, or transfer of trademark rights is claimed. AI assistance with selection, integration, and verification does not make this third-party logo artwork AI-generated Multi Pop material.
