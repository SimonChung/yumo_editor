import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import check_project_tool_versions as monitor


def release(value, body='', date='2026-11-13T00:00:00Z'):
    return monitor.entry(value, 'https://example.org/releases/' + value, body, date)


class FakeGitHub:
    def __init__(self, releases=None, issues=None, comments=None):
        self.releases = releases or []
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

    def request(self, path, *, method='GET', data=None):
        self.writes.append((method, path, data))
        return {'html_url': 'https://github.com/example/project/issues/1'}


class ProjectToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tool.txt').write_text('tool=1.2.3\n')
        self.pin = {'mode': 'pin', 'sources': [{'path': 'tool.txt', 'pattern': r'tool=(?P<version>\S+)'}]}
        self.watch = {'mode': 'watch', 'sources': [{'path': 'tool.txt', 'pattern': 'tool='}],
                      'started_at': '2026-11-12T01:00:00Z', 'initial_versions': []}

    def check(self, releases, config=None, api=None, publish=True, tool='powershell'):
        api = api or FakeGitHub()
        with patch.object(monitor, 'read_releases', return_value=releases):
            return monitor.check_tool(api, 'example/project', 'example', tool, config or self.pin, root=self.root, publish=publish), api

    def test_numeric_order_and_preview_transition(self):
        key = monitor.release_key
        self.assertLess(key('1.9'), key('1.10'))
        self.assertEqual(key('1.0'), key('v1.0.0'))
        self.assertLess(key('3.0.0-beta.9'), key('3.0.0-beta.30'))
        self.assertLess(key('3.0.0-rc.1'), key('3.0.0'))
        self.assertLess(key('2025.9.1'), key('2026.1.1'))
        self.assertLess(key('1.0.0'), key('1.0.0.post1'))
        self.assertLess(key('1.0.0.dev1'), key('1.0.0a1'))
        for invalid in ['latest', '^3.0.0', '3.2.0-nightly.20261112']:
            with self.assertRaises(ValueError):
                key(invalid)

    def test_reads_actual_pin_without_executing_source(self):
        (self.root / 'tool.txt').write_text('raise Exception("never execute")\ntool=1.4.0\n')
        self.assertEqual(monitor.source_basis('powershell', self.pin, self.root)['version'], '1.4.0')

    def test_json_pointer_uses_resolved_lock_version(self):
        (self.root / 'lock.json').write_text(json.dumps({'packages': {'node_modules/vite': {'version': '8.3.4'}}}))
        config = {'mode': 'pin', 'sources': [{'path': 'lock.json', 'pointer': ['packages', 'node_modules/vite', 'version']}]}
        self.assertEqual(monitor.source_basis('vite', config, self.root)['version'], '8.3.4')

    def test_missing_source_or_usage_is_failure_not_skip(self):
        (self.root / 'tool.txt').unlink()
        with self.assertRaises(FileNotFoundError):
            monitor.source_basis('powershell', self.watch, self.root)
        (self.root / 'tool.txt').write_text('no longer used')
        with self.assertRaises(ValueError):
            monitor.source_basis('powershell', self.watch, self.root)

    def test_paths_cannot_escape_repository(self):
        for path in ['../tool.txt', '/etc/passwd']:
            config = self.pin | {'sources': [{'path': path, 'pattern': 'tool='}]}
            with self.assertRaises(ValueError):
                monitor.source_basis('powershell', config, self.root)

    def test_missing_required_fields_and_unapproved_baselines_fail(self):
        for config in [self.pin | {'baseline': '1.2.3'}, self.watch | {'sources': []}, self.pin | {'channel': 'all'}, {'mode': 'watch', 'sources': self.pin['sources']}]:
            with self.assertRaises(ValueError):
                monitor.source_basis('powershell', config, self.root)

    def test_watch_never_invents_installed_version(self):
        basis = monitor.source_basis('powershell', self.watch, self.root)
        self.assertIsNone(basis['installed_version'])
        self.assertNotIn('version', basis)

    def test_watch_first_run_is_quiet(self):
        api = FakeGitHub()
        with patch.object(api, 'pages', side_effect=AssertionError('must not query Issues')):
            result, _ = self.check([release('1.3.0', date='2026-11-10T00:00:00Z')], self.watch, api)
        self.assertEqual(result['status'], 'no_update')
        self.assertEqual(api.writes, [])

    def test_watch_new_release_is_notified(self):
        result, api = self.check([release('1.3.0')], self.watch)
        self.assertTrue(result['published'])
        self.assertIn('未固定安裝版本', result['body'])
        self.assertIn('project-tool-release:powershell:1.3.0', result['body'])
        self.assertEqual(api.writes[0][0], 'POST')

    def test_watch_undated_inventory_detects_new_versions_only(self):
        config = self.watch | {'initial_versions': ['1.2.3']}
        basis = monitor.source_basis('powershell', config, self.root)
        candidates = monitor.candidates([release('1.2.4', date=None), release('1.2.3', date=None)], config, basis)
        self.assertEqual([r['version'] for r in candidates], ['1.2.4'])

    def test_watch_older_branch_security_release_is_not_suppressed(self):
        issue = {'number': 1, 'title': '[一般版本更新]', 'body': '<!-- project-tool-release:powershell:8.0.0 -->', 'state': 'closed'}
        api = FakeGitHub(issues=[issue])
        result, api = self.check([release('8.0.0'), release('7.4.9', 'Security patch CVE-2026-1234')], self.watch, api)
        self.assertEqual(result['latest'], '7.4.9')
        self.assertTrue(result['security'])
        self.assertEqual(len(api.writes), 1)

    def test_watch_deduplicates_all_versions_in_closed_issue(self):
        api = FakeGitHub(issues=[{'body': '<!-- project-tool-release:powershell:1.3.0 -->', 'state': 'closed'}])
        result, api = self.check([release('1.3.0')], self.watch, api)
        self.assertEqual(result['status'], 'already_reported')
        self.assertEqual(api.writes, [])

    def test_pin_no_update_is_quiet(self):
        result, api = self.check([release('1.2.3')])
        self.assertEqual(result['status'], 'no_update')
        self.assertEqual(api.writes, [])

    def test_security_in_intermediate_version_has_priority(self):
        result, _ = self.check([release('1.4.0'), release('1.3.0', 'Security patch CVE-2026-1234')])
        self.assertTrue(result['title'].startswith('[安全修補優先]'))
        self.assertIn('CVE-2026-1234', result['body'])

    def test_dry_run_never_writes(self):
        result, api = self.check([release('1.4.0')], publish=False)
        self.assertEqual(result['status'], 'update_available')
        self.assertEqual(api.writes, [])

    def test_floating_major_handles_future_patches_and_major_upgrade(self):
        config = self.pin | {'mode': 'major', 'started_at': self.watch['started_at']}
        basis = monitor.source_basis('powershell', config, self.root)
        values = [release('2.0.0', date='2026-01-01T00:00:00Z'), release('1.4.0'), release('1.3.0', date='2026-11-01T00:00:00Z')]
        self.assertEqual([r['version'] for r in monitor.candidates(values, config, basis)], ['2.0.0', '1.4.0'])

    def test_installed_preview_channel_does_not_adopt_other_previews(self):
        (self.root / 'tool.txt').write_text('tool=3.0.0-beta.30\n')
        config = self.pin | {'channel': 'installed-preview'}
        basis = monitor.source_basis('wails', config, self.root)
        values = [release('4.0.0-beta.1'), release('3.1.0'), release('3.0.0'), release('3.0.0-beta.31'), release('2.12.0')]
        self.assertEqual([r['version'] for r in monitor.candidates(values, config, basis)], ['3.1.0', '3.0.0', '3.0.0-beta.31'])

    def test_stable_install_ignores_prereleases(self):
        result, _ = self.check([release('2.0.0-beta.1'), release('1.2.3')])
        self.assertEqual(result['status'], 'no_update')

    def test_osv_fixed_version_prioritizes_security(self):
        advisory = {'vulns': [{'id': 'GHSA-test', 'affected': [{'package': {'name': 'vite'}, 'ranges': [{'events': [{'introduced': '0'}, {'fixed': '1.3.0'}]}]}]}]}
        with patch.object(monitor.core, 'request_json', return_value=advisory):
            result, _ = self.check([release('1.4.0')], tool='vite')
        self.assertTrue(result['security'])
        self.assertIn('GHSA-test', result['body'])

    def test_advisory_failure_never_sends_general_notification(self):
        api = FakeGitHub()
        with patch.object(monitor.core, 'request_json', side_effect=OSError('OSV unavailable')):
            with self.assertRaises(OSError):
                self.check([release('1.4.0')], tool='vite', api=api)
        self.assertEqual(api.writes, [])

    def test_security_escalation_is_deduplicated(self):
        issue = {'number': 1, 'title': '[一般版本更新]', 'body': '<!-- codex-skills:sbom-tool-update:powershell:1.4.0 -->', 'html_url': 'https://example.org/1'}
        api = FakeGitHub(issues=[issue])
        result, api = self.check([release('1.4.0', 'Security patch')], api=api)
        self.assertEqual(result['status'], 'security_escalation')
        self.assertEqual([w[0] for w in api.writes], ['POST', 'PATCH'])
        issue['title'] = '[安全修補優先]'
        issue['body'] = result['body']
        result, api = self.check([release('1.4.0', 'Security patch')], api=FakeGitHub(issues=[issue]))
        self.assertEqual(result['status'], 'already_reported')
        self.assertEqual(api.writes, [])


