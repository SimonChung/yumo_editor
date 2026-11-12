import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location('tool_versions', Path(__file__).resolve().parents[2] / 'scripts/check_sbom_tool_versions.py')
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)

DIGEST = 'sha256:' + 'a' * 64
REPO = 'example/skills'


def release(tag, body='Bug fixes', **kwargs):
    return {'tag_name': tag, 'name': tag, 'body': body, 'draft': False, 'prerelease': False,
            'published_at': '2026-11-12T01:00:00Z',
            'html_url': f'https://github.com/aquasecurity/trivy/releases/tag/{tag}', **kwargs}


class FakeGitHub:
    def __init__(self, releases, issues=None, comments=None):
        self.releases = releases
        self.issues = issues or []
        self.comments = comments or []
        self.writes = []

    def pages(self, path):
        if path.endswith('/releases'):
            return self.releases
        if path.endswith('/comments'):
            return self.comments
        if '/issues?' in path:
            return self.issues
        raise AssertionError(path)

    def request(self, path, *, data=None, method='GET'):
        self.writes.append((method, path, data))
        return {'html_url': 'https://github.com/example/skills/issues/12'}


class VersionMonitorTests(unittest.TestCase):
    def setUp(self):
        self.pin = patch.object(monitor, 'current_pin', return_value={'mode': 'scanner_pin', 'version': '0.76.2', 'sources': ['scanner.py']})
        self.pin.start()
        self.addCleanup(self.pin.stop)

    def run_check(self, api, publish=True):
        return monitor.check(api, REPO, 'example', publish=publish, digest_reader=lambda _: DIGEST)

    def issue(self, security=False, **kwargs):
        return {'number': 12, 'title': '[安全修補優先] Trivy' if security else '[一般版本更新] Trivy',
                'body': '<!-- codex-skills:sbom-tool-update:trivy:0.76.3 -->',
                'html_url': 'https://github.com/example/skills/issues/12', **kwargs}

    def test_no_new_version_performs_no_writes_or_registry_request(self):
        api = FakeGitHub([release('v0.76.2'), release('v0.76.1')])
        def unexpected(_):
            self.fail('No candidate should query the registry')
        result = monitor.check(api, REPO, 'example', publish=True, digest_reader=unexpected)
        self.assertEqual(result['status'], 'no_update')
        self.assertEqual(api.writes, [])

    def test_semver_numeric_order_and_unstable_releases(self):
        releases = [release('v0.9.0'), release('v0.10.0'), release('v0.11.0-rc.1', prerelease=True), release('v9.0.0', draft=True)]
        self.assertEqual([r['tag_name'] for r in monitor.newer_releases(releases, '0.8.0')], ['v0.10.0', 'v0.9.0'])

    def test_empty_or_malformed_release_data_fails(self):
        for releases in [[], [None], [release('unexpected')], [release('v0.76.3', body=None)], [release('v0.76.3', html_url='https://example.org')]]:
            with self.subTest(releases=releases), self.assertRaises(ValueError):
                self.run_check(FakeGitHub(releases))

    def test_new_version_creates_assigned_issue(self):
        api = FakeGitHub([release('v0.76.3')])
        result = self.run_check(api)
        self.assertTrue(result['published'])
        self.assertEqual(len(api.writes), 1)
        self.assertEqual(api.writes[0][:2], ('POST', '/repos/example/skills/issues'))
        payload = api.writes[0][2]
        self.assertEqual(payload['assignees'], ['example'])
        self.assertIn('0.76.3@' + DIGEST, payload['body'])
        self.assertIn('@example', payload['body'])
        self.assertIn(REPO, payload['body'])
        self.assertNotIn('codex-skills 的', payload['body'])

    def test_dry_run_is_read_only_even_with_new_release(self):
        api = FakeGitHub([release('v0.76.3')])
        self.assertEqual(self.run_check(api, publish=False)['status'], 'update_available')
        self.assertEqual(api.writes, [])

    def test_security_in_intermediate_release_has_priority(self):
        api = FakeGitHub([release('v0.77.0'), release('v0.76.3', 'Security update fixes CVE-2026-12345')])
        result = self.run_check(api)
        self.assertTrue(result['security'])
        self.assertTrue(result['title'].startswith('[安全修補優先]'))
        self.assertIn('CVE-2026-12345', result['body'])

    def test_open_and_closed_issues_are_deduplicated(self):
        for state in ['open', 'closed']:
            with self.subTest(state=state):
                api = FakeGitHub([release('v0.76.3')], [self.issue(state=state)])
                self.assertEqual(self.run_check(api)['status'], 'already_reported')
                self.assertEqual(api.writes, [])

    def test_pull_request_does_not_suppress_issue(self):
        api = FakeGitHub([release('v0.76.3')], [self.issue(pull_request={})])
        self.assertEqual(self.run_check(api)['status'], 'update_available')
        self.assertEqual(len(api.writes), 1)

    def test_security_escalates_existing_issue_once(self):
        api = FakeGitHub([release('v0.76.3', 'Security patch')], [self.issue()])
        self.assertEqual(self.run_check(api)['status'], 'security_escalation')
        self.assertEqual([w[0] for w in api.writes], ['POST', 'PATCH'])
        api = FakeGitHub([release('v0.76.3', 'Security patch')], [self.issue(security=True)])
        self.assertEqual(self.run_check(api)['status'], 'already_reported')
        self.assertEqual(api.writes, [])

    def test_escalation_retry_does_not_repeat_comment(self):
        api = FakeGitHub([release('v0.76.3', 'Security patch')], [self.issue()],
                         [{'body': '<!-- codex-skills:sbom-security-escalation -->'}])
        self.run_check(api)
        self.assertEqual([w[0] for w in api.writes], ['PATCH'])

    def test_registry_failure_leaves_issues_unchanged(self):
        api = FakeGitHub([release('v0.76.3')])
        def broken(_):
            raise OSError('Registry unavailable')
        with self.assertRaises(OSError):
            monitor.check(api, REPO, 'example', publish=True, digest_reader=broken)
        self.assertEqual(api.writes, [])

    def test_github_failure_is_nonzero_and_not_no_update(self):
        error = HTTPError('https://api.github.com/repos/example/skills', 403, 'Forbidden', {}, None)
        self.addCleanup(error.close)
        with patch.object(monitor.GitHub, 'pages', side_effect=error), patch.object(monitor, 'check_go', return_value={'tool': 'Go', 'status': 'no_update'}), patch('sys.argv', ['check', '--repository', REPO]), patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(monitor.main(), 1)
        self.assertEqual(json.loads(out.getvalue())['status'], 'failed')

    def test_pagination_does_not_silently_drop_closed_issues(self):
        api = monitor.GitHub()
        with patch.object(api, 'request', side_effect=[[{'number': i} for i in range(100)], [{'number': 101}]]) as request:
            self.assertEqual(len(api.pages('/repos/example/skills/issues?state=all')), 101)
        self.assertIn('&per_page=100&page=2', request.call_args[0][0])

    def test_digest_requires_exact_bytes_and_both_platforms(self):
        data = {'manifests': [{'platform': {'os': 'linux', 'architecture': arch}} for arch in ['amd64', 'arm64']]}
        raw = json.dumps(data).encode()
        class Response(io.BytesIO):
            headers = {'Docker-Content-Digest': 'sha256:' + monitor.hashlib.sha256(raw).hexdigest()}
        with patch.object(monitor, 'request_json', return_value={'token': 'registry-token'}), patch.object(monitor, 'urlopen', return_value=Response(raw)):
            self.assertEqual(monitor.image_digest('0.76.3'), Response.headers['Docker-Content-Digest'])
        Response.headers = {'Docker-Content-Digest': DIGEST}
        with patch.object(monitor, 'request_json', return_value={'token': 'registry-token'}), patch.object(monitor, 'urlopen', return_value=Response(raw)), self.assertRaises(ValueError):
            monitor.image_digest('0.76.3')
        raw = json.dumps({'manifests': [{'platform': {'os': 'linux', 'architecture': 'amd64'}}]}).encode()
        Response.headers = {'Docker-Content-Digest': 'sha256:' + monitor.hashlib.sha256(raw).hexdigest()}
        with patch.object(monitor, 'request_json', return_value={'token': 'registry-token'}), patch.object(monitor, 'urlopen', return_value=Response(raw)), self.assertRaises(ValueError):
            monitor.image_digest('0.76.3')


