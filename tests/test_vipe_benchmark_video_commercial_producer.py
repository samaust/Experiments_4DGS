"""CPU fixtures enforce complete commercial evidence without inferring permission."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from vipe_benchmark.config import ROOT
from vipe_benchmark.files import file_record,read_json,write_json
from vipe_benchmark.video_environment import FRAME_RECIPE
from vipe_benchmark.depth_environment import _requirements

PATH=ROOT/'docs/research/vipe-alternatives/plan031-execution/video-post-recovery-controls-001/commercial.py'
spec=importlib.util.spec_from_file_location('video_commercial',PATH)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class CommercialProducerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.scopefile=self.root/'code-LICENSE';self.scopefile.write_text('CPU fixture permission text')
        scope_record=file_record(self.scopefile)
        self.python=self.root/'python';self.python.write_text('CPU fixture interpreter')
        self.lock=self.root/'requirements.lock';self.lock.write_text('CPU fixture dependency lock')
        self.runtime=self.root/'runtime.json';write_json(self.runtime,{})
        self.setup=self.root/'setup.json';write_json(self.setup,dict(record_kind='actual',status='complete',candidate='D9',
            source_revision='source-pin',weight_revision='weights-pin',runtime_recipe=file_record(FRAME_RECIPE),
            runtime_environment=file_record(self.runtime),python_executable=str(self.python)))
        packages=[];rows=[];notices=[]
        for i,r in enumerate(_requirements(read_json(FRAME_RECIPE)['constraints'])):
            path=self.root/f'{i}-LICENSE';path.write_text('CPU fixture permissive grant')
            notice=file_record(path);notices.append(notice)
            version=str(r.specifier)[2:]
            packages.append(dict(name=r.name,version=version,files=[notice],license='fixture metadata'))
            rows.append(dict(name=r.name,version=version,permission='allowed',basis='Explicit fixture finding only',
                installed_evidence=[notice],primary_evidence=[dict(url='https://example.invalid/'+r.name,record=notice)]))
        self.inventory=self.root/'inventory.json';write_json(self.inventory,dict(packages=packages,executable=str(self.python)))
        self.runtime.write_text(__import__('json').dumps(dict(inventory=file_record(self.inventory),python=file_record(self.python),
            dependency_lock=file_record(self.lock),python_executable=str(self.python))))
        setup=read_json(self.setup);setup['runtime_environment']=file_record(self.runtime);self.setup.write_text(__import__('json').dumps(setup))
        self.manifest=self.root/'manifest.json';write_json(self.manifest,dict(schema='plan069-depth-installed-dependencies/v1',
            record_kind='actual',candidate='D9',source_revision='source-pin',runtime_recipe=file_record(FRAME_RECIPE),
            setup=file_record(self.setup),runtime_environment=file_record(self.runtime),inventory=file_record(self.inventory),
            python_executable=str(self.python),python=file_record(self.python),dependency_lock=file_record(self.lock),
            packages=packages,files=notices,native_source_files=[scope_record],notices=notices))
        self.findings=dict(schema='plan069-video-commercial-findings/v1',author='Fixture findings author',candidate='D9',source_revision='source-pin',
            weights_revision='weights-pin',dependency_manifest=file_record(self.manifest),scope='Local fixture-only commercial inference',
            packages=rows,embedded_components=[],scopes={key:dict(permission='allowed',basis='Explicit fixture-only scope finding',
                primary_evidence=[dict(url='https://example.invalid/'+key,record=scope_record)]) for key in module.SCOPES})
        self.findings_path=self.root/'findings.json';self.output=self.root/'prepared'

    def prepare(self):
        self.findings_path.write_text(__import__('json').dumps(self.findings))
        return module.prepare(ROOT,self.manifest,self.findings_path,self.output,preparer='Fixture evidence preparer')

    def test_exact48_preparation_remains_pending_independent_review(self):
        result=self.prepare()
        self.assertEqual(result['status'],'pending_independent_review')
        self.assertTrue(all(result[key]=='pending' for key in module.SCOPES))
        self.assertNotIn('independent_review',result)

    def test_license_label_cannot_replace_permission_finding(self):
        self.findings['packages'][0]['permission']='unknown'
        with self.assertRaisesRegex(ValueError,'explicit allowed'):self.prepare()
        self.assertFalse(self.output.exists())

    def test_missing_duplicate_or_wrong_version_distribution_finding_rejected(self):
        original=copy.deepcopy(self.findings)
        for action in ('missing','duplicate','version'):
            with self.subTest(action=action):
                self.findings=copy.deepcopy(original)
                if action=='missing':self.findings['packages'].pop()
                if action=='duplicate':self.findings['packages'][-1]=self.findings['packages'][0]
                if action=='version':self.findings['packages'][0]['version']='wrong'
                with self.assertRaises(ValueError):self.prepare()
                self.assertFalse(self.output.exists())

    def test_installed_notice_coverage_and_primary_bytes_required(self):
        self.findings['packages'][0]['installed_evidence']=[]
        with self.assertRaisesRegex(ValueError,'installed evidence'):self.prepare()
        self.findings['packages'][0]['installed_evidence']=self.findings['packages'][0]['primary_evidence'][0:0]
        self.findings['packages'][0]['primary_evidence'][0]['record']['sha256']='wrong'
        with self.assertRaises(ValueError):self.prepare()

    def test_explicit_scope_and_pinned_code_evidence_required(self):
        self.findings['scopes']['inference_outputs']['permission']='unknown'
        with self.assertRaises(ValueError):self.prepare()
        self.findings['scopes']['inference_outputs']['permission']='allowed'
        self.findings['scopes']['code']['primary_evidence']=self.findings['packages'][0]['primary_evidence']
        with self.assertRaisesRegex(ValueError,'pinned native'):self.prepare()

    def test_independent_review_binds_template_manifest_report_findings(self):
        template=self.prepare();path=self.output/'assessment-template.json'
        review=dict(schema='plan069-video-commercial-independent-review/v1',status='passed',reviewer='Independent fixture reviewer',
            assessment_template=file_record(path),dependency_manifest=template['dependency_manifest'],
            permission_report=template['permission_report'],explicit_findings=template['explicit_findings'],
            scope_permissions={key:'allowed' for key in module.SCOPES})
        rp=self.root/'review.json';write_json(rp,review);out=self.root/'assessment.json'
        result=module.finalize(ROOT,path,rp,out)
        self.assertEqual(result['status'],'passed');self.assertEqual(result['independent_review']['review'],file_record(rp))
        with self.assertRaises(ValueError):module.finalize(ROOT,path,rp,out)
        review['scope_permissions']['weights']='unknown';rp.write_text(__import__('json').dumps(review))
        with self.assertRaisesRegex(ValueError,'independent'):module.finalize(ROOT,path,rp,self.root/'other.json')

    def test_changed_primary_evidence_rejected_before_output(self):
        self.scopefile.write_text('changed fixture bytes')
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse(self.output.exists())

    def test_manifest_cannot_hide_notice_or_file_closure(self):
        import json
        original=read_json(self.manifest)
        for key in ('notices','files'):
            with self.subTest(key=key):
                changed=dict(original,**{key:[]});self.manifest.write_text(json.dumps(changed))
                self.findings['dependency_manifest']=file_record(self.manifest)
                with self.assertRaisesRegex(ValueError,'full installed'):self.prepare()
                self.assertFalse(self.output.exists())

    def test_manifest_runtime_records_cannot_be_relabelled(self):
        import json
        value=read_json(self.manifest);value['dependency_lock']=file_record(self.scopefile)
        self.manifest.write_text(json.dumps(value));self.findings['dependency_manifest']=file_record(self.manifest)
        with self.assertRaisesRegex(ValueError,'accepted runtime'):self.prepare()

    def test_handcrafted_pending_template_does_not_skip_permission_validation(self):
        import json
        template=self.prepare();path=self.output/'assessment-template.json'
        self.findings['packages'][0]['permission']='unknown';self.findings_path.write_text(json.dumps(self.findings))
        template['explicit_findings']=file_record(self.findings_path);path.write_text(json.dumps(template))
        rp=self.root/'review.json';write_json(rp,{})
        with self.assertRaisesRegex(ValueError,'explicit allowed'):
            module.finalize(ROOT,path,rp,self.root/'assessment.json')

    def test_findings_author_or_preparer_cannot_self_review(self):
        import json
        template=self.prepare();path=self.output/'assessment-template.json'
        base=dict(schema='plan069-video-commercial-independent-review/v1',status='passed',
            assessment_template=file_record(path),dependency_manifest=template['dependency_manifest'],
            permission_report=template['permission_report'],explicit_findings=template['explicit_findings'],
            scope_permissions={key:'allowed' for key in module.SCOPES})
        rp=self.root/'review.json'
        for reviewer in (self.findings['author'],template['preparer'],'  '+self.findings['author'].upper()+'  ',None,{}):
            with self.subTest(reviewer=reviewer):
                rp.write_text(json.dumps(dict(base,reviewer=reviewer)))
                with self.assertRaises(ValueError):
                    module.finalize(ROOT,path,rp,self.root/'assessment.json')

    def test_licence_family_notice_cannot_hide_behind_legacy_manifest_list(self):
        import json
        added=self.root/'embedded-LICENCE';added.write_text('Supplemental fixture terms')
        notice=file_record(added);inventory=read_json(self.inventory)
        inventory['packages'][0]['files'].append(notice);self.inventory.write_text(json.dumps(inventory))
        runtime=read_json(self.runtime);runtime['inventory']=file_record(self.inventory);self.runtime.write_text(json.dumps(runtime))
        setup=read_json(self.setup);setup['runtime_environment']=file_record(self.runtime);self.setup.write_text(json.dumps(setup))
        manifest=read_json(self.manifest)
        manifest.update(inventory=file_record(self.inventory),packages=inventory['packages'],setup=file_record(self.setup),
            runtime_environment=file_record(self.runtime),files=[r for package in inventory['packages'] for r in package['files']])
        # Original producer legacy notices excludes LICENCE, intentionally unchanged.
        self.manifest.write_text(json.dumps(manifest));self.findings['dependency_manifest']=file_record(self.manifest)
        with self.assertRaisesRegex(ValueError,'notices require explicit'):self.prepare()
        self.assertFalse(self.output.exists())
