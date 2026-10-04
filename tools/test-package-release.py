#!/usr/bin/env python3
"""Exercise release integrity gates and the installer's archive contract."""

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zipfile


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load('release', 'package-release.py')
installer = load('installer', 'install-multi-pop-theme.py')


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='multi-pop-release-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        files = {'.gitignore': 'private/\ndist/\n', 'multi-pop-thor/theme.xml': '<theme/>',
                 'multi-pop-thor/README.md': 'Install instructions', 'multi-pop-thor/LICENSE': 'License',
                 'multi-pop-thor/LICENSING.md': 'Scope', 'multi-pop-thor/scripts/start_es_thor.sh': '#!/bin/sh\n',
                 'multi-pop-thor/frontend/test.patch': 'The verified patch', 'private/secret.env': 'Must not ship'}
        files['tools/install-multi-pop-theme.py'] = Path(__file__).with_name('install-multi-pop-theme.py').read_text()
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        private = self.root / 'private'
        self.binary = private / 'emulationstation'
        header = bytearray(64)
        header[:6] = b'\x7fELF\x02\x01'
        struct.pack_into('<H', header, 18, 183)
        self.binary.write_bytes(header)
        self.upstream = private / 'upstream.tar.gz'
        self.sdl = private / 'SDL2.tar.gz'
        self.upstream.write_bytes(b'Fixture source archive')
        self.sdl.write_bytes(b'Fixture SDL archive')
        self.pugixml = private / 'pugixml-source.tar.gz'
        self.pugixml.write_bytes(b'Fixture pugixml archive')
        self.config = {'frontend_revision': 'source-revision', 'firmware_revision': 'firmware-revision',
                       'firmware_version': '20261001', 'frontend': {'sha256': release.sha256(self.binary)},
                       'upstream_source': {'sha256': release.sha256(self.upstream)},
                       'sdl_source': {'sha256': release.sha256(self.sdl)},
                       'pugixml_source': {'asset': self.pugixml.name, 'sha256': release.sha256(self.pugixml)},
                       'build_inputs': {'multi-pop-thor/frontend/test.patch': release.sha256(self.root / 'multi-pop-thor/frontend/test.patch')}}
        (self.root / 'frontend-build').mkdir()
        (self.root / 'frontend-build/release.json').write_text(json.dumps(self.config))
        report = {'artifact_sha256': release.sha256(self.binary), 'frontend_revision': 'source-revision', 'firmware_revision': 'firmware-revision'}
        (self.root / 'multi-pop-thor/frontend/compatibility.json').write_text(json.dumps(report))

    def package(self):
        return release.package(self.root, self.root / 'dist', self.binary, self.upstream, self.sdl)

    def test_install_contract_and_private_exclusion(self):
        ready, source, sums = self.package()
        with zipfile.ZipFile(ready) as archive:
            manifest = installer.read_manifest(archive)
            for name, digest in manifest.items():
                self.assertEqual(hashlib.sha256(archive.read('multi-pop-thor/' + name)).hexdigest(), digest)
            self.assertEqual((archive.getinfo('multi-pop-thor/frontend/emulationstation').external_attr >> 16) & 0o777, 0o755)
        with zipfile.ZipFile(source) as archive:
            self.assertFalse(any('private/' in name for name in archive.namelist()))
            self.assertFalse(any(name.endswith('/emulationstation') for name in archive.namelist()))
            self.assertIn('multi-pop-thor-source/frontend-build/upstream-source.tar.gz', archive.namelist())
            self.assertEqual(archive.read('multi-pop-thor-source/frontend-build/pugixml-source.tar.gz'), self.pugixml.read_bytes())
        self.assertIn(release.sha256(ready), sums.read_text())

    def test_modified_binary_is_rejected(self):
        self.binary.write_bytes(self.binary.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'Frontend checksum'):
            self.package()

    def test_stale_frontend_after_patch_change_is_rejected(self):
        (self.root / 'multi-pop-thor/frontend/test.patch').write_text('New behavior without a new binary')
        with self.assertRaisesRegex(ValueError, 'build input changed'):
            self.package()

    def test_substituted_source_is_rejected(self):
        self.upstream.write_bytes(b'Different source')
        with self.assertRaisesRegex(ValueError, 'Source archive checksum'):
            self.package()

    def test_substituted_submodule_is_rejected(self):
        self.pugixml.write_bytes(b'Different submodule source')
        with self.assertRaisesRegex(ValueError, 'Source archive checksum'):
            self.package()

    def test_symlink_cannot_import_outside_file(self):
        (self.root / 'multi-pop-thor/external.txt').symlink_to(self.root / 'private/secret.env')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            self.package()

    def test_repeated_packages_are_identical(self):
        first = {path.name: path.read_bytes() for path in self.package()}
        second = {path.name: path.read_bytes() for path in self.package()}
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main(verbosity=2)
