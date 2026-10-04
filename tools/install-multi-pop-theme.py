#!/usr/bin/env python3
"""Install a complete Multi Pop archive without changing the active configuration."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


THEME = Path('/roms/themes/multi-pop-thor')
STATE = Path('/storage/.config/multi-pop-thor')
SETTINGS = Path('/storage/.config/emulationstation/es_settings.cfg')
SWAY_FILES = (Path('/storage/.config/sway/config'), Path('/storage/.config/sway/multi-pop-thor.conf'))
LAUNCHER = Path('/usr/bin/start_es.sh')
MOUNTINFO = Path('/proc/self/mountinfo')
FRONTEND = 'frontend/emulationstation'
START_SCRIPT = 'scripts/start_es_thor.sh'
ACTIVATION_FILES = ('installed.settings', 'installed.sway', 'installed.fragment', 'launcher.identity', 'theme.path', 'active')


def run(args, timeout=15):
    result = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError('A required command failed: ' + args[0])
    return result.stdout


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError('The manifest contains a duplicate file.')
        result[key] = value
    return result


def read_manifest(archive):
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise RuntimeError('The archive contains duplicate entries.')
    manifest = json.loads(archive.read('install-manifest.json'), object_pairs_hook=unique_object)
    if not isinstance(manifest, dict) or not manifest:
        raise RuntimeError('The archive manifest is not a file inventory.')
    for name, checksum in manifest.items():
        path = PurePosixPath(name)
        if not name or '\\' in name or '\x00' in name or path.is_absolute() or '..' in path.parts or str(path) != name:
            raise RuntimeError('The archive contains an unsafe file path.')
        if not isinstance(checksum, str) or not re.fullmatch(r'[0-9a-f]{64}', checksum):
            raise RuntimeError('A manifest checksum is invalid.')
    expected = {'multi-pop-thor/' + name for name in manifest} | {'install-manifest.json'}
    if set(names) != expected:
        raise RuntimeError('The archive contains missing or unexpected entries.')
    required = {'theme.xml', FRONTEND, START_SCRIPT}
    if not required.issubset(manifest):
        raise RuntimeError('The archive does not contain the complete installed theme.')
    for entry in archive.infolist():
        kind = stat.S_IFMT(entry.external_attr >> 16)
        if entry.is_dir() or kind not in (0, stat.S_IFREG):
            raise RuntimeError('The archive contains a nonregular file.')
    return manifest


def unpack(archive_path, stage):
    with zipfile.ZipFile(archive_path) as archive:
        manifest = read_manifest(archive)
        for name, expected in manifest.items():
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open('multi-pop-thor/' + name) as source, destination.open('wb') as target:
                shutil.copyfileobj(source, target)
            destination.chmod(0o755 if name.startswith('scripts/') or name == FRONTEND else 0o644)
            if file_sha(destination) != expected:
                raise RuntimeError('A staged file checksum did not match: ' + name)
    return manifest


def api(path):
    with urllib.request.urlopen('http://127.0.0.1:1234/' + path, timeout=5) as response:
        return json.load(response)


def app_nodes(node):
    found = []
    if node.get('app_id') or node.get('window') or node.get('window_properties', {}).get('class'):
        found.append(node)
    for child in node.get('nodes', []) + node.get('floating_nodes', []):
        found.extend(app_nodes(child))
    return found


def frontend_node():
    nodes = app_nodes(json.loads(run(['swaymsg', '-r', '-t', 'get_tree'])))
    if len(nodes) != 1 or nodes[0].get('app_id') != 'emulationstation':
        raise RuntimeError('Another application is active; the theme was preserved.')
    return nodes[0]


def require_idle_frontend():
    if api('runningGame') != {'msg': 'NO GAME RUNNING'} or api('isIdle') != [True]:
        raise RuntimeError('A game or frontend operation is running; the theme was preserved.')
    node = frontend_node()
    rectangle = node.get('rect', {})
    if (rectangle.get('x'), rectangle.get('y'), rectangle.get('width'), rectangle.get('height')) != (-1240, 0, 4400, 1080):
        raise RuntimeError('The existing frontend does not have the expected Thor viewport.')
    if run(['systemctl', 'is-active', 'essway']).strip() != 'active':
        raise RuntimeError('The existing frontend service is not active.')
    return node


def selected_theme():
    values = {node.get('name'): node.get('value') for node in ET.parse(SETTINGS).getroot()}
    if values.get('ThemeSet') != 'multi-pop-thor':
        raise RuntimeError('Multi Pop is not the selected theme.')
    return values


def settings_values():
    values = {}
    for node in ET.parse(SETTINGS).getroot():
        name = (node.tag, node.get('name'))
        value = node.get('value')
        if node.tag == 'bool':
            value = value.lower() == 'true'
        elif node.tag == 'int':
            value = int(value)
        elif node.tag == 'float':
            value = float(value)
        values[name] = value
    return values


def identity(path):
    info = path.stat()
    return str(info.st_dev) + ':' + str(info.st_ino)


def is_file_mount(path):
    # The firmware's mountpoint utility misses file bind mounts, while the kernel mount table records their exact destinations.
    for line in MOUNTINFO.read_text().splitlines():
        fields = line.split()
        if len(fields) < 5:
            continue
        destination = re.sub(r'\\([0-7]{3})', lambda match: chr(int(match.group(1), 8)), fields[4])
        if destination == str(path):
            return True
    return False


def require_owned_launcher(stage):
    expected = (STATE / 'launcher.identity').read_text().strip()
    if not is_file_mount(LAUNCHER):
        raise RuntimeError('The expected Multi Pop launcher mount is absent.')
    if identity(LAUNCHER) != expected:
        raise RuntimeError('Another launcher is mounted; its contents were preserved.')
    if file_sha(LAUNCHER) != file_sha(stage / START_SCRIPT):
        raise RuntimeError('This archive would change the launcher; a theme-only update cannot do that.')
    return expected


def snapshot_files():
    paths = (*SWAY_FILES, *[STATE / name for name in ACTIVATION_FILES])
    return {'files': {str(path): file_sha(path) for path in paths}, 'settings': settings_values()}


def require_preserved(before, launcher_identity):
    current = snapshot_files()
    if current['files'] != before['files']:
        raise RuntimeError('An activation or compositor file changed while the frontend restarted.')
    # Normal saves can reorder XML and record the last system, but existing user preferences must retain their values.
    for name, expected in before['settings'].items():
        if name[1] != 'LastSystem' and current['settings'].get(name) != expected:
            raise RuntimeError('A user preference changed while the frontend restarted.')
    if identity(LAUNCHER) != launcher_identity:
        raise RuntimeError('The launcher mount changed while the frontend restarted.')


def verify_install(manifest, before, launcher_identity):
    expected_executable = str((THEME / FRONTEND).resolve())
    last_error = None
    for attempt in range(20):
        try:
            node = require_idle_frontend()
            pids = run(['pidof', 'emulationstation']).split()
            if len(pids) != 1 or node.get('pid') != int(pids[0]):
                raise RuntimeError('The expected frontend process is not the only frontend.')
            executable = os.readlink('/proc/' + pids[0] + '/exe')
            if executable != expected_executable:
                raise RuntimeError('The frontend is not running the installed theme binary.')
            command = Path('/proc/' + pids[0] + '/cmdline').read_bytes().split(b'\x00')
            if [b'--resolution', b'4400', b'1080'] not in [command[i:i + 3] for i in range(len(command) - 2)]:
                raise RuntimeError('The frontend did not retain its Thor resolution.')
            values = selected_theme()
            require_preserved(before, launcher_identity)
            outputs = json.loads(run(['swaymsg', '-r', '-t', 'get_outputs']))
            screens = {output.get('name'): output for output in outputs}
            if any(not screens.get(name, {}).get('active') or not screens.get(name, {}).get('power') for name in ('DSI-2', 'DSI-1')):
                raise RuntimeError('Both Thor screens are not active.')
            for name, expected in manifest.items():
                if file_sha(THEME / name) != expected:
                    raise RuntimeError('An installed file checksum did not match: ' + name)
            return {
                'executable': executable, 'frontendSHA256': file_sha(THEME / FRONTEND),
                'theme': values['ThemeSet'], 'gamelistViewStyle': values.get('GamelistViewStyle'),
                'viewport': node['rect'],
                'outputs': [{key: output.get(key) for key in ('name', 'active', 'power', 'rect')} for output in outputs],
            }
        except (RuntimeError, OSError, ValueError) as error:
            last_error = error
            time.sleep(1)
    raise RuntimeError('The updated frontend did not pass verification: ' + str(last_error))


def install(archive_path, expected_sha):
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha) or file_sha(archive_path) != expected_sha:
        raise RuntimeError('The uploaded archive checksum did not match.')
    if os.geteuid() != 0 or not THEME.is_dir() or not STATE.is_dir():
        raise RuntimeError('Run this updater as root on an already activated Multi Pop Thor.')
    os.environ['SWAYSOCK'] = '/var/run/0-runtime-dir/sway-ipc.0.sock'
    lock = STATE / 'lock'
    lock.mkdir()
    stage = None
    backup = None
    service_stopped = False
    swapped = False
    try:
        require_idle_frontend()
        selected_theme()
        stage = Path(tempfile.mkdtemp(prefix='.multi-pop-stage-', dir=THEME.parent))
        stage.chmod(0o755)
        manifest = unpack(archive_path, stage)
        launcher_identity = require_owned_launcher(stage)
        protected_before_help = snapshot_files()

        # The normal launcher environment prevents an SSH session's missing audio setup from blocking even the help command.
        run(['bash', '-c', '. /usr/bin/es_settings; exec "$1" --help', 'multi-pop-check', str(stage / FRONTEND)], timeout=20)
        require_preserved(protected_before_help, launcher_identity)
        require_idle_frontend()
        selected_theme()

        # The frontend owns its normal shutdown save, so configuration snapshots are taken after it has finished saving.
        service_stopped = True
        run(['systemctl', 'stop', 'essway'], timeout=30)
        if subprocess.run(['pidof', 'emulationstation'], capture_output=True, check=False).returncode == 0:
            raise RuntimeError('The frontend remained running after its service stopped.')
        selected_theme()
        before = snapshot_files()
        if before['files'] != protected_before_help['files']:
            raise RuntimeError('An activation or compositor file changed before the theme swap.')
        if identity(LAUNCHER) != launcher_identity:
            raise RuntimeError('The launcher mount changed before the theme swap.')
        backup = THEME.parent / ('.multi-pop-backup-' + stage.name.removeprefix('.multi-pop-stage-'))
        THEME.rename(backup)
        stage.rename(THEME)
        stage = None
        swapped = True

        # Keeping the owned launcher mounted preserves its inode; its stable theme path selects the newly installed frontend.
        run(['systemctl', 'start', 'essway'], timeout=30)
        result = verify_install(manifest, before, launcher_identity)
        service_stopped = False
        result.update({
            'archive': str(archive_path), 'archiveSHA256': expected_sha, 'verifiedFiles': len(manifest),
            'previousThemeBackup': str(backup), 'launcherPreserved': True,
            'settingsPreserved': True, 'swayPreserved': True,
        })
        return result
    except Exception as error:
        recovery_error = None
        try:
            if swapped:
                run(['systemctl', 'stop', 'essway'], timeout=30)
                failed = THEME.parent / ('.multi-pop-failed-' + backup.name.removeprefix('.multi-pop-backup-'))
                THEME.rename(failed)
                backup.rename(THEME)
            elif backup is not None and backup.exists() and not THEME.exists():
                backup.rename(THEME)
        except Exception as recovery:
            recovery_error = recovery
        finally:
            if service_stopped:
                try:
                    run(['systemctl', 'start', 'essway'], timeout=30)
                except Exception as recovery:
                    recovery_error = recovery
        if recovery_error is not None:
            raise RuntimeError('The update failed and automatic recovery needs inspection; the previous theme backup was retained.') from error
        raise
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage)
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('sha256')
    args = parser.parse_args()
    print(json.dumps(install(args.archive, args.sha256), indent=2))


if __name__ == '__main__':
    main()
