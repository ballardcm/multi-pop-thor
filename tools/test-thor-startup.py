#!/usr/bin/env python3
"""Exercise activation, simulated reboot, and restoration in an isolated device tree."""

import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'multi-pop-thor/scripts'


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mp-start-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'storage/.config'
        self.state = self.config / 'multi-pop-thor'
        self.settings = self.config / 'emulationstation/es_settings.cfg'
        self.sway = self.config / 'sway/config'
        self.override = self.config / 'system.d/essway.service.d/multi-pop-thor.conf'
        self.mountinfo = self.root / 'proc/self/mountinfo'
        self.write(self.settings, '<config>\n<string name="ThemeSet" value="system-theme" />\n</config>\n')
        self.stock_settings = self.settings.read_text()
        self.stock_sway = ('output DSI-2 transform 90\noutput DSI-1 power off\n'
                           'exec_always swaymsg input "0:0:bottom_touchscreen" events disabled\n')
        self.write(self.sway, self.stock_sway)
        self.write(self.mountinfo, '')
        self.write(self.root / 'usr/bin/es_settings', ':\n')
        self.write(self.root / 'usr/bin/start_es.sh', '#!/bin/bash\n')
        self.write(self.root / 'usr/bin/emulationstation', '#!/bin/bash\nprintf stock > "$TEST_ROOT/started"\n', 0o755)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        # Only privileged platform commands are replaced; the actual helper scripts do the file mutations.
        stub = r"""#!PYTHON
import os, pathlib, sys
root = pathlib.Path(os.environ['TEST_ROOT'])
command = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / 'commands').open('a') as log:
    log.write(command + ' ' + ' '.join(args) + '\n')
mountinfo = root / 'proc/self/mountinfo'
if command == 'systemctl' and args[0] == 'show':
    print(' '.join(str(p) for p in (root / 'storage/.config/system.d/essway.service.d').glob('*.conf')))
elif command == 'swaymsg':
    print('[{"name":"DSI-2"}, {"name":"DSI-1"}]')
elif command == 'mount':
    mountinfo.write_text('1 0 0:1 ' + args[-2] + ' ' + args[-1] + ' rw - overlay overlay rw\n')
elif command == 'umount':
    mountinfo.write_text('')
elif command == 'stat':
    print('1:2')
"""
        import sys
        for name in ('systemctl', 'swaymsg', 'mount', 'mountpoint', 'umount', 'stat', 'sleep'):
            self.write(self.bin / name, stub.replace('PYTHON', sys.executable, 1), 0o755)
        sockpath = self.root / 'run/0-runtime-dir/sway-ipc.0.sock'
        sockpath.parent.mkdir(parents=True)
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.bind(str(sockpath))
        self.addCleanup(self.sock.close)
        self.env = dict(os.environ, TEST_ROOT=str(self.root), PATH=str(self.bin) + os.pathsep + os.environ['PATH'])
        self.install_theme('roms/themes/multi-pop-thor')

    def write(self, path, text, mode=0o644):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(mode)

    def install_theme(self, location):
        self.theme = self.root / location
        self.write(self.theme / 'theme.xml', '<theme/>')
        for source in SCRIPTS.glob('*.sh'):
            text = source.read_text()
            text = re.sub(r'/(?:storage|roms|usr/bin|proc|sys|var/run|run)/',
                          lambda match: str(self.root) + match[0], text)
            text = text.replace('[[ $EUID -eq 0 ]]', 'true')
            self.write(self.theme / 'scripts' / source.name, text, 0o755)
        self.write(self.theme / 'frontend/emulationstation', '#!/bin/bash\nprintf patched > "$TEST_ROOT/started"\n', 0o755)

    def helper(self, name, *args, success=True):
        result = subprocess.run(['bash', str(self.theme / 'scripts' / name), *args], env=self.env,
                                text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def reboot(self):
        self.sway.write_text(self.stock_sway)
        self.mountinfo.write_text('')
        self.helper('start_after_reboot.sh')

    def test_install_reboot_repeat_and_restore(self):
        self.helper('enable_multi_pop_thor.sh')
        self.assertIn(str(self.theme / 'scripts/start_after_reboot.sh'), self.override.read_text())
        self.assertIn('daemon-reload', (self.root / 'commands').read_text())
        self.reboot()
        self.assertEqual((self.root / 'started').read_text(), 'patched')
        self.assertIn('start_es_thor.sh', self.mountinfo.read_text())
        self.assertEqual(self.sway.read_bytes(), (self.state / 'installed.sway').read_bytes())
        self.helper('enable_multi_pop_thor.sh', '--prepare')
        self.reboot()
        self.helper('restore_multi_pop_thor.sh')
        self.assertFalse(self.override.exists())
        self.assertEqual(self.settings.read_text(), self.stock_settings)
        self.assertEqual(self.sway.read_text(), self.stock_sway)
        self.assertEqual(self.mountinfo.read_text(), '')
        self.helper('enable_multi_pop_thor.sh', '--prepare')
        self.assertTrue(self.override.exists())

    def test_prepare_preserves_stock_theme_after_reboot(self):
        self.helper('enable_multi_pop_thor.sh', '--prepare')
        self.assertIn('system-theme', self.settings.read_text())
        self.helper('start_after_reboot.sh')
        self.assertEqual((self.root / 'started').read_text(), 'patched')
        self.reboot()
        self.assertEqual((self.root / 'started').read_text(), 'stock')
        self.assertEqual(self.sway.read_text(), self.stock_sway)
        self.assertEqual(self.mountinfo.read_text(), '')
        self.helper('restore_multi_pop_thor.sh')
        self.assertFalse(self.override.exists())

    def test_alternative_theme_directory(self):
        shutil.rmtree(self.theme)
        self.install_theme('storage/.config/emulationstation/themes/multi-pop-thor')
        self.helper('enable_multi_pop_thor.sh')
        self.reboot()
        self.assertEqual((self.root / 'started').read_text(), 'patched')
        self.helper('restore_multi_pop_thor.sh')

    def test_unowned_service_override_is_preserved(self):
        for name in ('custom.conf', 'multi-pop-thor.conf'):
            with self.subTest(name=name):
                override = self.override.with_name(name)
                self.write(override, '[Service]\nExecStart=/custom/frontend\n')
                self.helper('enable_multi_pop_thor.sh', success=False)
                self.assertEqual(self.settings.read_text(), self.stock_settings)
                self.assertEqual(self.sway.read_text(), self.stock_sway)
                self.assertIn('/custom/frontend', override.read_text())
                override.unlink()

    def test_edited_service_override_blocks_restore(self):
        self.helper('enable_multi_pop_thor.sh')
        self.override.write_text('[Service]\nExecStart=/custom/frontend\n')
        self.helper('restore_multi_pop_thor.sh', success=False)
        self.assertIn('/custom/frontend', self.override.read_text())
        self.assertIn('multi-pop-thor', self.settings.read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
