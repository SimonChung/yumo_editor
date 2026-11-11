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
        self.pin = patch.object(monitor, 'current_version', return_value='0.76.2')
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
        for releases in [[], [release('unexpected')], [release('v0.76.3', body=None)], [release('v0.76.3', html_url='https://example.org')]]:
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
        with patch.object(monitor.GitHub, 'pages', side_effect=error), patch('sys.argv', ['check', '--repository', REPO]), patch('sys.stdout', new_callable=io.StringIO) as out:
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
            'schema_version': 1, 'pin_sources': sources, **extra}))

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

    def test_baseline_is_explicit_and_optional_source_takes_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, [{'kind': 'go_version_guard', 'path': 'image.go', 'optional': True}], baseline='0.76.2')
            self.assertEqual(monitor.current_pin(root)['mode'], 'release_baseline')
            (root / 'image.go').write_text('if tool.Version != "0.77.0" {\n')
            self.assertEqual(monitor.current_pin(root), {'mode': 'scanner_pin', 'version': '0.77.0', 'sources': ['image.go']})
            (root / 'image.go').write_text('invalid guard')
            with self.assertRaises(ValueError):
                monitor.current_pin(root)

    def test_missing_required_source_cannot_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, [{'kind': 'trivy_image', 'path': 'missing'}], baseline='0.76.2')
            with self.assertRaises(FileNotFoundError):
                monitor.current_pin(root)
            self.config(root, [])
            with self.assertRaises(ValueError):
                monitor.current_pin(root)

    def test_source_traversal_and_disagreement_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.config(root, [{'kind': 'trivy_image', 'path': '../outside', 'optional': True}])
            with self.assertRaises(ValueError):
                monitor.current_pin(root)
            for filename, value in [('a', '0.76.2'), ('b', '0.76.3')]:
                (root / filename).write_text('aquasec/trivy:' + value + '@' + DIGEST)
            self.config(root, [{'kind': 'trivy_image', 'path': filename} for filename in ['a', 'b']])
            with self.assertRaises(ValueError):
                monitor.current_pin(root)


if __name__ == '__main__':
    unittest.main()
