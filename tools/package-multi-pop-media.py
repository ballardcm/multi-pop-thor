#!/usr/bin/env python3
"""Package audited public media with exact ROM matches and source credits."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / 'multi-pop-media-staging'


def read_json(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(args):
    inventory = read_json(ROOT / 'multi-pop-media-inventory.json')
    rows = {}
    for system in inventory:
        for game in system['games']:
            rom = game['romPath']
            if rom in rows:
                raise ValueError('The inventory contains a duplicate ROM path.')
            rows[rom] = {'system': system['system'], 'romPath': rom,
                         'folder': system['folder'], 'gamelist': system['gamelist'],
                         'metadata': {}, 'sources': {}}
    files = {}
    sources = {}

    def asset(row, kind, record, path):
        path = path.resolve()
        if not path.is_relative_to(STAGING.resolve()) or not path.is_file():
            raise ValueError('A media asset is outside the audited staging directory.')
        digest = sha(path)
        if digest != record['sha256']:
            raise ValueError('A media asset changed after verification: ' + path.name)
        key = hashlib.sha256(row['romPath'].encode()).hexdigest()[:20]
        ext = '.png' if kind == 'screenshot' else '.mp4'
        relative = kind + 's/' + row['system'] + '/' + key + ext
        files[relative] = digest
        sources[relative] = path
        row[kind] = relative

    if not args.videos_only:
        for record in read_json(STAGING / 'screenshots-report.json')['records']:
            if record['status'] != 'ready':
                continue
            row = rows[record['romPath']]
            asset(row, 'screenshot', record, Path(record['localFile']))
            row['sources']['screenshot'] = {k: record[k] for k in
                ('source', 'sourceName', 'match', 'sha256') if k in record}
        for record in read_json(STAGING / 'metadata-report.json')['matches']:
            row = rows[record['rom_path']]
            data = record['data']
            mapping = {'Overview': 'desc', 'Genres': 'genre', 'Developer': 'developer',
                       'Publisher': 'publisher'}
            for source, destination in mapping.items():
                value = data.get(source, '')
                if isinstance(value, list):
                    value = ', '.join(value)
                if value and str(value).strip().lower() != 'unknown':
                    row['metadata'][destination] = str(value).strip()
            date = data.get('ReleaseDateISO') or data.get('ReleaseDate', '')
            if re.match(r'^\d{4}-\d{2}-\d{2}', date):
                row['metadata']['releasedate'] = date[:10].replace('-', '') + 'T000000'
            row['sources']['metadata'] = {'source': record['source'],
                                        'url': record['source_url']}

    if args.verified_videos:
        manifest = read_json(args.verified_videos)
        videos = manifest if isinstance(manifest, list) else manifest['records']
        # A completed conversion is insufficient; only the separate visual QA manifest is accepted.
        safe = set()
        for name in ('video-candidates.json', 'video-alias-candidates.json'):
            data = read_json(STAGING / name)
            candidates = data if isinstance(data, list) else data['candidates']
            safe.update((r['rom_path'], str(r['longplay_id'])) for r in candidates)
        for record in videos:
            if (record['rom_path'], str(record['longplay_id'])) not in safe:
                raise ValueError('A video is no longer in the approved exact-title candidate list.')
            row = rows[record['rom_path']]
            asset(row, 'video', record, Path(record['video_local']))
            row['sources']['video'] = {k: record[k] for k in
                ('source_page', 'credit', 'longplay_id', 'source_title', 'seek_seconds', 'sha256')
                if k in record}

    games = [r for r in rows.values() if r['metadata'] or 'screenshot' in r or 'video' in r]
    manifest = {'version': '0.4', 'files': files, 'games': games,
                'sources': {'screenshots': 'https://docs.libretro.com/guides/roms-playlists-thumbnails/',
                            'metadata': 'https://gamesdb.launchbox-app.com/',
                            'videos': 'https://longplays.org/'}}
    destination = ROOT / ('multi-pop-media-' + args.tag + '.zip')
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        archive.writestr('manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
        for relative, source in sources.items():
            archive.write(source, relative)
    report = {'archive': str(destination), 'sha256': sha(destination),
              'games': len(games), 'screenshots': sum('screenshot' in r for r in games),
              'descriptions': sum('desc' in r['metadata'] for r in games),
              'videos': sum('video' in r for r in games), 'bytes': destination.stat().st_size}
    (ROOT / ('multi-pop-media-' + args.tag + '-manifest.json')).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    (ROOT / ('multi-pop-media-' + args.tag + '-package.json')).write_text(
        json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', default='v0.4')
    parser.add_argument('--verified-videos', type=Path)
    parser.add_argument('--videos-only', action='store_true')
    build(parser.parse_args())