class ScannerPinTests(unittest.TestCase):
    def config(self, root, sources, **extra):
        (root / '.github').mkdir(exist_ok=True)
        (root / '.github/sbom-tool-monitor.json').write_text(json.dumps({
            'schema_version': 2, 'tools': {'trivy': {'pin_sources': sources, **extra}}}))

    def test_pin_is_read_without_executing_script(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'scanner.py'
            path.write_text("raise Exception('must not execute')\nSCANNER = 'aquasec/trivy:0.76.2@" + DIGEST + "'\n")
            self.assertEqual(monitor.current_version(path), '0.76.2')
            path.write_text("SCANNER = 'aquasec/trivy:latest'\n")
            with self.assertRaises(ValueError):
                monitor.current_version(path)

    def test_powershell_source_follows_actual_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'verify.ps1'
            self.config(root, [{'kind': 'trivy_image', 'path': 'verify.ps1'}])
            source.write_text("$scanner = 'aquasec/trivy:0.76.3@" + DIGEST + "'\n")
            self.assertEqual(monitor.current_pin(root)['version'], '0.76.3')
            source.write_text("$scanner = 'aquasec/trivy:latest'\n")
            with self.assertRaises(ValueError):
                monitor.current_pin(root)

    def test_go_version_guard_is_required_and_follows_actual_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, [{'kind': 'go_version_guard', 'path': 'image.go'}])
            with self.assertRaises(FileNotFoundError):
                monitor.current_pin(root)
            (root / 'image.go').write_text('if tool.Version != "0.77.0" {\n')
            self.assertEqual(monitor.current_pin(root), {'mode': 'scanner_pin', 'version': '0.77.0', 'sources': ['image.go']})
            (root / 'image.go').write_text('invalid guard')
            with self.assertRaises(ValueError):
                monitor.current_pin(root)

    def test_missing_required_source_cannot_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, [{'kind': 'trivy_image', 'path': 'missing'}])
            with self.assertRaises(FileNotFoundError):
                monitor.current_pin(root)
            self.config(root, [])
            with self.assertRaises(ValueError):
                monitor.current_pin(root)

    def test_source_traversal_and_disagreement_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, [{'kind': 'trivy_image', 'path': '../outside'}])
            with self.assertRaises(ValueError):
                monitor.current_pin(root)
            for filename, value in [('a', '0.76.2'), ('b', '0.76.3')]:
                (root / filename).write_text('aquasec/trivy:' + value + '@' + DIGEST)
            self.config(root, [{'kind': 'trivy_image', 'path': filename} for filename in ['a', 'b']])
            with self.assertRaises(ValueError):
                monitor.current_pin(root)


