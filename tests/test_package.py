"""Offline package integrity checks, not a usability or model-behavior score."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/ux-ui-quality'
REF = SKILL / 'references'
CLASSES = {'standard', 'research', 'platform-practice', 'design-reputation-precedent', 'our-synthesis'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


class PackageTests(unittest.TestCase):
    def test_manifests_and_discovery_paths(self):
        portable = read_json(ROOT / 'plugin.json')
        legacy = read_json(ROOT / '.codex-plugin/plugin.json')
        for key in ('name', 'version', 'description', 'author'):
            self.assertEqual(portable[key], legacy[key])
        self.assertEqual(portable['name'], 'ux-ui-quality')
        self.assertRegex(portable['version'], r'^\d+\.\d+\.\d+$')
        self.assertEqual(portable['extensions']['com.openai']['interface'], legacy['interface'])
        self.assertEqual(legacy['interface']['capabilities'], ['Skills'])
        skill_root = (ROOT / legacy['skills']).resolve()
        self.assertEqual(skill_root, (ROOT / 'skills').resolve())
        self.assertTrue((skill_root / portable['name'] / 'SKILL.md').is_file())

    def test_no_executable_runtime_or_configuration(self):
        forbidden = {'hooks', 'mcpservers', 'mcp', 'servers', 'dependencies', 'scripts'}
        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn(key.lower(), forbidden)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        for manifest in (ROOT / 'plugin.json', ROOT / '.codex-plugin/plugin.json'):
            walk(read_json(manifest))
        self.assertFalse((ROOT / 'mcp.json').exists())
        self.assertFalse((ROOT / '.mcp.json').exists())
        self.assertFalse((ROOT / 'AGENTS.md').exists())
        for path in ROOT.rglob('*'):
            if path.is_file():
                self.assertFalse(path.is_symlink(), path)
                self.assertNotIn(path.suffix, {'.sh', '.js', '.mjs', '.so', '.dylib', '.exe'})
                if path.suffix == '.py':
                    self.assertEqual(path.parent, ROOT / 'tests')

    def test_skill_metadata_and_implicit_invocation(self):
        skill = (SKILL / 'SKILL.md').read_text()
        frontmatter = skill.split('---', 2)[1]
        self.assertRegex(frontmatter, r'(?m)^name: ux-ui-quality$')
        self.assertRegex(frontmatter, r'(?m)^description: .+')
        metadata = (SKILL / 'agents/openai.yaml').read_text()
        self.assertRegex(metadata, r'(?m)^  allow_implicit_invocation: true$')
        prompt = re.search(r'(?m)^  default_prompt: "(.+)"$', metadata).group(1)
        self.assertIn('$ux-ui-quality', prompt)
        short = re.search(r'(?m)^  short_description: "(.+)"$', metadata).group(1)
        self.assertTrue(25 <= len(short) <= 64)
        self.assertLess(len(skill.splitlines()), 100)

    def test_sources_identity_provenance_and_dates(self):
        catalogue = read_json(REF / 'sources.json')
        checked = datetime.date.fromisoformat(catalogue['checked_date'])
        sources = catalogue['sources']
        ids = [s['id'] for s in sources]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(ids), 15)
        urls = []
        source_checked_dates = []
        for source in sources:
            self.assertRegex(source['id'], r'^[A-Z][A-Z0-9-]+$')
            self.assertIn(source['evidence_class'], CLASSES)
            for field in ('title', 'publisher', 'supports', 'limitation', 'verification'):
                self.assertTrue(source[field].strip(), (source['id'], field))
            parsed = urlparse(source['url'])
            self.assertEqual(parsed.scheme, 'https')
            self.assertTrue(parsed.hostname)
            self.assertFalse(parsed.username or parsed.password)
            urls.append(source['url'])
            source_checked = datetime.date.fromisoformat(source['checked_date'])
            source_checked_dates.append(source_checked)
            self.assertLessEqual(source_checked, checked)
            for field in ('publication_date', 'updated_date'):
                value = source[field]
                if value is not None:
                    self.assertLessEqual(datetime.date.fromisoformat(value), source_checked)
            if source['publication_date'] and source['updated_date']:
                self.assertLessEqual(source['publication_date'], source['updated_date'])
            self.assertIsInstance(source['older_foundation'], bool)
        self.assertEqual(max(source_checked_dates), checked)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(any(s['older_foundation'] for s in sources))

    def test_rules_are_complete_and_sources_resolve(self):
        text = (REF / 'principles.md').read_text()
        rules = re.findall(r'^### (UX-\d{2}) — (.*?)(?=^### |^## |\Z)', text, re.M | re.S)
        self.assertTrue(30 <= len(rules) <= 36)
        ids = [rid for rid, _ in rules]
        self.assertEqual(len(ids), len(set(ids)))
        sources = {s['id'] for s in read_json(REF / 'sources.json')['sources']}
        for rid, body in rules:
            for field in ('Условие', 'Действие', 'Проверка', 'Ограничение', 'Класс', 'Источники'):
                self.assertRegex(body, rf'(?m)^- \*\*{field}:\*\* \S.+', rid)
            cls = re.search(r'\*\*Класс:\*\* `([^`]+)`', body).group(1)
            self.assertIn(cls, CLASSES)
            cited = re.search(r'\*\*Источники:\*\* (.+)', body).group(1)
            for source in re.findall(r'`([^`]+)`', cited):
                self.assertIn(source, sources, rid)
        for path in (ROOT / 'README.md', REF / 'journeys.md', REF / 'product-patterns.md'):
            for source in re.findall(r'`([A-Z][A-Z0-9-]+)`', path.read_text()):
                if source != 'ON_INSTALL':
                    self.assertIn(source, sources, str(path))

    def test_local_links_stay_inside_package_and_resolve(self):
        count = 0
        for path in ROOT.rglob('*.md'):
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text()):
                if urlparse(target).scheme:
                    continue
                clean = target.split('#', 1)[0]
                if not clean:
                    continue
                destination = (path.parent / clean).resolve()
                self.assertTrue(destination.is_relative_to(ROOT), (path, target))
                self.assertTrue(destination.exists(), (path, target))
                count += 1
        self.assertGreaterEqual(count, 8)

    def test_evaluation_variety_and_rule_references(self):
        cases = read_json(ROOT / 'evals/cases.json')['cases']
        self.assertTrue(12 <= len(cases) <= 16)
        self.assertEqual(len({c['id'] for c in cases}), len(cases))
        self.assertEqual(len({c['prompt'] for c in cases}), len(cases))
        selections = {c['selection'] for c in cases}
        self.assertEqual(selections, {'positive', 'negative', 'boundary', 'explicit'})
        self.assertGreaterEqual(sum(c['selection'] == 'negative' for c in cases), 3)
        rules = set(re.findall(r'^### (UX-\d{2})', (REF / 'principles.md').read_text(), re.M))
        required = {'fewer-clicks', 'irreversible', 'unknown-submit', 'busy-b2b', 'accessible-auth', 'reputation', 'ai-simplification', 'backend-only', 'typo-only'}
        self.assertTrue(required <= {c['id'] for c in cases})
        for case in cases:
            self.assertTrue(case['prompt'].strip())
            self.assertGreaterEqual(len(case['rubric']), 2)
            self.assertTrue(all(isinstance(item, str) and item.strip() for item in case['rubric']))
            self.assertTrue(set(case['rule_ids']) <= rules)
            if case['selection'] == 'negative':
                self.assertEqual(case['rule_ids'], [])


    def test_original_evaluation_prompts_and_rubrics_are_frozen(self):
        cases = read_json(ROOT / 'evals/cases.json')['cases']
        projection = [{key: case[key] for key in ('id', 'prompt', 'rubric')} for case in cases]
        canonical = json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        expected = read_json(ROOT / 'evals/regressions.json')['baseline_prompt_rubric_sha256']
        self.assertEqual(len(cases), 15)
        self.assertEqual(digest, expected)

    def test_regression_criteria_have_valid_cases_and_existing_owners(self):
        cases = {case['id'] for case in read_json(ROOT / 'evals/cases.json')['cases']}
        regressions = read_json(ROOT / 'evals/regressions.json')['regressions']
        self.assertEqual(len(regressions), len({item['id'] for item in regressions}))
        self.assertEqual({item['case_id'] for item in regressions},
                         {'whole-journey', 'unknown-submit', 'no-app-access',
                          'target-and-drag', 'ai-simplification', 'busy-b2b', 'accessible-auth'})
        for item in regressions:
            self.assertIn(item['case_id'], cases)
            self.assertGreaterEqual(len(item['owners']), 1)
            for owner in item['owners']:
                path = (ROOT / owner['path']).resolve()
                self.assertTrue(path.is_relative_to(ROOT))
                self.assertTrue(path.is_file())
                text = path.read_text()
                self.assertEqual(len({'heading', 'rule_id'} & owner.keys()), 1)
                if 'heading' in owner:
                    headings = re.findall(r'^#{1,6} (.+)$', text, re.M)
                    self.assertIn(owner['heading'], headings)
                else:
                    rule_ids = re.findall(r'^### (UX-\d{2})', text, re.M)
                    self.assertIn(owner['rule_id'], rule_ids)
            criteria = item['criteria']
            self.assertEqual(len(criteria), len({c['id'] for c in criteria}))
            self.assertGreaterEqual(len(criteria), 2)
            for criterion in criteria:
                self.assertTrue(criterion['acceptance'].strip())
        journey = next(item for item in regressions if item['case_id'] == 'whole-journey')
        dimension_criteria = [c for c in journey['criteria'] if 'required_dimensions' in c]
        self.assertEqual(len(dimension_criteria), 1)
        dimensions = dimension_criteria[0]['required_dimensions']
        self.assertEqual(len(dimensions), 6)
        self.assertEqual(set(dimensions), {'service-touchpoints', 'interface-actions',
                                          'decisions', 're-entry', 'context-switches', 'waiting'})

    def test_unknown_outcome_rule_has_relevant_source_provenance(self):
        text = (REF / 'principles.md').read_text()
        body = re.search(r'^### UX-20 .*?(?=^### |\Z)', text, re.M | re.S).group(0)
        cited = re.search(r'\*\*Источники:\*\* (.+)', body).group(1)
        self.assertEqual(re.findall(r'`([^`]+)`', cited), ['STRIPE-ERRORS'])
        sources = {s['id']: s for s in read_json(REF / 'sources.json')['sources']}
        source = sources['STRIPE-ERRORS']
        self.assertEqual(source['evidence_class'], 'platform-practice')
        self.assertEqual(urlparse(source['url']).hostname, 'docs.stripe.com')
        self.assertIsNone(source['publication_date'])
        self.assertIsNone(source['updated_date'])


if __name__ == '__main__':
    unittest.main()
