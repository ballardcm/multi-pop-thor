#!/usr/bin/env python3
"""Exercise preservation and concurrency behavior using isolated game list fixtures."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


spec = importlib.util.spec_from_file_location("media_install", Path(__file__).with_name("install-multi-pop-media.py"))
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)

ORIGINAL = b'''<?xml version="1.0"?><gameList custom="kept"><!-- Preserve this comment. --><folder id="f"><path>./nested</path><custom>folder data</custom></folder><game custom="yes"><path>./a.nes</path><name>My game title</name><image>./cover.png</image><desc>My own description</desc><genre>Unknown</genre><releasedate>00000000T000000</releasedate><favorite>true</favorite><playcount>17</playcount><customValue>unchanged</customValue></game><game><path>/another/location/game.nes</path><custom>outside reference</custom></game></gameList>'''


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="multi-pop-media-fixtures-")
        self.root = Path(self.temporary.name).resolve()
        self.folder = self.root / "roms/nes"
        self.folder.mkdir(parents=True)
        self.stage = self.root / "stage"
        self.stage.mkdir()
        self.source = self.stage / "snap.png"
        self.source.write_bytes(b"fixture-snapshot")
        self.files = {"snap.png": media.sha_file(self.source)}
        (self.folder / "cover.png").write_bytes(b"cover")
        self.gamelist = self.folder / "gamelist.xml"
        self.gamelist.write_bytes(ORIGINAL)
        self.row = {"system": "nes", "folder": self.folder, "gamelist": self.gamelist,
                    "romPath": str(self.folder / "a.nes"), "screenshot": "snap.png",
                    "metadata": {"desc": "Provider description", "genre": "Action",
                                 "publisher": "Publisher", "releasedate": "19900101T000000"}}

    def tearDown(self):
        self.temporary.cleanup()

    def merge(self, payload, row=None):
        return media.merge_xml(payload, [row or self.row], self.stage, self.files)

    def test_cover_user_fields_and_custom_xml_survive(self):
        output, changes, copies, skipped = self.merge(ORIGINAL)
        root = media.parse_xml(output)
        game = root.find("game")
        for key, value in {"name": "My game title", "desc": "My own description", "favorite": "true",
                           "playcount": "17", "customValue": "unchanged", "thumbnail": "./cover.png",
                           "genre": "Action", "releasedate": "19900101T000000"}.items():
            self.assertEqual(media.text(game, key), value)
        self.assertEqual(root.get("custom"), "kept")
        self.assertEqual(root.find("folder").get("id"), "f")
        self.assertIn(b"Preserve this comment.", output)
        self.assertIn(b"outside reference", output)
        for reference, (source, digest) in copies.items():
            media.copy_owned(self.folder, reference, source, digest)
        second, changes2, _, _ = self.merge(output)
        self.assertFalse(changes2)
        self.assertEqual(second, output)

    def test_distinct_user_screenshot_is_preserved(self):
        (self.folder / "user-shot.png").write_bytes(b"user screenshot")
        original = b'<gameList><game><path>./a.nes</path><image>./user-shot.png</image><thumbnail>./cover.png</thumbnail></game></gameList>'
        output, changes, _, skipped = self.merge(original, {**self.row, "metadata": {}})
        self.assertEqual(output, original)
        self.assertFalse(changes)
        self.assertEqual(skipped["existing_separate_preview_preserved"], 1)

    def test_missing_cover_does_not_become_its_own_screenshot(self):
        original = b'<gameList><game><path>./a.nes</path></game></gameList>'
        output, _, _, _ = self.merge(original, {**self.row, "metadata": {}})
        second, changes, _, _ = self.merge(output, {**self.row, "metadata": {}})
        self.assertFalse(changes)
        self.assertFalse(media.text(media.parse_xml(second).find("game"), "thumbnail"))

    def test_atomic_guard_refuses_a_concurrent_edit(self):
        expected = media.sha_file(self.gamelist)
        self.gamelist.write_bytes(b"concurrent change")
        with self.assertRaises(media.ConcurrentChange):
            media.atomic_checked(self.gamelist, b"replacement", expected)
        self.assertEqual(self.gamelist.read_bytes(), b"concurrent change")

    def test_retry_rereads_new_user_values_and_restarts(self):
        original_writer = media.atomic_checked
        calls = []

        def concurrent_writer(path, payload, expected):
            if not calls:
                current = media.parse_xml(path.read_bytes())
                current.find("game/playcount").text = "18"
                path.write_bytes(media.ET.tostring(current))
            calls.append(True)
            return original_writer(path, payload, expected)

        with patch.object(media, "idle_frontend"), patch.object(media.subprocess, "run") as service, patch.object(media, "atomic_checked", concurrent_writer):
            result = media.bulk_install(self.stage, self.files, [self.row], self.root / "state", True, "http://localhost", "fixture")
        self.assertEqual(result["retries"], 1)
        self.assertTrue(result["frontendRestarted"])
        self.assertEqual(media.text(media.parse_xml(self.gamelist.read_bytes()).find("game"), "playcount"), "18")
        self.assertTrue(any(call.args[0] == ["systemctl", "start", "essway"] for call in service.call_args_list))

    def test_error_after_stop_still_restarts(self):
        with patch.object(media, "idle_frontend"), patch.object(media.subprocess, "run") as service, patch.object(media, "copy_owned", side_effect=ValueError("fixture copy failure")):
            result = media.bulk_install(self.stage, self.files, [self.row], self.root / "state", True, "http://localhost", "fixture")
        self.assertIn("fixture copy failure", result["error"])
        self.assertTrue(result["frontendRestarted"])
        self.assertEqual(self.gamelist.read_bytes(), ORIGINAL)

    def test_backup_is_not_overwritten(self):
        path = media.backup_once(self.gamelist, b"first original", self.root / "state")
        media.backup_once(self.gamelist, b"second original", self.root / "state")
        self.assertEqual(Path(path).read_bytes(), b"first original")

    def test_manifest_rejects_path_and_hash_changes(self):
        row = {**self.row, "folder": str(self.folder), "gamelist": str(self.gamelist)}
        manifest = self.stage / "manifest.json"
        manifest.write_text(json.dumps({"files": self.files, "games": [row]}))
        files, rows = media.load_manifest(self.stage, "manifest.json", {self.root / "roms"})
        self.assertEqual(len(rows), 1)
        with self.assertRaises(ValueError):
            media.canonical_rom("../escape.nes", self.folder)
        self.source.write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            media.load_manifest(self.stage, "manifest.json", {self.root / "roms"})

    def test_native_metadata_adds_blank_date_without_sending_user_fields(self):
        current = {"path": self.row["romPath"], "name": "My game title", "desc": "My own description",
                   "genre": "My genre", "publisher": "My publisher", "releasedate": "00000000T000000"}
        updated = {**current, "releasedate": "19900101T000000"}
        response = Mock(status=200)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        reads = [(200, [{"id": "native-id", "path": self.row["romPath"]}]),
                 (200, current), (200, current), (200, updated)]
        with patch.object(media, "http_json", side_effect=reads), patch.object(media.urllib.request, "urlopen", return_value=response) as post, patch.object(media.subprocess, "run") as service:
            result = media.metadata_install([self.row], self.root / "state", True, "http://localhost")
        self.assertNotIn("error", result)
        self.assertEqual(result["changes"][0]["changedKeys"], ["releasedate"])
        request = post.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"releasedate": "19900101T000000"})
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(Path(result["backups"][str(self.gamelist)]).read_bytes(), ORIGINAL)
        service.assert_not_called()

    def test_native_metadata_preserves_a_date_filled_before_post(self):
        current = {"path": self.row["romPath"], "releasedate": "Unknown"}
        fresh = {**current, "releasedate": "19920715T000000"}
        row = {**self.row, "metadata": {"releasedate": "19900101T000000"}}
        reads = [(200, [{"id": "native-id", "path": self.row["romPath"]}]),
                 (200, current), (200, fresh)]
        with patch.object(media, "http_json", side_effect=reads), patch.object(media.urllib.request, "urlopen") as post:
            result = media.metadata_install([row], self.root / "state", True, "http://localhost")
        self.assertNotIn("error", result)
        self.assertFalse(result["changes"])
        self.assertEqual(result["skipped"], {"metadata_changed_before_import": 1})
        post.assert_not_called()

    def test_native_metadata_verifies_the_imported_date(self):
        current = {"path": self.row["romPath"], "releasedate": "00000000T000000"}
        row = {**self.row, "metadata": {"releasedate": "19900101T000000"}}
        response = Mock(status=200)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        reads = [(200, [{"id": "native-id", "path": self.row["romPath"]}]),
                 (200, current), (200, current), (200, current)]
        with patch.object(media, "http_json", side_effect=reads), patch.object(media.urllib.request, "urlopen", return_value=response):
            result = media.metadata_install([row], self.root / "state", True, "http://localhost")
        self.assertEqual(result["error"], "Imported metadata verification failed")
        self.assertFalse(result["changes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
