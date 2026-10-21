"""Check logo provenance, shipped notices, complete routing, and text fallbacks."""

import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def check(theme):
    root = theme / 'assets/logos'
    catalog = json.loads((root / 'catalog.json').read_text())
    platforms = json.loads((theme / 'platforms.json').read_text())
    makers = {value['manufacturer'] for value in platforms.values()}
    assert catalog['schema_version'] == 1
    for kind, expected in [('platforms', set(platforms)), ('manufacturers', makers)]:
        assert not set(catalog[kind]) & set(catalog['fallbacks'][kind]), kind
        assert set(catalog[kind]) | set(catalog['fallbacks'][kind]) == expected, kind
        for entry in catalog[kind].values():
            path = root / entry['file']
            assert path.resolve().is_relative_to(root.resolve()), path
            data = path.read_bytes()
            assert hashlib.sha256(data).hexdigest() == entry['sha256'], path
            assert len(entry['source_sha256']) == 64, path
            assert entry['source'] in catalog['sources'], path
            assert '..' not in Path(entry['source_path']).parts, path
            svg = ET.fromstring(data)
            assert len(svg.get('viewBox', '').split()) == 4, path
            for element in svg.iter():
                assert element.tag.split('}')[-1] not in ('script', 'image', 'text', 'foreignObject'), path
                assert not any(k.split('}')[-1] == 'href' and not v.startswith('#')
                               for k, v in element.attrib.items()), path
    for source in catalog['sources'].values():
        assert len(source['revision']) == 40
        notice = root / source['notice']
        assert hashlib.sha256(notice.read_bytes()).hexdigest() == source['notice_sha256'], notice
    for key, info in platforms.items():
        variables = ET.parse(theme / 'palettes' / (key + '.xml')).find('variables')
        for prefix, kind, lookup in [('platform', 'platforms', key), ('manufacturer', 'manufacturers', info['manufacturer'])]:
            entry = catalog[kind].get(lookup)
            expected = '${themePath}/assets/logos/' + entry['file'] if entry else '${themePath}/assets/ui/white.svg'
            assert variables.findtext(prefix + 'Logo') == expected, (key, prefix)
            assert variables.findtext(prefix + 'LogoVisible') == str(bool(entry)).lower(), (key, prefix)
            assert variables.findtext(prefix + 'TextVisible') == str(not entry).lower(), (key, prefix)
    print(f"PASS: {len(catalog['platforms'])} platform logos, {len(catalog['manufacturers'])} manufacturer logos, source notices, hashes, and fallbacks")


if __name__ == '__main__':
    check(Path(sys.argv[1]))