def go_release(value, body='Bug fixes'):
    return {'tag_name': value, 'name': 'go' + value, 'body': body,
            'published_at': '2026-11-12', 'html_url': monitor.GO_HISTORY + '#go' + value}


def download(value, stable=True):
    return {'version': 'go' + value, 'stable': stable,
            'files': [{'kind': 'source', 'version': 'go' + value, 'sha256': 'a' * 64}]}


def history(value, body='Bug fixes', tag='p'):
    return f'<{tag} id="go{value}">go{value} (released 2026-11-12) {body}</{tag}>'


class GoPinTests(unittest.TestCase):
    def config(self, root, sources, **extra):
        (root / '.github').mkdir(exist_ok=True)
        (root / '.github/sbom-tool-monitor.json').write_text(json.dumps({
            'schema_version': 2, 'tools': {'go': {'pin_sources': sources, **extra}}}))

    def test_module_version_requires_an_actual_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, [{'kind': 'go_mod', 'path': 'go.mod'}])
            with self.assertRaises(FileNotFoundError):
                monitor.current_go_pin(root)
            (root / 'go.mod').write_text('module demo\ngo 1.27.5\n')
            self.assertEqual(monitor.current_go_pin(root)['version'], '1.27.5')
            self.assertEqual(monitor.current_go_pin(root)['mode'], 'go_pins')

    def test_all_module_toolchain_ci_and_image_versions_are_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'go.mod').write_text('module demo\ngo 1.27.4 // minimum\ntoolchain go1.27.5\n')
            (root / 'ci.yml').write_text("    go-version: '1.27.5'\n")
            (root / 'Dockerfile').write_text('FROM --platform=$BUILDPLATFORM golang:1.27.3-bookworm@' + DIGEST + ' AS build\n')
            self.config(root, [{'kind': kind, 'path': path} for kind, path in [('go_mod', 'go.mod'), ('go_ci', 'ci.yml'), ('go_image', 'Dockerfile')]])
            pin = monitor.current_go_pin(root)
            self.assertEqual(pin['version'], '1.27.3')
            self.assertEqual(pin['versions'], ['1.27.3', '1.27.4', '1.27.5'])
            self.assertEqual(len(pin['pins']), 3)

    def test_required_missing_invalid_and_unconfigured_sources_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, [{'kind': 'go_mod', 'path': 'go.mod'}])
            with self.assertRaises(FileNotFoundError):
                monitor.current_go_pin(root)
            for text in ['module demo', 'go 1.27rc1', 'go 1.27.4\ngo 1.27.5', 'go 1.27.4\ntoolchain go1.28rc1']:
                (root / 'go.mod').write_text(text + '\n')
                with self.subTest(text=text), self.assertRaises(ValueError):
                    monitor.current_go_pin(root)
            self.config(root, [])
            with self.assertRaises(ValueError):
                monitor.current_go_pin(root)

    def test_source_escape_and_non_exact_ci_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, [{'kind': 'go_mod', 'path': '../outside'}])
            with self.assertRaises(ValueError):
                monitor.current_go_pin(root)
            for kind, text in [('go_ci', 'go-version: stable'), ('go_ci', 'go-version: 1.27.x'), ('go_image', 'FROM golang:latest')]:
                (root / 'source').write_text(text)
                self.config(root, [{'kind': kind, 'path': 'source'}])
                with self.subTest(text=text), self.assertRaises(ValueError):
                    monitor.current_go_pin(root)

    def test_minor_go_directive_and_default_toolchain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, [{'kind': 'go_mod', 'path': 'go.mod'}])
            (root / 'go.mod').write_text('go 1.27\ntoolchain default\n')
            self.assertEqual(monitor.current_go_pin(root)['versions'], ['1.27.0'])


