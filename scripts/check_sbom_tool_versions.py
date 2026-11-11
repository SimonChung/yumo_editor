#!/usr/bin/env python3
"""Check Trivy and Go releases; create deduplicated GitHub Issues on request."""
from __future__ import annotations

import argparse
import ast
from datetime import date
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = 'aquasecurity/trivy'
VERSION = re.compile(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)')
SECURITY = re.compile(r'\bCVE-\d{4}-\d+\b|\bGHSA-[a-z0-9-]+\b|security[ -]+(?:update|fix|patch)|(?:fix|patch|remediat)\w*[^\n]{0,60}vulnerabil', re.I)
IDENTIFIER = re.compile(r'\b(?:CVE-\d{4}-\d+|GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4})\b', re.I)
GO_DOWNLOADS = 'https://go.dev/dl/?mode=json'
GO_HISTORY = 'https://go.dev/doc/devel/release'


def version(value: str) -> tuple[int, int, int]:
    match = VERSION.fullmatch(value)
    if not match:
        raise ValueError(f'Unsupported stable version: {value!r}')
    return tuple(map(int, match.groups()))


def python_scanner_version(path: Path) -> str:
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SCANNER' for t in node.targets):
            pin = ast.literal_eval(node.value)
            match = re.fullmatch(r'aquasec/trivy:(\d+\.\d+\.\d+)@sha256:[0-9a-f]{64}', pin)
            if not match:
                raise ValueError('Expected a version-and-digest-pinned aquasec/trivy scanner')
            version(match[1])
            return match[1]
    raise ValueError('Missing SCANNER pin')


