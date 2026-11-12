#!/usr/bin/env python3
"""Check declared project tools and notify only for new releases, security first."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
import hashlib
from html import unescape
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote, unquote
import xml.etree.ElementTree as ET

import check_sbom_tool_versions as core

ROOT = Path(__file__).resolve().parents[1]
ANDROID = 'https://dl.google.com/android/repository/repository2-3.xml'
TOOL_DEFINITIONS = {
    'git': {'name': 'Git', 'provider': 'git'},
    'python': {'name': 'Python', 'provider': 'python'},
    'powershell': {'name': 'PowerShell', 'github': 'PowerShell/PowerShell'},
    'docker-engine': {'name': 'Docker Engine', 'github': 'moby/moby', 'tag': r'(?:docker-)?v(?P<version>.+)'},
    'docker-compose': {'name': 'Docker Compose', 'github': 'docker/compose'},
    'docker-desktop': {'name': 'Docker Desktop', 'provider': 'docker-desktop'},
    'gradle': {'name': 'Gradle', 'github': 'gradle/gradle'},
    'agp': {'name': 'Android Gradle Plugin', 'provider': 'agp', 'osv': ['Maven', 'com.android.tools.build:gradle']},
    'jdk': {'name': 'JDK', 'provider': 'jdk'},
    'android-build-tools': {'name': 'Android SDK Build-Tools', 'provider': 'android', 'package': 'build-tools;'},
    'android-platform': {'name': 'Android SDK Platform', 'provider': 'android', 'package': 'platforms;android-'},
    'android-platform-tools': {'name': 'Android SDK Platform-Tools', 'provider': 'android', 'package': 'platform-tools'},
    'android-emulator': {'name': 'Android Emulator', 'provider': 'android', 'package': 'emulator'},
    'android-commandline-tools': {'name': 'Android SDK Command-line Tools', 'provider': 'android', 'package': 'cmdline-tools;'},
    'android-studio': {'name': 'Android Studio', 'provider': 'android-studio'},
    'prometheus': {'name': 'Prometheus / promtool', 'github': 'prometheus/prometheus'},
    'alertmanager': {'name': 'Alertmanager / amtool', 'github': 'prometheus/alertmanager'},
    'postgresql': {'name': 'PostgreSQL', 'provider': 'postgresql'},
    'alpine': {'name': 'Alpine base image', 'provider': 'alpine'},
    'debian': {'name': 'Debian base image', 'provider': 'debian'},
    'make': {'name': 'GNU Make', 'provider': 'make'},
    'curl': {'name': 'curl', 'github': 'curl/curl', 'tag': r'curl-(?P<version>.+)'},
    'node': {'name': 'Node.js', 'github': 'nodejs/node'},
    'npm': {'name': 'npm', 'github': 'npm/cli'},
    'task': {'name': 'Task', 'github': 'go-task/task'},
    'wails': {'name': 'Wails CLI', 'github': 'wailsapp/wails', 'osv': ['Go', 'github.com/wailsapp/wails/v3']},
    'nsis': {'name': 'NSIS', 'provider': 'nsis'},
    'typescript': {'name': 'TypeScript', 'npm': 'typescript'},
    'vite': {'name': 'Vite', 'npm': 'vite'},
    'vite-react': {'name': 'Vite React plugin', 'npm': '@vitejs/plugin-react'},
    'action-checkout': {'name': 'actions/checkout', 'github': 'actions/checkout'},
    'action-setup-go': {'name': 'actions/setup-go', 'github': 'actions/setup-go'},
    'action-upload-artifact': {'name': 'actions/upload-artifact', 'github': 'actions/upload-artifact'},
}
for _package in ['markitdown', 'PyYAML', 'pip', 'attrs', 'jsonschema', 'jsonschema-specifications', 'referencing', 'rpds-py']:
    TOOL_DEFINITIONS['pypi-' + _package.lower()] = {'name': _package, 'pypi': _package}


def release_key(value):
    """Numeric release ordering; only supported stable or explicit preview syntax."""
    match = re.fullmatch(r'v?(\d+(?:\.\d+){0,3})(?:[-.]?(alpha|beta|rc|post|dev|a|b)[.-]?(\d+))?(?:\+[\w.-]+)?', value)
    if not match:
        raise ValueError(f'Unsupported version: {value!r}')
    parts = tuple(int(n) for n in match[1].split('.'))
    stage = {None: 4, 'post': 4, 'dev': 0, 'alpha': 1, 'a': 1, 'beta': 2, 'b': 2, 'rc': 3}[match[2]]
    return parts + (0,) * (4 - len(parts)), stage, int(match[3] or 0)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Release timestamps require a timezone')
    return parsed.astimezone(timezone.utc)


def plain(value):
    return unescape(re.sub(r'<[^>]+>', ' ', value))


def entry(value, url, body='', published=None):
    release_key(value)
    if not url.startswith('https://'):
        raise ValueError('Expected HTTPS release source')
    if published:
        timestamp(published)
    return {'version': value.removeprefix('v'), 'tag_name': value, 'name': value,
            'html_url': url, 'body': body, 'published_at': published}


@lru_cache(maxsize=256)
def read_json(url):
    return core.request_json(url)


@lru_cache(maxsize=256)
def read_text(url):
    return core.request_text(url)


@lru_cache(maxsize=64)
def github_releases(api, repository):
    return api.pages(f'/repos/{repository}/releases')


def settings(root=ROOT):
    config = json.loads((root / '.github/project-tools.json').read_text())
    if not isinstance(config, dict) or set(config) != {'schema_version', 'tools'} or config['schema_version'] != 1 or not isinstance(config['tools'], dict):
        raise ValueError('Expected explicit schema 1 project tools')
    if set(config['tools']) - TOOL_DEFINITIONS.keys():
        raise ValueError('Unknown project tool')
    return config['tools']


def source_basis(tool, config, root=ROOT):
    mode = config.get('mode')
    required = {'mode', 'sources'} | ({'started_at', 'initial_versions'} if mode == 'watch' else {'started_at'} if mode == 'major' else set())
    if mode not in {'pin', 'watch', 'major'} or set(config) - required - {'channel'} or not required <= config.keys():
        raise ValueError(f'Invalid {tool} settings')
    if 'channel' in config and config['channel'] != 'installed-preview':
        raise ValueError('Unsupported release channel')
    if not isinstance(config['sources'], list) or not config['sources']:
        raise ValueError('Every tool requires actual source evidence')
    pins = []
    for source in config['sources']:
        if set(source) not in ({'path', 'pattern'}, {'path', 'pointer'}):
            raise ValueError('Sources require path and pattern or JSON pointer')
        path = (root / source['path']).resolve()
        if Path(source['path']).is_absolute() or not path.is_relative_to(root.resolve()):
            raise ValueError('Tool source must be inside repository')
        content = path.read_text(encoding='utf-8')
        if 'pointer' in source:
            value = json.loads(content)
            for key in source['pointer']:
                value = value[key]
            values = [str(value)]
        else:
            pattern = re.compile(source['pattern'], re.M)
            matches = list(pattern.finditer(content))
            if not matches:
                raise ValueError(f'Missing actual {tool} usage in {source["path"]}')
            if mode == 'watch':
                values = []
            else:
                values = [m.group('version') for m in matches]
        if mode != 'watch':
            if not values:
                raise ValueError('Missing actual version')
            for value in values:
                release_key(value)
        pins.append({'source': source['path'], 'versions': sorted(set(values), key=release_key)})
    if mode == 'watch':
        timestamp(config['started_at'])
        if not isinstance(config['initial_versions'], list):
            raise ValueError('Watch requires an explicit initial upstream inventory')
        for value in config['initial_versions']:
            release_key(value)
        return {'mode': mode, 'started_at': config['started_at'], 'sources': pins, 'installed_version': None}
    values = sorted({v for pin in pins for v in pin['versions']}, key=release_key)
    if mode == 'major':
        timestamp(config['started_at'])
    return {'mode': mode, 'version': values[0], 'versions': values, 'sources': pins}


def read_releases(tool, api):
    definition = TOOL_DEFINITIONS[tool]
    result = []
    if 'github' in definition:
        repository = definition['github']
        for release in github_releases(api, repository):
            if release.get('draft'):
                continue
            match = re.fullmatch(definition.get('tag', r'v?(?P<version>.+)'), release.get('tag_name', ''))
            if not match:
                continue
            value = match['version'].replace('_', '.')
            if '+' in value:
                continue  # experimental alternate builds are not ordinary upstream releases
            try:
                key = release_key(value)
            except ValueError:
                continue  # nightly and unsupported historic tags are never candidates
            if release.get('prerelease') and key[1] == 4:
                continue
            if not isinstance(release.get('body'), str) or not release.get('published_at'):
                raise ValueError('Incomplete GitHub release')
            expected = f'https://github.com/{repository}/releases/tag/{release["tag_name"]}'
            if unquote(release.get('html_url', '')) != expected:
                raise ValueError('Unexpected release source')
            result.append(entry(value, release['html_url'], release['body'], release['published_at']))
    elif 'pypi' in definition:
        package = definition['pypi']
        data = read_json(f'https://pypi.org/pypi/{quote(package)}/json')
        for value, files in data['releases'].items():
            try:
                release_key(value)
            except ValueError:
                continue
            usable = [f for f in files if not f.get('yanked')]
            if usable:
                result.append(entry(value, f'https://pypi.org/project/{package}/{value}/', published=min(f['upload_time_iso_8601'] for f in usable)))
    elif 'npm' in definition:
        package = definition['npm']
        data = read_json(f'https://registry.npmjs.org/{quote(package, safe="")}')
        for value, metadata in data['versions'].items():
            try:
                release_key(value)
            except ValueError:
                continue
            if metadata.get('deprecated'):
                continue
            result.append(entry(value, f'https://www.npmjs.com/package/{package}/v/{value}', published=data['time'][value]))
    else:
        result = special_releases(tool, api)
    if not result:
        raise ValueError(f'No release inventory for {tool}; check incomplete')
    return sorted(result, key=lambda r: release_key(r['version']), reverse=True)


def special_releases(tool, api):
    result = []
    if tool == 'git':
        # Git publishes annotated tags, not GitHub Releases. Tags have upstream dates.
        for tag in api.request('/repos/git/git/tags?per_page=100'):
            value = tag['name'].removeprefix('v')
            try:
                key = release_key(value)
            except ValueError:
                continue
            if key[1] != 4:
                continue
            ref = api.request('/repos/git/git/git/ref/tags/' + quote(tag['name'], safe=''))['object']
            if ref['type'] != 'tag':
                raise ValueError('Expected annotated upstream Git tag')
            data = api.request('/repos/git/git/git/tags/' + ref['sha'])
            result.append(entry(value, 'https://github.com/git/git/releases/tag/' + tag['name'], data['message'], data['tagger']['date']))
            if len(result) >= 20:
                break
    elif tool == 'python':
        data = ET.fromstring(read_text('https://www.python.org/downloads/feed.rss'))
        for item in data.findall('./channel/item'):
            value = item.findtext('title', '').removeprefix('Python ')
            try:
                release_key(value)
            except ValueError:
                continue
            result.append(entry(value, item.findtext('link'), item.findtext('description', ''), parsedate_to_datetime(item.findtext('pubDate')).isoformat()))
    elif tool == 'agp':
        url = 'https://dl.google.com/dl/android/maven2/com/android/tools/build/gradle/maven-metadata.xml'
        data = ET.fromstring(read_text(url))
        for node in data.findall('./versioning/versions/version'):
            try:
                key = release_key(node.text)
            except ValueError:
                continue
            if key[1] == 4:
                series = '-'.join(node.text.split('.')[:2]) + '-0'
                result.append(entry(node.text, 'https://developer.android.com/build/releases/agp-' + series + '-release-notes'))
    elif tool.startswith('android-') and tool != 'android-studio':
        data = ET.fromstring(read_text(ANDROID))
        prefix = TOOL_DEFINITIONS[tool]['package']
        for package in data.findall('remotePackage'):
            path = package.get('path', '')
            if not (path.startswith(prefix) if prefix.endswith((';', '-')) else path == prefix):
                continue
            if package.find('obsolete') is not None or package.find('revision/preview') is not None:
                continue
            channel = package.find('channelRef')
            if channel is not None and channel.get('ref') != 'channel-0':
                continue
            value = path.split('android-')[-1] if tool == 'android-platform' else '.'.join(package.findtext('revision/' + part, '0') for part in ['major', 'minor', 'micro'])
            if not re.fullmatch(r'\d+(?:\.\d+)*', value):
                continue
            result.append(entry(value, 'https://developer.android.com/tools/releases/' + ('platform-tools' if tool == 'android-platform-tools' else 'build-tools' if tool == 'android-build-tools' else 'platforms' if tool == 'android-platform' else 'emulator' if tool == 'android-emulator' else 'cmdline-tools'), package.findtext('display-name', '')))
    elif tool == 'jdk':
        info = read_json('https://api.adoptium.net/v3/info/available_releases')
        for major in sorted(set(info['available_lts_releases'] + [info['most_recent_feature_release']])):
            assets = read_json(f'https://api.adoptium.net/v3/assets/latest/{major}/hotspot?architecture=x64&image_type=jdk&os=linux&vendor=eclipse')
            for asset in assets:
                v = asset['version']
                value = '.'.join(str(v.get(p, 0)) for p in ['major', 'minor', 'security']) + '+' + str(v['build'])
                result.append(entry(value, asset['release_link'], published=asset['binary']['updated_at']))
    elif tool == 'postgresql':
        for release in read_json('https://www.postgresql.org/versions.json'):
            if release['supported']:
                value = release['major'] + '.' + release['latestMinor']
                result.append(entry(value, f'https://www.postgresql.org/docs/release/{value}/', published=release['relDate'] + 'T00:00:00Z'))
    elif tool == 'alpine':
        for branch in read_json('https://alpinelinux.org/releases.json')['release_branches']:
            for release in branch.get('releases', []):
                value = release['version']
                url = 'https://alpinelinux.org/' + release['notes'].removesuffix('.md') + '.html' if release.get('notes') else 'https://alpinelinux.org/releases/'
                result.append(entry(value, url, published=release['date'] + 'T00:00:00Z'))
    elif tool == 'nsis':
        url = 'https://nsis.sourceforge.io/Docs/AppendixF.html'
        raw = read_text(url)
        for match in re.finditer(r'<a name="v([0-9.]+)"></a><h2>.*?</h2>(.*?)(?=<a name="v|\Z)', raw, re.S):
            body = plain(match[2])
            date_match = re.search(r'Released on (\w+) (\d+)(?:st|nd|rd|th)?, (\d{4})', body)
            if not date_match:
                continue  # unreleased development documentation is excluded
            when = datetime.strptime(' '.join(date_match.groups()), '%B %d %Y').replace(tzinfo=timezone.utc)
            result.append(entry(match[1], url + '#v' + match[1], body, when.isoformat()))
    elif tool == 'docker-desktop':
        url = 'https://raw.githubusercontent.com/docker/docs/main/content/manuals/desktop/release-notes.md'
        raw = read_text(url)
        for match in re.finditer(r'^## (\d+\.\d+\.\d+)\s*\n(.*?)(?=^## |\Z)', raw, re.M | re.S):
            date_match = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', match[2])
            if not date_match:
                continue
            result.append(entry(match[1], 'https://docs.docker.com/desktop/release-notes/#' + match[1].replace('.', ''), match[2], date_match[1] + 'T00:00:00Z'))
    elif tool == 'android-studio':
        url = 'https://dl.google.com/android/studio/patches/updates.xml'
        data = ET.fromstring(read_text(url))
        for channel in data.findall('./product/channel'):
            if channel.get('status') != 'release':
                continue
            for build in channel.findall('build'):
                value = build.get('version', '')
                # The stable IDE version is year.major.minor.patch, not the marketing name.
                match = re.search(r'(20\d{2}\.\d+\.\d+(?:\.\d+)?)', value)
                if not match:
                    continue
                patch = re.search(r'Patch (\d+)', value)
                version = match[1] + ('.' + patch[1] if patch and len(match[1].split('.')) == 3 else '')
                when = datetime.fromtimestamp(int(build.get('releaseDate')) / 1000, timezone.utc).isoformat() if build.get('releaseDate', '').isdigit() else None
                result.append(entry(version, 'https://developer.android.com/studio/releases', plain(build.findtext('message', '')), when))
    elif tool == 'debian':
        url = 'https://www.debian.org/News/news'
        data = ET.fromstring(read_text(url))
        ns = {'r': 'http://purl.org/rss/1.0/', 'dc': 'http://purl.org/dc/elements/1.1/'}
        for item in data.findall('r:item', ns):
            title = item.findtext('r:title', '', ns)
            match = re.search(r'Debian (?:\d+: )?(\d+(?:\.\d+)+).*released', title)
            if match:
                when = item.findtext('dc:date', namespaces=ns)
                if re.fullmatch(r'\d{4}-\d{2}-\d{2}', when):
                    when += 'T00:00:00Z'
                result.append(entry(match[1], item.findtext('r:link', namespaces=ns), title + '\n' + plain(item.findtext('r:description', '', ns)), when))
    elif tool == 'make':
        url = 'https://ftp.gnu.org/gnu/make/'
        for value, day in re.findall(r'href="make-(\d+(?:\.\d+)+)\.tar\.gz".*?(\d{4}-\d{2}-\d{2})', read_text(url)):
            result.append(entry(value, url + 'make-' + value + '.tar.gz', published=day + 'T00:00:00Z'))
    return result


def candidates(releases, config, basis):
    current = release_key(basis['version']) if 'version' in basis else None
    channel = config.get('channel')
    eligible = []
    for release in releases:
        key = release_key(release['version'])
        if key[1] != 4 and not (channel == 'installed-preview' and current and current[1] != 4 and key[0][:2] == current[0][:2]):
            continue
        if basis['mode'] == 'watch':
            if release['version'] in config['initial_versions']:
                continue
            if release['published_at']:
                newer = timestamp(release['published_at']) > timestamp(config['started_at'])
            else:
                newer = release['version'] not in config['initial_versions']
        elif basis['mode'] == 'major':
            # Existing patches are already selected by a floating alias; future patches still notify.
            newer = key[0][0] > current[0][0] or (key[0][0] == current[0][0] and release['published_at'] and timestamp(release['published_at']) > timestamp(config['started_at']))
        else:
            newer = key > current
        if newer:
            eligible.append(release)
    return eligible


def extra_evidence(tool, basis, releases):
    definition = TOOL_DEFINITIONS[tool]
    enriched = []
    for release in releases:
        row = dict(release)
        url = None
        if tool == 'gradle':
            url = f'https://docs.gradle.org/{row["version"]}/release-notes.html'
        elif tool in {'python', 'postgresql', 'alpine', 'agp', 'debian'}:
            url = row['html_url']
        elif tool == 'git':
            # Stable release tag, not moving master, so notes cannot describe a future release.
            prefix = f'https://raw.githubusercontent.com/git/git/v{row["version"]}/Documentation/RelNotes/{row["version"]}'
            try:
                row['body'] += '\n' + read_text(prefix + '.adoc')
            except OSError as exc:
                if getattr(exc, 'code', None) != 404:
                    raise
                row['body'] += '\n' + read_text(prefix + '.txt')
        if url:
            content = read_text(url)
            if tool == 'agp' and release_key(row['version'])[0][2] != 0:
                section = re.search(r'<h3\b[^>]*id="fixed-issues-agp-' + re.escape(row['version']) + r'"[^>]*>.*?</h3>(.*?)(?=<h[123]\b|\Z)', content, re.S)
                if not section:
                    raise ValueError('Missing AGP patch release notes')
                content = section[0]
            row['body'] += '\n' + plain(content)
        enriched.append(row)
    evidence = core.security_evidence(enriched)
    for row in enriched:
        if re.search(r'(?:^|\n)\s*#{1,6}\s+Security\b|\bsecurity (?:release|vulnerability|vulnerabilities)\b', row['body'], re.I) and not any(e['version'] == row['tag_name'] for e in evidence):
            evidence.append({'version': row['tag_name'], 'url': row['html_url'], 'identifiers': []})
    if tool == 'jdk':
        # Temurin asset releases omit CVEs. Correlate nearby official OpenJDK
        # advisories as a priority signal, never as proof of installed exposure.
        base = 'https://openjdk.org/groups/vulnerability/advisories/'
        dates = set(re.findall(r'href=[\"\x27](\d{4}-\d{2}-\d{2})[\"\x27]', read_text(base)))
        if not dates:
            raise ValueError('Missing OpenJDK advisory index')
        for row in releases:
            for day in sorted(dates, reverse=True):
                age = (timestamp(row['published_at']) - timestamp(day + 'T00:00:00Z')).days
                if 0 <= age <= 14:
                    body = plain(read_text(base + day))
                    ids = sorted(set(i.upper() for i in core.IDENTIFIER.findall(body)))
                    if ids:
                        evidence.append({'version': row['version'], 'url': base + day, 'identifiers': ids,
                                         'basis': 'Official OpenJDK advisory within 14 days before this JDK asset release; verify version applicability.'})
    osv = definition.get('osv') or (['PyPI', definition['pypi']] if 'pypi' in definition else ['npm', definition['npm']] if 'npm' in definition else None)
    if osv and 'versions' in basis:
        for current in basis['versions']:
            data = core.request_json('https://api.osv.dev/v1/query', data={'package': {'ecosystem': osv[0], 'name': osv[1]}, 'version': current}, method='POST')
            if not isinstance(data, dict) or not isinstance(data.get('vulns', []), list):
                raise ValueError('Invalid advisory response')
            for advisory in data.get('vulns', []):
                if advisory.get('withdrawn'):
                    continue
                fixes = [event['fixed'] for affected in advisory.get('affected', []) if affected.get('package', {}).get('name') == osv[1] for span in affected.get('ranges', []) for event in span.get('events', []) if 'fixed' in event]
                supported_fixes = []
                for fixed in fixes:
                    try:
                        if release_key(current) < release_key(fixed) <= release_key(releases[0]['version']):
                            supported_fixes.append(fixed)
                    except ValueError:
                        continue
                if supported_fixes:
                    evidence.append({'version': ', '.join(supported_fixes), 'url': 'https://osv.dev/vulnerability/' + advisory['id'], 'identifiers': [advisory['id'], *advisory.get('aliases', [])]})
    return evidence


def check_tool(api, repository, assignee, tool, config, *, root=ROOT, publish=False):
    definition = TOOL_DEFINITIONS[tool]
    basis = source_basis(tool, config, root)
    releases = read_releases(tool, api)
    selected = candidates(releases, config, basis)
    stable = [r for r in releases if release_key(r['version'])[1] == 4]
    result = {'tool': definition['name'], 'tool_id': tool, 'status': 'no_update', 'published': False,
              'version_basis': basis, 'latest_stable_upstream': stable[0]['version'] if stable else None}
    if not selected:
        return result
    issues = api.pages(f'/repos/{repository}/issues?state=all&creator=github-actions%5Bbot%5D')
    issues = [i for i in issues if 'pull_request' not in i]
    # Unpinned tools can publish a security patch on an older supported branch.
    # Remember every release in a watch notification, not just the largest version.
    covered = False
    if basis['mode'] == 'watch':
        unseen = [r for r in selected if not any(f'<!-- project-tool-release:{tool}:{r["version"]} -->' in (i.get('body') or '') for i in issues)]
        covered = not unseen
        selected = unseen or selected[:1]  # revisit latest release for a later security disclosure
    evidence = extra_evidence(tool, basis, selected)
    latest = selected[0]['version']
    marker = f'<!-- codex-skills:sbom-tool-update:{tool}:{latest} -->'
    existing = next((i for i in issues if 'pull_request' not in i and marker in (i.get('body') or '')), None)
    if covered and existing is None:
        existing = next(i for i in issues if f'<!-- project-tool-release:{tool}:{latest} -->' in (i.get('body') or ''))
    result.update(latest=latest, security=bool(evidence), evidence=evidence)
    security_key = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()[:20]
    security_marker = f'<!-- project-tool-security:{security_key} -->'
    if existing and (not evidence or security_marker in (existing.get('body') or '')):
        return result | {'status': 'already_reported', 'issue': existing.get('html_url')}
    priority = '安全修補優先' if evidence else '一般版本更新'
    title = f'[{priority}] {definition["name"]} {latest} 已發布'
    description = f'目前來源版本：`{basis["version"]}`' if 'version' in basis else f'未固定安裝版本；自 {basis["started_at"]} 追蹤官方新發布，未推測主機版本。'
    coverage_markers = {f'<!-- project-tool-release:{tool}:{r["version"]} -->' for r in selected}
    if existing:
        coverage_markers.update(re.findall(r'<!-- project-tool-release:[^\n]+? -->', existing.get('body') or ''))
    lines = [marker, security_marker, *sorted(coverage_markers), f'@{assignee}，{repository} 使用的 {definition["name"]} 有新版。', '', description,
             f'- 最新候選：[{latest}]({selected[0]["html_url"]})',
             '- 實際使用來源：' + ', '.join('`' + p['source'] + '`' for p in basis['sources']), '',
             '建議 24～48 小時內評估安全修補並驗證。' if evidence else '建議納入每月維護評估。', '']
    if evidence:
        lines += ['安全修補線索（含中間版本；請依公告確認適用性）：', '']
        lines += [f'- [{e["version"]}]({e["url"]})：' + (', '.join(e['identifiers']) or '官方發布紀錄標示安全修補') for e in evidence]
    lines += ['', '新增或尚未採用版本：', '']
    lines += [f'- [{r["version"]}]({r["html_url"]})' for r in selected[:30]]
    if len(selected) > 30:
        lines += [f'- 另有 {len(selected) - 30} 個中間版本；安全證據已全部檢查。']
    lines += ['', '此通知不會自動升級。變更工具或映像後，須重新測試、核對 digest 並通過 SBOM，再提交推送。']
    result.update(status='security_escalation' if existing else 'update_available', title=title, body='\n'.join(lines) + '\n')
    if publish:
        if existing:
            comment_marker = f'<!-- project-tool-security-comment:{security_key} -->'
            comments = api.pages(f'/repos/{repository}/issues/{existing["number"]}/comments')
            if not any(comment_marker in (c.get('body') or '') for c in comments):
                api.request(f'/repos/{repository}/issues/{existing["number"]}/comments', method='POST', data={'body': comment_marker + '\n' + result['body']})
            response = api.request(f'/repos/{repository}/issues/{existing["number"]}', method='PATCH', data={'title': title, 'body': result['body']})
            return result | {'published': True, 'issue': response['html_url']}
        return core.publish_issue(api, repository, assignee, existing, title, result['body'], result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY'))
    parser.add_argument('--assignee', default='SimonChung')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    results = []
    try:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository or '') or not re.fullmatch(r'[A-Za-z0-9-]+', args.assignee):
            raise ValueError('Expected repository and GitHub login')
        token = os.environ.get('GH_TOKEN', '')
        if args.publish and not token:
            raise ValueError('GH_TOKEN required for publishing')
        api = core.GitHub(token)
        checks = [('Trivy', lambda publish: core.check(api, args.repository, args.assignee, publish=publish)),
                  ('Go', lambda publish: core.check_go(api, args.repository, args.assignee, publish=publish))]
        for tool, config in settings().items():
            checks.append((TOOL_DEFINITIONS[tool]['name'], lambda publish, tool=tool, config=config: check_tool(api, args.repository, args.assignee, tool, config, publish=publish)))
        pending = []
        for name, checker in checks:
            try:
                result = checker(False)
            except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
                result = {'tool': name, 'status': 'failed', 'error': str(exc), 'published': False}
            results.append(result)
            if result['status'] in {'update_available', 'security_escalation'}:
                pending.append((len(results) - 1, checker))
        if args.publish:
            for index, checker in sorted(pending, key=lambda pair: not results[pair[0]].get('security', False)):
                try:
                    results[index] = checker(True)
                except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
                    results[index] = {'tool': results[index]['tool'], 'status': 'failed', 'error': str(exc), 'published': False}
        failed = any(r['status'] == 'failed' for r in results)
        report = {'status': 'failed' if failed else 'ok', 'tools': sorted(results, key=lambda r: not r.get('security', False))}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        failed = True
        report = {'status': 'failed', 'error': str(exc), 'tools': results}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        Path(os.environ['GITHUB_STEP_SUMMARY']).write_text('## 專案工具版本檢查\n\n```json\n' + json.dumps(report, ensure_ascii=False, indent=2) + '\n```\n')
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