class GoReleaseTests(unittest.TestCase):
    def releases(self, downloads, html, current='1.27.4'):
        with patch.object(monitor, 'request_json', return_value=downloads), patch.object(monitor, 'request_text', return_value=html):
            return monitor.newer_go_releases(current)

    def test_no_new_stable_release_skips_history_and_prereleases(self):
        with patch.object(monitor, 'request_json', return_value=[download('1.27.4'), download('1.28rc1', False)]), patch.object(monitor, 'request_text') as read:
            self.assertEqual(monitor.newer_go_releases('1.27.4'), [])
            read.assert_not_called()

    def test_numeric_order_and_intermediate_security_with_html(self):
        html = ''.join(history(f'1.27.{n}', 'security\n<b>fixes</b>' if n == 5 else 'bug fixes') for n in range(4, 11))
        releases = self.releases([download('1.27.9'), download('1.27.10')], html)
        self.assertEqual(releases[0]['tag_name'], '1.27.10')
        self.assertEqual([r['version'] for r in monitor.security_evidence(releases)], ['1.27.5'])

    def test_new_major_release_and_old_branch_security_patch(self):
        html = history('1.27.4') + history('1.27.5', 'security fixes') + history('1.28.0', tag='h2')
        releases = self.releases([download('1.28.0'), download('1.27.5')], html)
        self.assertEqual(releases[0]['tag_name'], '1.28.0')
        self.assertEqual(monitor.security_evidence(releases)[0]['version'], '1.27.5')

    def test_old_unreleased_history_entry_does_not_break_current_interval(self):
        html = '<p id="go1.7.2">This release was never published.</p>' + history('1.27.4') + history('1.27.5', 'security fixes')
        releases = self.releases([download('1.27.5')], html)
        self.assertEqual(monitor.security_evidence(releases)[0]['version'], '1.27.5')

    def test_supported_branch_patch_cannot_disappear_from_history(self):
        html = history('1.27.4') + history('1.28.0', tag='h2')
        with self.assertRaises(ValueError):
            self.releases([download('1.28.0'), download('1.27.5')], html)

    def test_empty_or_incomplete_downloads_fail(self):
        for downloads in [[], {}, [None], [download('1.28rc1', False)], [download('1.27.5') | {'files': []}], [download('1.27.5') | {'files': [None]}], [download('1.27.5') | {'stable': None}], [download('1.28rc1')]]:
            with self.subTest(downloads=downloads), self.assertRaises(ValueError):
                self.releases(downloads, '')

    def test_missing_latest_current_patch_or_malformed_history_fails(self):
        for html in ['', history('1.27.5'), history('1.27.4'), history('1.27.4') + history('1.27.6'),
                     history('1.27.4') + history('1.27.5') * 2,
                     history('1.27.4') + '<p id="go1.27.5">truncated',
                     history('1.27.4') + '<p id="go1.27.5">no date</p>']:
            latest = '1.27.6' if 'go1.27.6' in html else '1.27.5'
            with self.subTest(html=html), self.assertRaises(ValueError):
                self.releases([download(latest)], html)

    def test_history_failure_is_not_no_update(self):
        with patch.object(monitor, 'request_json', return_value=[download('1.27.5')]), patch.object(monitor, 'request_text', side_effect=OSError('offline')), self.assertRaises(OSError):
            monitor.newer_go_releases('1.27.4')


class GoNotificationTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(monitor, 'current_go_pin', return_value={
            'mode': 'go_pins', 'version': '1.27.4', 'versions': ['1.27.4'],
            'pins': [{'source': 'go.mod', 'versions': ['1.27.4']}]})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_check(self, api, releases, publish=True):
        return monitor.check_go(api, REPO, 'example', publish=publish, release_reader=lambda _: releases)

    def issue(self, security=False, **extra):
        return {'number': 15, 'title': '[安全修補優先] Go' if security else '[一般版本更新] Go',
                'body': '<!-- codex-skills:sbom-tool-update:go:1.27.5 -->',
                'html_url': 'https://github.com/example/skills/issues/15', **extra}

    def test_no_update_is_silent_and_needs_no_issue_access(self):
        api = FakeGitHub([])
        with patch.object(api, 'pages', side_effect=AssertionError('No issue access expected')):
            self.assertEqual(self.run_check(api, [])['status'], 'no_update')
        self.assertEqual(api.writes, [])

    def test_new_release_issue_is_assigned_and_separate_from_trivy(self):
        api = FakeGitHub([], [{'body': '<!-- codex-skills:sbom-tool-update:trivy:1.27.5 -->'}])
        result = self.run_check(api, [go_release('1.27.5')])
        self.assertTrue(result['published'])
        self.assertEqual(len(api.writes), 1)
        payload = api.writes[0][2]
        self.assertEqual(payload['assignees'], ['example'])
        self.assertIn('go.mod', payload['body'])
        self.assertIn('Go 1.27.5', payload['title'])

    def test_closed_open_and_pr_deduplication(self):
        for state in ['open', 'closed']:
            api = FakeGitHub([], [self.issue(state=state)])
            self.assertEqual(self.run_check(api, [go_release('1.27.5')])['status'], 'already_reported')
            self.assertEqual(api.writes, [])
        api = FakeGitHub([], [self.issue(pull_request={})])
        self.assertTrue(self.run_check(api, [go_release('1.27.5')])['published'])

    def test_intermediate_security_has_priority(self):
        result = self.run_check(FakeGitHub([]), [go_release('1.27.6'), go_release('1.27.5', 'security fixes')])
        self.assertTrue(result['title'].startswith('[安全修補優先]'))
        self.assertIn('#go1.27.5', result['body'])

    def test_security_escalation_and_retry_once_even_after_close(self):
        releases = [go_release('1.27.5', 'security fixes')]
        api = FakeGitHub([], [self.issue(state='closed')])
        self.assertEqual(self.run_check(api, releases)['status'], 'security_escalation')
        self.assertEqual([w[0] for w in api.writes], ['POST', 'PATCH'])
        api = FakeGitHub([], [self.issue()], [{'body': '<!-- codex-skills:sbom-security-escalation -->'}])
        self.run_check(api, releases)
        self.assertEqual([w[0] for w in api.writes], ['PATCH'])
        api = FakeGitHub([], [self.issue(security=True)])
        self.assertEqual(self.run_check(api, releases)['status'], 'already_reported')
        self.assertEqual(api.writes, [])

    def test_dry_run_is_read_only_and_uses_actual_source(self):
        api = FakeGitHub([])
        result = self.run_check(api, [go_release('1.27.5')], publish=False)
        self.assertIn('go.mod', result['body'])
        self.assertNotIn('基準', result['body'])
        self.assertFalse(result['published'])
        self.assertEqual(api.writes, [])

    def test_failed_trivy_does_not_prevent_go_check(self):
        with patch.object(monitor, 'check', side_effect=OSError('offline')), patch.object(monitor, 'check_go', return_value={'tool': 'Go', 'status': 'no_update'}) as go, patch('sys.argv', ['check', '--repository', REPO]), patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(monitor.main(), 1)
            go.assert_called_once()
            result = json.loads(out.getvalue())
            self.assertEqual([t['status'] for t in result['tools']], ['failed', 'no_update'])

    def test_failed_go_preserves_trivy_result_and_fails_workflow(self):
        with patch.object(monitor, 'check', return_value={'tool': 'Trivy', 'status': 'no_update'}), patch.object(monitor, 'current_pin', return_value={}), patch.object(monitor, 'check_go', side_effect=ValueError('bad Go metadata')), patch('sys.argv', ['check', '--repository', REPO]), patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(monitor.main(), 1)
            self.assertEqual([t['status'] for t in json.loads(out.getvalue())['tools']], ['no_update', 'failed'])


