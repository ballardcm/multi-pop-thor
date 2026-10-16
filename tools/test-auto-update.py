#!/usr/bin/env python3
"""Exercise the Thor auto-updater against a local stand-in for GitHub and the frontend API."""

import hashlib
import http.server
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('auto_update', ROOT / 'multi-pop-thor/scripts/auto_update.py')
auto_update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auto_update)

FIRMWARE = 'firmware-a'
TAG = 'build-0123456789ab'


def theme_files(version, firmware=FIRMWARE):
    return {
        'theme.xml': ('<theme version="' + version + '"/>').encode(),
        'frontend/emulationstation': b'\x7fELF frontend ' + version.encode(),
        'frontend/compatibility.json': json.dumps({'firmware_revision': firmware}).encode(),
        'scripts/start_es_thor.sh': b'#!/bin/bash\n',
    }


def archive_bytes(files):
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for name, data in files.items():
            archive.writestr('multi-pop-thor/' + name, data)
        archive.writestr('install-manifest.json', json.dumps(manifest))
    return output.getvalue()


class Server(http.server.ThreadingHTTPServer):
    def __init__(self):
        super().__init__(('127.0.0.1', 0), Handler)
        self.routes = {}
        self.requests = []
        self.notifications = []


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append(self.path)
        body = self.server.routes.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.server.notifications.append(self.rfile.read(int(self.headers['Content-Length'])).decode())
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


class AutoUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.server = Server()
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        base = 'http://127.0.0.1:%d' % self.server.server_address[1]
        self.themes = root / 'roms/themes'
        self.config = auto_update.Config(
            theme=self.themes / 'multi-pop-thor', state=root / 'storage/.config/multi-pop-thor',
            release_api=base + '/release', frontend_api=base, frontend_wait=2,
            installer=ROOT / 'tools/install-multi-pop-theme.py')
        for name, data in theme_files('old').items():
            path = self.config.theme / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.server.routes['/runningGame'] = b'{"msg":"NO GAME RUNNING"}'
        self.publish(theme_files('new'))

    def publish(self, files, tag=TAG, sums_override=None):
        archive = archive_bytes(files)
        name = 'multi-pop-thor-rocknix-20261001.zip'
        digest = sums_override or hashlib.sha256(archive).hexdigest()
        base = 'http://127.0.0.1:%d' % self.server.server_address[1]
        self.server.routes.update({
            '/release': json.dumps({'tag_name': tag, 'assets': [
                {'name': name, 'browser_download_url': base + '/zip'},
                {'name': 'SHA256SUMS', 'browser_download_url': base + '/sums'}]}).encode(),
            '/zip': archive,
            '/sums': (digest + '  ' + name + '\n').encode(),
        })

    def installed_theme(self):
        return (self.config.theme / 'theme.xml').read_text()

    def updates(self, name):
        return auto_update.read_json(self.config.updates / name)

    def test_stage_apply_and_confirm(self):
        auto_update.background(self.config)
        self.assertEqual(self.updates('staged.json')['tag'], TAG)
        self.assertIn('installs the next time', self.server.notifications[0])
        self.assertIn('old', self.installed_theme())
        auto_update.apply(self.config)
        self.assertIn('new', self.installed_theme())
        self.assertIsNone(self.updates('staged.json'))
        backup = Path(self.updates('pending.json')['backup'])
        self.assertIn('old', (backup / 'theme.xml').read_text())
        (self.config.updates / 'last-check').unlink()
        auto_update.background(self.config)
        self.assertEqual(self.updates('installed.json')['tag'], TAG)
        self.assertIsNone(self.updates('pending.json'))
        self.assertTrue(backup.is_dir())
        self.assertEqual(self.server.requests.count('/zip'), 1)

    def test_archive_not_matching_its_checksum_is_never_staged(self):
        self.publish(theme_files('new'), sums_override='0' * 64)
        auto_update.background(self.config)
        self.assertIsNone(self.updates('staged.json'))
        self.assertIn('does not match SHA256SUMS', (self.config.updates / 'auto-update.log').read_text())

    def test_release_for_other_firmware_is_skipped(self):
        self.publish(theme_files('new', firmware='firmware-b'))
        auto_update.background(self.config)
        self.assertIsNone(self.updates('staged.json'))
        self.assertEqual(self.updates('rejected.json'), [TAG])

    def test_matching_installation_is_recorded_without_staging(self):
        self.publish(theme_files('old'))
        auto_update.background(self.config)
        self.assertIsNone(self.updates('staged.json'))
        self.assertEqual(self.updates('installed.json')['tag'], TAG)

    def test_unconfirmed_update_rolls_back_and_is_skipped(self):
        auto_update.background(self.config)
        auto_update.apply(self.config)
        # The new frontend never answers, so each restart counts as a failed start.
        for start in range(auto_update.FAILED_STARTS_BEFORE_ROLLBACK + 1):
            auto_update.apply(self.config)
        self.assertIn('old', self.installed_theme())
        self.assertIsNone(self.updates('pending.json'))
        self.assertEqual(self.updates('rejected.json'), [TAG])
        self.assertTrue((self.themes / ('.multi-pop-failed-' + TAG)).is_dir())
        (self.config.updates / 'last-check').unlink()
        auto_update.background(self.config)
        self.assertIsNone(self.updates('staged.json'))

    def test_disabled_updates_do_not_check(self):
        (self.config.state / 'auto-update-disabled').parent.mkdir(parents=True, exist_ok=True)
        (self.config.state / 'auto-update-disabled').touch()
        auto_update.background(self.config)
        self.assertNotIn('/release', self.server.requests)

    def test_checks_are_rate_limited(self):
        self.publish(theme_files('old'))
        auto_update.background(self.config)
        auto_update.background(self.config)
        self.assertEqual(self.server.requests.count('/release'), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