def current_pin(root: Path | None = None) -> dict:
    root = (root or ROOT).resolve()
    config = json.loads((root / '.github/sbom-tool-monitor.json').read_text(encoding='utf-8'))
    if config.get('schema_version') != 1 or not isinstance(config.get('pin_sources'), list):
        raise ValueError('Invalid SBOM tool monitor configuration')
    found = []
    for source in config['pin_sources']:
        relative = Path(source['path'])
        path = (root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(root):
            raise ValueError('Scanner source must be inside the repository')
        if not path.exists() and source.get('optional') is True:
            continue
        kind = source['kind']
        if kind == 'python_scanner':
            value = python_scanner_version(path)
        else:
            content = path.read_text(encoding='utf-8')
            if kind == 'trivy_image':
                values = set(re.findall(r'aquasec/trivy:(\d+\.\d+\.\d+)@sha256:[0-9a-f]{64}(?![0-9a-f])', content))
            elif kind == 'go_version_guard':
                values = set(re.findall(r'if tool\.Version != "(\d+\.\d+\.\d+)"', content))
            else:
                raise ValueError(f'Unknown scanner source kind: {kind}')
            if len(values) != 1:
                raise ValueError(f'Expected exactly one pinned Trivy version in {relative}')
            value = values.pop()
        version(value)
        found.append({'version': value, 'source': relative.as_posix()})
    if found:
        if len({item['version'] for item in found}) != 1:
            raise ValueError('Scanner source versions disagree')
        return {'mode': 'scanner_pin', 'version': found[0]['version'], 'sources': [item['source'] for item in found]}
    baseline = config.get('baseline')
    if not isinstance(baseline, str):
        raise ValueError('No scanner source or explicit release-monitor baseline')
    version(baseline)
    return {'mode': 'release_baseline', 'version': baseline, 'sources': ['.github/sbom-tool-monitor.json']}


def current_version(path: Path | None = None) -> str:
    return python_scanner_version(path) if path is not None else current_pin()['version']


def go_version(value: str) -> str:
    match = re.fullmatch(r'(?:go)?(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?', value)
    if not match:
        raise ValueError(f'Expected an exact stable Go version: {value!r}')
    return '.'.join(str(int(part or '0')) for part in match.groups())


def current_go_pin(root: Path | None = None) -> dict:
    root = (root or ROOT).resolve()
    config = json.loads((root / '.github/sbom-tool-monitor.json').read_text(encoding='utf-8'))
    settings = config.get('go')
    if config.get('schema_version') != 1 or not isinstance(settings, dict) or not isinstance(settings.get('pin_sources'), list):
        raise ValueError('Missing or invalid Go release monitor configuration')
    pins = []
    for source in settings['pin_sources']:
        relative = Path(source['path'])
        path = (root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(root):
            raise ValueError('Go source must be inside the repository')
        if not path.exists() and source.get('optional') is True:
            continue
        content = path.read_text(encoding='utf-8')
        kind = source['kind']
        if kind == 'go_mod':
            directives = re.findall(r'^\s*go\s+(\S+)\s*(?://.*)?$', content, re.M)
            if len(directives) != 1:
                raise ValueError(f'Expected one go directive in {relative}')
            values = directives + [v for v in re.findall(r'^\s*toolchain\s+(\S+)\s*(?://.*)?$', content, re.M) if v != 'default']
        elif kind == 'go_ci':
            values = re.findall(r'^\s*go-version:\s*[\'\"]?([^\s\'\"#]+)', content, re.M)
        elif kind == 'go_image':
            values = re.findall(r'^\s*FROM\s+(?:--platform=\S+\s+)?golang:([^\s@-]+)', content, re.M | re.I)
        else:
            raise ValueError(f'Unknown Go source kind: {kind}')
        if not values:
            raise ValueError(f'Missing pinned Go version in {relative}')
        pins.append({'source': relative.as_posix(), 'versions': sorted({go_version(v) for v in values}, key=version)})
    if pins:
        versions = sorted({v for pin in pins for v in pin['versions']}, key=version)
        return {'mode': 'go_pins', 'version': versions[0], 'versions': versions, 'pins': pins}
    baseline = settings.get('baseline')
    if not isinstance(baseline, str):
        raise ValueError('No Go source or explicit release-monitor baseline')
    value = go_version(baseline)
    return {'mode': 'release_baseline', 'version': value, 'versions': [value], 'pins': []}


class GoHistory(HTMLParser):
    """Read only version-labelled release paragraphs/headings, not site navigation."""
    def __init__(self, current: str, latest: str):
        super().__init__(convert_charrefs=True)
        self.current = version(current)
        self.latest = version(latest)
        self.entries = {}
        self.active = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        identifier = dict(attrs).get('id', '')
        if tag in ('p', 'h2') and re.fullmatch(r'go\d+\.\d+(?:\.\d+)?', identifier):
            # Historical reserved/unreleased entries have no publication date.
            # Only the requested upgrade interval is relevant to this check.
            if not self.current <= version(go_version(identifier)) <= self.latest:
                return
            if self.active:
                raise ValueError('Nested Go release entries')
            self.active = (tag, identifier)
            self.parts = []

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.active and tag == self.active[0]:
            identifier = self.active[1]
            value = go_version(identifier)
            body = ' '.join(' '.join(self.parts).split())
            published = re.search(r'\(released (\d{4}-\d{2}-\d{2})\)', body)
            if not published or value in self.entries:
                raise ValueError(f'Incomplete or duplicate Go history entry: {identifier}')
            date.fromisoformat(published[1])
            self.entries[value] = {'tag_name': value, 'name': identifier, 'body': body,
                                   'published_at': published[1], 'html_url': GO_HISTORY + '#' + identifier}
            self.active = None


def request_text(url: str) -> str:
    with urlopen(Request(url, headers={'User-Agent': 'codex-skills-tool-version-check'}), timeout=30) as response:
        return response.read().decode('utf-8')


def newer_go_releases(current: str) -> list[dict]:
    downloads = request_json(GO_DOWNLOADS)
    if not isinstance(downloads, list) or not downloads:
        raise ValueError('No Go download metadata; check incomplete')
    stable = []
    for release in downloads:
        if not isinstance(release, dict):
            raise ValueError('Invalid Go download entry')
        if release.get('stable') is False:
            continue
        if release.get('stable') is not True:
            raise ValueError('Missing Go stable release flag')
        value = go_version(release['version'])
        files = release.get('files', [])
        if not isinstance(files, list) or not all(isinstance(f, dict) for f in files):
            raise ValueError('Invalid Go download file inventory')
        sources = [f for f in files if f.get('kind') == 'source']
        if len(sources) != 1 or sources[0].get('version') != release['version'] or not re.fullmatch(r'[0-9a-f]{64}', sources[0].get('sha256', '')):
            raise ValueError(f'Incomplete official Go download: {value}')
        stable.append(value)
    if not stable:
        raise ValueError('No stable Go releases; check incomplete')
    latest = max(stable, key=version)
    if version(latest) <= version(current):
        return []
    history = GoHistory(current, latest)
    history.feed(request_text(GO_HISTORY))
    history.close()
    required = {current, latest} | {v for v in stable if version(current) < version(v)}
    if history.active or not required <= history.entries.keys():
        raise ValueError('Official Go history is incomplete for the current/latest version')
    candidates = [r for v, r in history.entries.items() if version(current) < version(v) <= version(latest)]
    # A missing intermediate patch must not silently hide a security release.
    for candidate in candidates:
        major, minor, patch = version(candidate['tag_name'])
        start = version(current)[2] + 1 if (major, minor) == version(current)[:2] else 0
        if any(f'{major}.{minor}.{n}' not in history.entries for n in range(start, patch + 1)):
            raise ValueError('Missing intermediate Go release history')
    return sorted(candidates, key=lambda r: version(r['tag_name']), reverse=True)


def request_json(url: str, *, headers: dict | None = None, data: dict | None = None, method: str = 'GET'):
    request = Request(url, headers={'User-Agent': 'codex-skills-sbom-version-check', **(headers or {})},
                      data=None if data is None else json.dumps(data).encode(), method=method)
    if data is not None:
        request.add_header('Content-Type', 'application/json')
    with urlopen(request, timeout=30) as response:
        return json.load(response)


class GitHub:
    def __init__(self, token: str = ''):
        self.headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10'}
        if token:
            self.headers['Authorization'] = 'Bearer ' + token

    def request(self, path: str, *, data: dict | None = None, method: str = 'GET'):
        if not path.startswith('/repos/'):
            raise ValueError('Only repository API endpoints are supported')
        return request_json('https://api.github.com' + path, headers=self.headers, data=data, method=method)

    def pages(self, path: str) -> list[dict]:
        result = []
        for page in range(1, 101):
            batch = self.request(f'{path}{"&" if "?" in path else "?"}per_page=100&page={page}')
            if not isinstance(batch, list):
                raise ValueError('Expected a paginated GitHub list')
            result.extend(batch)
            if len(batch) < 100:
                return result
        raise ValueError('Pagination limit exceeded; check incomplete')


def newer_releases(releases: list[dict], current: str) -> list[dict]:
    if not isinstance(releases, list) or not all(isinstance(r, dict) for r in releases):
        raise ValueError('Invalid Trivy release inventory')
    stable = []
    for release in releases:
        if release.get('draft') or release.get('prerelease'):
            continue
        tag = release.get('tag_name', '')
        if not VERSION.fullmatch(tag):
            raise ValueError(f'Unexpected non-prerelease tag: {tag!r}')
        if not release.get('published_at') or not isinstance(release.get('body'), str):
            raise ValueError(f'Incomplete release metadata: {tag}')
        if release.get('html_url') != f'https://github.com/{UPSTREAM}/releases/tag/{tag}':
            raise ValueError('Unexpected release source URL')
        stable.append(release)
    if not stable:
        raise ValueError('No stable releases returned; check incomplete')
    return sorted((r for r in stable if version(r['tag_name']) > version(current)),
                  key=lambda r: version(r['tag_name']), reverse=True)


def security_evidence(releases: list[dict]) -> list[dict]:
    evidence = []
    for release in releases:
        text = (release.get('name') or '') + '\n' + release['body']
        if SECURITY.search(text):
            evidence.append({'version': release['tag_name'], 'url': release['html_url'],
                             'identifiers': sorted(set(i.upper() for i in IDENTIFIER.findall(text)))})
    return evidence


def image_digest(release_version: str) -> str:
    version(release_version)
    token = request_json('https://auth.docker.io/token?service=registry.docker.io&scope=repository:aquasec/trivy:pull')['token']
    request = Request(f'https://registry-1.docker.io/v2/aquasec/trivy/manifests/{release_version}', headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json',
    })
    with urlopen(request, timeout=30) as response:
        raw = response.read()
        digest = response.headers.get('Docker-Content-Digest')
    if digest != 'sha256:' + hashlib.sha256(raw).hexdigest():
        raise ValueError('Registry digest does not match manifest bytes')
    index = json.loads(raw)
    platforms = {(m.get('platform', {}).get('os'), m.get('platform', {}).get('architecture')) for m in index.get('manifests', [])}
    if not {('linux', 'amd64'), ('linux', 'arm64')} <= platforms:
        raise ValueError('Trivy index is missing required amd64/arm64 platforms')
    return digest


def issue_content(current: str, releases: list[dict], digest: str, assignee: str, repository: str) -> tuple[str, str]:
    latest = releases[0]['tag_name'].removeprefix('v')
    evidence = security_evidence(releases)
    marker = f'<!-- codex-skills:sbom-tool-update:trivy:{latest} -->'
    priority = '安全修補優先' if evidence else '一般版本更新'
    title = f'[{priority}] Trivy {latest} 已發布（目前 {current}）'
    lines = [marker, f'@{assignee}，{repository} 追蹤的 Trivy 有新正式版本。', '',
             f'- 目前採用版本／巡檢基準：`{current}`（來源見 `.github/sbom-tool-monitor.json`）', f'- 最新正式版：`{latest}`',
             f'- 發布時間：{releases[0]["published_at"]}',
             f'- 新版映像：`aquasec/trivy:{latest}@{digest}`',
             '- 已確認多架構索引包含 linux/amd64 與 linux/arm64。', '',
             '建議於 24～48 小時內評估安全修補並驗證更新。' if evidence else '建議納入每月工具更新窗口。', '']
    if evidence:
        lines += ['官方發布說明中的安全修補線索（可能包含掃描器或容器相依；影響範圍以官方公告為準）：', '']
        for item in evidence:
            ids = ', '.join(item['identifiers']) or '官方說明標示安全／漏洞修補'
            lines.append(f'- [{item["version"]}]({item["url"]})：{ids}')
    lines += ['', '尚未採用的正式版本（安全修補優先）：', '']
    for release in sorted(releases, key=lambda r: not bool(security_evidence([r]))):
        lines.append(f'- [{release["tag_name"]}]({release["html_url"]}) — {release["published_at"]}')
    lines += ['', '更新時固定版本與 digest，重新執行測試及 SBOM 驗證，通過後再提交推送。',
              '這份 Issue 只追蹤新版資訊，未變更工具或依賴。']
    return title, '\n'.join(lines) + '\n'


def check(api: GitHub, repository: str, assignee: str, *, publish: bool = False, digest_reader=image_digest) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Expected owner/repository')
    if not re.fullmatch(r'[A-Za-z0-9-]+', assignee):
        raise ValueError('Expected a GitHub assignee login')
    current = current_version()
    releases = newer_releases(api.pages(f'/repos/{UPSTREAM}/releases'), current)
    result = {'status': 'no_update', 'tool': 'Trivy', 'current': current, 'published': False}
    if not releases:
        return result
    latest = releases[0]['tag_name'].removeprefix('v')
    evidence = security_evidence(releases)
    marker = f'<!-- codex-skills:sbom-tool-update:trivy:{latest} -->'
    issues = api.pages(f'/repos/{repository}/issues?state=all&creator=github-actions%5Bbot%5D')
    existing = next((i for i in issues if 'pull_request' not in i and marker in (i.get('body') or '')), None)
    result.update(latest=latest, security=bool(evidence), evidence=evidence)
    # The Issue is durable deduplication state, including closed Issues.
    if existing and (not evidence or existing['title'].startswith('[安全修補優先]')):
        result.update(status='already_reported', issue=existing['html_url'])
        return result
    digest = digest_reader(latest)
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
        raise ValueError('Invalid candidate image digest')
    title, body = issue_content(current, releases, digest, assignee, repository)
    result.update(status='security_escalation' if existing else 'update_available', digest=digest, title=title, body=body)
    if not publish:
        return result
    return publish_issue(api, repository, assignee, existing, title, body, result)


def publish_issue(api: GitHub, repository: str, assignee: str, existing: dict | None, title: str, body: str, result: dict) -> dict:
    if existing:
        # One escalation comment wakes participants even if the original Issue was closed.
        comment_marker = '<!-- codex-skills:sbom-security-escalation -->'
        comments = api.pages(f'/repos/{repository}/issues/{existing["number"]}/comments')
        if not any(comment_marker in (c.get('body') or '') for c in comments):
            api.request(f'/repos/{repository}/issues/{existing["number"]}/comments', method='POST',
                        data={'body': comment_marker + '\n' + body})
        response = api.request(f'/repos/{repository}/issues/{existing["number"]}', method='PATCH',
                               data={'title': title, 'body': body})
    else:
        response = api.request(f'/repos/{repository}/issues', method='POST',
                               data={'title': title, 'body': body, 'assignees': [assignee]})
    result.update(published=True, issue=response['html_url'])
    return result


def check_go(api: GitHub, repository: str, assignee: str, *, publish: bool = False, release_reader=None) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) or not re.fullmatch(r'[A-Za-z0-9-]+', assignee):
        raise ValueError('Expected owner/repository and GitHub assignee login')
    basis = current_go_pin()
    current = basis['version']
    releases = (release_reader or newer_go_releases)(current)
    result = {'status': 'no_update', 'tool': 'Go', 'current': current, 'published': False, 'version_basis': basis}
    if not releases:
        return result
    latest = releases[0]['tag_name']
    evidence = security_evidence(releases)
    marker = f'<!-- codex-skills:sbom-tool-update:go:{latest} -->'
    issues = api.pages(f'/repos/{repository}/issues?state=all&creator=github-actions%5Bbot%5D')
    existing = next((i for i in issues if 'pull_request' not in i and marker in (i.get('body') or '')), None)
    result.update(latest=latest, security=bool(evidence), evidence=evidence)
    if existing and (not evidence or existing['title'].startswith('[安全修補優先]')):
        result.update(status='already_reported', issue=existing['html_url'])
        return result
    priority = '安全修補優先' if evidence else '一般版本更新'
    title = f'[{priority}] Go {latest} 已發布（目前 {current}）'
    lines = [marker, f'@{assignee}，{repository} 追蹤的 Go 有新正式版本。', '',
             f'- 目前最低採用版本／巡檢基準：`{current}`', f'- 最新正式版：`{latest}`',
             f'- 發布日期：{releases[0]["published_at"]}', '- [官方下載及 SHA-256](https://go.dev/dl/)', '']
    if basis['pins']:
        lines += ['專案版本來源（go.mod 為最低需求，toolchain／CI／映像另列）：', '']
        lines += [f'- `{pin["source"]}`：' + ', '.join(pin['versions']) for pin in basis['pins']]
    else:
        lines += ['此專案尚無設定的 Go 版本來源，以 `.github/sbom-tool-monitor.json` 的基準追蹤新版；不表示專案已使用 Go。']
    lines += ['', '建議於 24～48 小時內評估安全修補。' if evidence else '建議納入每月工具更新窗口。', '']
    if evidence:
        lines += ['官方發布紀錄中的安全修補線索（含中間版本；實際影響以官方公告為準）：', '']
        lines += [f'- [{item["version"]}]({item["url"]})：' + (', '.join(item['identifiers']) or '官方紀錄標示安全修補') for item in evidence]
    lines += ['', '尚未採用的正式版本（安全修補優先）：', '']
    lines += [f'- [{r["tag_name"]}]({r["html_url"]}) — {r["published_at"]}' for r in sorted(releases, key=lambda r: not bool(security_evidence([r])))]
    lines += ['', '更新 go.mod／工具模組／CI；有 Go 建置映像時同步固定版本與 digest，重新跑建置、測試及 SBOM，通過後提交推送。',
              '此 Issue 僅通知新版，不會自動升級。已讀的基準通知可關閉，後續同版本不再重複提醒。']
    body = '\n'.join(lines) + '\n'
    result.update(status='security_escalation' if existing else 'update_available', title=title, body=body)
    return publish_issue(api, repository, assignee, existing, title, body, result) if publish else result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY'))
    parser.add_argument('--assignee', default='SimonChung')
    parser.add_argument('--publish', action='store_true', help='Create/update Issues; default is read-only')
    args = parser.parse_args()
    try:
        token = os.environ.get('GH_TOKEN', '')
        if args.publish and not token:
            raise ValueError('GH_TOKEN is required for publishing')
        if not args.repository:
            raise ValueError('Set GITHUB_REPOSITORY or --repository owner/repository')
        api = GitHub(token)
        results = []
        for name, checker in [('Trivy', check), ('Go', check_go)]:
            try:
                item = checker(api, args.repository, args.assignee, publish=args.publish)
                if name == 'Trivy':
                    item['version_basis'] = current_pin()
            except (OSError, ValueError, KeyError, TypeError) as exc:
                item = {'tool': name, 'status': 'failed', 'error': str(exc)}
            results.append(item)
        code = int(any(item['status'] == 'failed' for item in results))
        result = {'status': 'failed' if code else 'ok', 'tools': results}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # Never include request headers or credential values in reports.
        result = {'status': 'failed', 'error': str(exc)}
        code = 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        Path(summary).write_text('## Trivy 與 Go 版本檢查\n\n```json\n' + json.dumps(result, ensure_ascii=False, indent=2) + '\n```\n', encoding='utf-8')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