class ActualToolTests(unittest.TestCase):
    def config(self, root, tools):
        (root / '.github').mkdir(exist_ok=True)
        (root / '.github/sbom-tool-monitor.json').write_text(json.dumps({'schema_version': 2, 'tools': tools}))

    def test_no_tools_performs_no_network_requests_or_issue_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, {})
            with patch.object(monitor, 'ROOT', root), patch.object(monitor, 'urlopen', side_effect=AssertionError('Unused tools must not access the network')), patch('sys.argv', ['check', '--repository', REPO, '--publish']), patch.dict(monitor.os.environ, {'GH_TOKEN': 'test-only'}), patch('sys.stdout', new_callable=io.StringIO) as out:
                self.assertEqual(monitor.main(), 0)
            tools = json.loads(out.getvalue())['tools']
            self.assertEqual([t['status'] for t in tools], ['not_used', 'not_used'])
            self.assertTrue(all(not t['published'] and 'current' not in t for t in tools))

    def test_trivy_only_never_checks_go(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, {'trivy': {'pin_sources': [{'kind': 'trivy_image', 'path': 'scanner'}]}})
            (root / 'scanner').write_text('aquasec/trivy:0.76.2@' + DIGEST)
            api = FakeGitHub([release('v0.76.3')])
            with patch.object(monitor, 'ROOT', root), patch.object(monitor, 'newer_go_releases', side_effect=AssertionError('Go is unused')):
                self.assertEqual(monitor.check_go(api, REPO, 'example', publish=True)['status'], 'not_used')
                self.assertTrue(monitor.check(api, REPO, 'example', publish=True, digest_reader=lambda _: DIGEST)['published'])
            self.assertEqual(len(api.writes), 1)
            self.assertIn('Trivy', api.writes[0][2]['title'])

    def test_go_only_never_checks_trivy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, {'go': {'pin_sources': [{'kind': 'go_mod', 'path': 'go.mod'}]}})
            (root / 'go.mod').write_text('module demo\ngo 1.27.4\n')
            api = FakeGitHub([])
            with patch.object(monitor, 'ROOT', root), patch.object(api, 'pages', side_effect=AssertionError('Trivy is unused')):
                self.assertEqual(monitor.check(api, REPO, 'example', publish=True)['status'], 'not_used')
                self.assertEqual(monitor.check_go(api, REPO, 'example', release_reader=lambda _: [])['status'], 'no_update')
            self.assertEqual(api.writes, [])

    def test_baselines_optional_sources_and_typos_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for settings in [{'pin_sources': [], 'baseline': '1.27.4'}, {'pin_sources': [{'kind': 'go_mod', 'path': 'go.mod', 'optional': True}]}, {'pin_sources': []}]:
                self.config(root, {'go': settings})
                with self.subTest(settings=settings), self.assertRaises(ValueError):
                    monitor.current_go_pin(root)
            self.config(root, {'Go': {'pin_sources': []}})
            with self.assertRaises(ValueError):
                monitor.current_go_pin(root)
            (root / '.github/sbom-tool-monitor.json').write_text(json.dumps({'schema_version': 1, 'pin_sources': [], 'baseline': '0.76.2'}))
            with self.assertRaises(ValueError):
                monitor.current_pin(root)

    def test_enabled_missing_source_fails_instead_of_becoming_unused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, {'go': {'pin_sources': [{'kind': 'go_mod', 'path': 'missing.go.mod'}]}})
            with patch.object(monitor, 'ROOT', root), patch.object(monitor, 'urlopen', side_effect=AssertionError('No request after a source failure')), patch('sys.argv', ['check', '--repository', REPO]), patch('sys.stdout', new_callable=io.StringIO) as out:
                self.assertEqual(monitor.main(), 1)
            self.assertEqual([t['status'] for t in json.loads(out.getvalue())['tools']], ['not_used', 'failed'])


if __name__ == '__main__':
    unittest.main()