class ProviderTests(unittest.TestCase):
    def test_pypi_yanked_and_invalid_versions_are_ignored(self):
        data = {'releases': {'1.0.0': [{'yanked': False, 'upload_time_iso_8601': '2026-01-01T00:00:00Z'}], '2.0.0': [{'yanked': True}], 'invalid': []}}
        with patch.object(monitor, 'read_json', return_value=data):
            self.assertEqual([r['version'] for r in monitor.read_releases('pypi-pip', None)], ['1.0.0'])

    def test_npm_lock_packages_and_deprecated_releases(self):
        data = {'versions': {'1.0.0': {}, '2.0.0': {'deprecated': 'withdrawn'}}, 'time': {'1.0.0': '2026-01-01T00:00:00Z'}}
        with patch.object(monitor, 'read_json', return_value=data):
            self.assertEqual(monitor.read_releases('vite-react', None)[0]['version'], '1.0.0')

    def test_empty_or_malformed_inventory_fails(self):
        with patch.object(monitor, 'read_json', return_value={'releases': {}}), self.assertRaises(ValueError):
            monitor.read_releases('pypi-pip', None)
        with patch.object(monitor, 'read_json', return_value={}), self.assertRaises(KeyError):
            monitor.read_releases('vite', None)

    def test_github_drafts_and_source_url_are_checked(self):
        data = [{'tag_name': 'v1.0.0', 'body': '', 'published_at': '2026-01-01T00:00:00Z', 'html_url': 'https://github.com/PowerShell/PowerShell/releases/tag/v1.0.0'}, {'draft': True}]
        with patch.object(monitor, 'github_releases', return_value=data):
            self.assertEqual(monitor.read_releases('powershell', None)[0]['version'], '1.0.0')
            data[0]['html_url'] = 'https://example.org/forged'
            with self.assertRaises(ValueError):
                monitor.read_releases('powershell', None)

    def test_android_sdk_excludes_preview_and_obsolete(self):
        xml = '<sdk-repository>' + ''.join(f'<remotePackage path="build-tools;{v}"><revision><major>{v}</major>{extra}</revision><channelRef ref="{channel}"/>{obsolete}</remotePackage>' for v, extra, channel, obsolete in [('36', '', 'channel-0', ''), ('37', '<preview>1</preview>', 'channel-0', ''), ('38', '', 'channel-1', ''), ('35', '', 'channel-0', '<obsolete/>')]) + '</sdk-repository>'
        with patch.object(monitor, 'read_text', return_value=xml):
            self.assertEqual([r['version'] for r in monitor.read_releases('android-build-tools', None)], ['36.0.0'])

    def test_agp_patch_uses_series_page_and_its_own_security_notes(self):
        xml = '<metadata><versioning><versions><version>9.5.1</version></versions></versioning></metadata>'
        with patch.object(monitor, 'read_text', return_value=xml):
            self.assertEqual(monitor.read_releases('agp', None)[0]['html_url'], 'https://developer.android.com/build/releases/agp-9-5-0-release-notes')
        html = '<h3 id="fixed-issues-agp-9.5.1">9.5.1</h3><p>Bug fixes</p><h3 id="fixed-issues-agp-9.5.0">9.5.0</h3><p>Security patch CVE-2026-1234</p>'
        with patch.object(monitor, 'read_text', return_value=html), patch.object(monitor.core, 'request_json', return_value={}):
            self.assertEqual(monitor.extra_evidence('agp', {'versions': ['9.5.0']}, [release('9.5.1')]), [])

    def test_android_studio_stable_patch_identity(self):
        xml = '<products><product><channel status="release"><build version="Rabbit | 2026.2.2 Patch 1"><message>fix</message></build></channel><channel status="beta"><build version="2027.1.1"/></channel></product></products>'
        with patch.object(monitor, 'read_text', return_value=xml):
            self.assertEqual(monitor.read_releases('android-studio', None)[0]['version'], '2026.2.2.1')

    def test_nsis_does_not_notify_unreleased_documentation(self):
        html = '<a name="v3.14"></a><h2>3.14</h2><p>Released on ????? ???, ????</p><a name="v3.13"></a><h2>3.13</h2><p>Released on September 27th, 2026</p>'
        with patch.object(monitor, 'read_text', return_value=html):
            self.assertEqual([r['version'] for r in monitor.read_releases('nsis', None)], ['3.13'])

    def test_jdk_advisory_priority_does_not_attribute_later_fixes(self):
        def reader(url):
            if url.endswith('/'):
                return '<a href="2026-10-20">Oct 20</a><a href="2026-10-24">Oct 24</a>'
            return 'Fixed CVE-2026-1234'
        with patch.object(monitor, 'read_text', side_effect=reader):
            evidence = monitor.extra_evidence('jdk', {}, [release('25.0.5+8', date='2026-10-22T00:00:00Z')])
        self.assertEqual(len(evidence), 1)
        self.assertTrue(evidence[0]['url'].endswith('2026-10-20'))
        self.assertIn('verify version applicability', evidence[0]['basis'])

    def test_debian_feed_recognizes_point_release(self):
        xml = '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/"><item><title>Updated Debian 13: 13.7 released</title><link>https://www.debian.org/News/2026/test</link><dc:date>2026-09-12</dc:date></item></rdf:RDF>'
        with patch.object(monitor, 'read_text', return_value=xml):
            self.assertEqual(monitor.read_releases('debian', None)[0]['version'], '13.7')

    def test_security_priority_order_and_one_failure_does_not_hide_others(self):
        writes = []
        def trivy(api, repo, assignee, publish=False):
            raise OSError('Trivy unavailable')
        def go(api, repo, assignee, publish=False):
            if publish:
                writes.append('Go')
            return {'tool': 'Go', 'status': 'update_available', 'security': False, 'published': publish}
        def extra(api, repo, assignee, tool, config, publish=False):
            if publish:
                writes.append(tool)
            return {'tool': tool, 'status': 'update_available', 'security': True, 'published': publish}
        with patch.object(monitor, 'settings', return_value={'powershell': {}}), patch.object(monitor.core, 'check', side_effect=trivy), patch.object(monitor.core, 'check_go', side_effect=go), patch.object(monitor, 'check_tool', side_effect=extra), patch.dict('os.environ', {'GH_TOKEN': 'test'}, clear=True), patch('sys.argv', ['check', '--repository', 'example/project', '--publish']), patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(monitor.main(), 1)
        self.assertEqual(writes, ['powershell', 'Go'])
        self.assertEqual(json.loads(out.getvalue())['status'], 'failed')

    def test_no_declared_extras_never_queries_their_sources(self):
        unused = {'tool': 'unused', 'status': 'not_used', 'published': False}
        with patch.object(monitor, 'settings', return_value={}), patch.object(monitor.core, 'check', return_value=unused), patch.object(monitor.core, 'check_go', return_value=unused), patch.object(monitor, 'read_releases', side_effect=AssertionError('unused tools must not query upstream')), patch('sys.argv', ['check', '--repository', 'example/project']), patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(monitor.main(), 0)


if __name__ == '__main__':
    unittest.main()
