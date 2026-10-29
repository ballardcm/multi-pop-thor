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
TAG = 'thor-10.28.26.2'
ARCHIVE = 'multi-pop-thor-rocknix-20261001.zip'


def theme_files(version, firmware=FIRMWARE, number=None):
    number = {'old': 1, 'new': 2}.get(version, 3) if number is None else number
    return {
        'theme.xml': ('<theme version="' + version + '"/>').encode(),
        'version.json': json.dumps({'version': number}).encode(),
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
        # A route may carry the Link header GitHub uses to point at the next page of releases.
        if isinstance(body, tuple):
            body, link = body
            self.send_header('Link', link)
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
            release_api=base + '/release', frontend_api=base, frontend_wait=2, notify_delay=0,
            installer=ROOT / 'tools/install-multi-pop-theme.py', es_settings=root / 'es_settings.cfg')
        self.set_updates('on')
        for name, data in theme_files('old').items():
            path = self.config.theme / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.server.routes['/runningGame'] = b'{"msg":"NO GAME RUNNING"}'
        self.server.routes['/isIdle'] = b'[ true ]'
        self.publish(theme_files('new'))

    def set_updates(self, value):
        settings = '<?xml version="1.0"?>\n<config>\n\t<string name="ThemeSet" value="multi-pop-thor" />\n'
        if value is not None:
            settings += '\t<string name="subset.autoupdate" value="' + value + '" />\n'
        self.config.es_settings.write_text(settings + '</config>\n')

    @property
    def base(self):
        return 'http://127.0.0.1:%d' % self.server.server_address[1]

    def entry(self, tag, path='', **extra):
        # Every entry carries complete assets, so only its tag or flags can be the reason it is passed over.
        return {'tag_name': tag, 'draft': False, 'prerelease': False, **extra, 'assets': [
            {'name': ARCHIVE, 'browser_download_url': self.base + '/zip' + path},
            {'name': 'SHA256SUMS', 'browser_download_url': self.base + '/sums' + path}]}

    def noise(self):
        # The monorepo also publishes RG DS, frontend-input, and unfinished releases, all newer than the Thor one here.
        return [
            self.entry('rgds-12.01.26.1', '/rgds'),
            self.entry('thor-frontend-rocknix-20261001-6', '/frontend'),
            self.entry('thor-12.02.26.1', '/prerelease', prerelease=True),
            self.entry('thor-12.03.26.1', '/draft', draft=True),
            self.entry('build-0123456789ab', '/legacy'),
        ]

    def publish(self, files, tag=TAG, sums_override=None, releases=None):
        archive = archive_bytes(files)
        digest = sums_override or hashlib.sha256(archive).hexdigest()
        listing = self.noise() + [self.entry(tag)] if releases is None else releases
        self.server.routes.update({
            '/release': json.dumps(listing).encode(),
            '/zip': archive,
            '/sums': (digest + '  ' + ARCHIVE + '\n').encode(),
        })

    def assert_only_thor_downloads(self):
        fetched = [path for path in self.server.requests if path.startswith(('/zip', '/sums'))]
        self.assertTrue(fetched)
        self.assertEqual(set(fetched) - {'/zip', '/sums'}, set())

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
        self.assertEqual(self.server.notifications[-1], 'Multi Pop updated to version 2.')
        self.assertIsNone(self.updates('pending.json'))
        self.assertTrue(backup.is_dir())
        self.assertEqual(self.server.requests.count('/zip'), 1)

    def test_message_waits_for_an_idle_frontend(self):
        self.server.routes['/isIdle'] = b'[ false ]'
        self.config.idle_wait = 0
        auto_update.background(self.config)
        self.assertEqual(self.updates('staged.json')['tag'], TAG)
        self.assertEqual(self.server.notifications, [])

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

    def test_older_or_equal_release_is_never_staged(self):
        for number in (1, 0):
            with self.subTest(number=number):
                tag = 'thor-01.01.26.%d' % (number + 1)
                self.publish(theme_files('older', number=number), tag=tag)
                (self.config.updates / 'last-check').unlink(missing_ok=True)
                auto_update.background(self.config)
                self.assertIsNone(self.updates('staged.json'))
                self.assertIn(tag, self.updates('rejected.json'))
                self.assertIn('old', self.installed_theme())

    def test_numbered_release_replaces_an_unnumbered_installation(self):
        (self.config.theme / 'version.json').unlink()
        auto_update.background(self.config)
        self.assertEqual(self.updates('staged.json')['version'], 2)

    def test_manual_check_stages_while_updates_are_off(self):
        self.set_updates(None)
        auto_update.background(self.config)
        auto_update.check(self.config)
        self.assertIn('version 2 is ready', self.server.notifications[-1])
        auto_update.apply(self.config)
        self.assertIn('new', self.installed_theme())

    def test_manual_check_reports_up_to_date(self):
        self.publish(theme_files('old'))
        auto_update.check(self.config)
        auto_update.check(self.config)
        self.assertEqual(self.server.requests.count('/release'), 2)
        self.assertEqual(self.server.notifications, ['Multi Pop is up to date (version 1).'] * 2)

    def test_manual_check_reports_a_failure(self):
        del self.server.routes['/release']
        auto_update.check(self.config)
        self.assertIn('Could not check', self.server.notifications[-1])

    def test_updates_are_off_unless_turned_on(self):
        for value in (None, 'off'):
            with self.subTest(value=value):
                self.set_updates(value)
                auto_update.background(self.config)
                self.assertNotIn('/release', self.server.requests)

    def test_turning_updates_off_discards_a_staged_release(self):
        auto_update.background(self.config)
        self.set_updates('off')
        auto_update.apply(self.config)
        self.assertIn('old', self.installed_theme())
        self.assertIsNone(self.updates('staged.json'))
        self.assertFalse((self.config.updates / 'staged.zip').exists())

    def test_checks_are_rate_limited(self):
        self.publish(theme_files('old'))
        auto_update.background(self.config)
        auto_update.background(self.config)
        self.assertEqual(self.server.requests.count('/release'), 1)

    def test_date_release_displays_label_even_with_legacy_pending_state(self):
        (self.config.theme / 'version.json').write_text(json.dumps({'version': 25}))
        files = theme_files('new', number=20261021001)
        files['version.json'] = json.dumps({'version': 20261021001, 'display_version': '10.21.26.1'}).encode()
        self.publish(files)
        auto_update.check(self.config)
        self.assertIn('version 10.21.26.1 is ready', self.server.notifications[-1])
        auto_update.apply(self.config)
        # A pre-date updater may have written this marker without a display label.
        pending = self.updates('pending.json')
        pending.pop('display_version', None)
        auto_update.write_json(self.config.updates / 'pending.json', pending)
        auto_update.confirm(self.config)
        self.assertEqual(self.server.notifications[-1], 'Multi Pop updated to version 10.21.26.1.')
        auto_update.check(self.config)
        self.assertEqual(self.server.notifications[-1], 'Multi Pop is up to date (version 10.21.26.1).')

    def test_other_systems_and_frontend_inputs_are_ignored(self):
        auto_update.background(self.config)
        self.assertEqual(self.updates('staged.json')['tag'], TAG)
        self.assert_only_thor_downloads()

    def test_prereleases_and_drafts_are_ignored(self):
        self.publish(theme_files('new'), releases=[
            self.entry('thor-12.02.26.1', '/prerelease', prerelease=True),
            self.entry('thor-12.03.26.1', '/draft', draft=True)])
        auto_update.check(self.config)
        self.assertIsNone(self.updates('staged.json'))
        self.assertNotIn('/zip/prerelease', self.server.requests)
        self.assertNotIn('/zip/draft', self.server.requests)
        self.assertEqual(self.server.notifications, ['Multi Pop is up to date (version 1).'])

    def test_newest_thor_release_wins_whatever_the_listing_order(self):
        older = ['thor-10.28.26.1', 'thor-09.30.26.9', 'thor-12.31.25.99']
        for order in (older + [TAG], [TAG] + older, older[:1] + [TAG] + older[1:]):
            with self.subTest(order=order):
                self.publish(theme_files('new'), releases=[self.entry(tag, '' if tag == TAG else '/' + tag) for tag in order])
                self.assertEqual(auto_update.latest_release(self.config)[0], TAG)
        # Revision and year order numerically, not as text.
        self.publish(theme_files('new'), releases=[self.entry('thor-01.02.27.1', '/a'), self.entry('thor-12.31.26.100', '/b'), self.entry('thor-01.02.27.10')])
        self.assertEqual(auto_update.latest_release(self.config)[0], 'thor-01.02.27.10')

    def test_release_missing_its_downloads_is_ignored(self):
        incomplete = self.entry('thor-12.31.26.1', '/incomplete')
        incomplete['assets'] = incomplete['assets'][:1]
        self.publish(theme_files('new'), releases=[incomplete, self.entry(TAG)])
        self.assertEqual(auto_update.latest_release(self.config)[0], TAG)

    def test_empty_list_is_up_to_date(self):
        self.publish(theme_files('new'), releases=[])
        auto_update.check(self.config)
        self.assertIsNone(self.updates('staged.json'))
        self.assertEqual(self.server.notifications, ['Multi Pop is up to date (version 1).'])
        self.assertNotIn('failed', (self.config.updates / 'auto-update.log').read_text())

    def test_single_release_object_is_accepted(self):
        self.publish(theme_files('new'))
        self.server.routes['/release'] = json.dumps(self.entry(TAG)).encode()
        auto_update.background(self.config)
        self.assertEqual(self.updates('staged.json')['tag'], TAG)

    def test_next_page_is_followed_when_the_first_has_no_thor_release(self):
        self.publish(theme_files('new'))
        self.server.routes['/release'] = (json.dumps(self.noise()).encode(), '<' + self.base + '/release2>; rel="next"')
        self.server.routes['/release2'] = (json.dumps([self.entry(TAG)]).encode(), '<' + self.base + '/release3>; rel="next"')
        self.server.routes['/release3'] = json.dumps([self.entry('thor-12.31.26.1', '/later')]).encode()
        auto_update.background(self.config)
        self.assertEqual(self.updates('staged.json')['tag'], TAG)
        self.assertNotIn('/release3', self.server.requests)

    def test_pages_stop_after_the_limit(self):
        for page in range(1, 6):
            self.server.routes['/page%d' % page] = (b'[]', '<%s/page%d>; rel="next"' % (self.base, page + 1))
        self.config.release_api = self.base + '/page1'
        self.assertIsNone(auto_update.latest_release(self.config))
        self.assertEqual([path for path in self.server.requests if path.startswith('/page')], ['/page1', '/page2', '/page3'])

    def test_missing_repository_is_a_logged_failure(self):
        del self.server.routes['/release']
        auto_update.background(self.config)
        self.assertIsNone(self.updates('staged.json'))
        self.assertIn('Update check failed: HTTP Error 404', (self.config.updates / 'auto-update.log').read_text())

    def test_update_source_override_is_honored(self):
        relay = self.base + '/relay'
        self.server.routes['/relay'] = self.server.routes['/release']
        auto_update.write_json(self.config.state / 'update-source.json', {'release_api': relay})
        auto_update.use_update_source(self.config)
        self.assertEqual(self.config.release_api, relay)
        auto_update.background(self.config)
        self.assertEqual(self.updates('staged.json')['tag'], TAG)
        self.assertIn('/relay', self.server.requests)
        self.assertNotIn('/release', self.server.requests)

    def test_update_source_requires_https_or_loopback(self):
        default = self.config.release_api
        auto_update.write_json(self.config.state / 'update-source.json', {'release_api': 'http://192.168.1.5:8000/releases'})
        with self.assertRaisesRegex(RuntimeError, 'HTTPS'):
            auto_update.use_update_source(self.config)
        self.assertEqual(self.config.release_api, default)
        auto_update.write_json(self.config.state / 'update-source.json', {'release_api': 'https://relay.example/releases'})
        auto_update.use_update_source(self.config)
        self.assertEqual(self.config.release_api, 'https://relay.example/releases')

    def test_default_source_is_the_monorepo(self):
        self.assertEqual(auto_update.Config().release_api, 'https://api.github.com/repos/ballardcm/multi-pop/releases?per_page=30')


if __name__ == '__main__':
    unittest.main(verbosity=2)
