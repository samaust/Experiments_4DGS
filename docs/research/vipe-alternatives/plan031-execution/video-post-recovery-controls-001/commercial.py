"""Assemble exact video commercial evidence; explicit independent findings required."""
import argparse
import json
from pathlib import Path
import sys

SCOPES=('code','weights','dependencies','inference_outputs')


def require(value,message):
    if not value:raise ValueError(message)


def identity(value):
    require(isinstance(value,str) and bool(value.strip()),'nonempty string identity required')
    return value.strip().casefold()


def api(checkout):
    sys.path.insert(0,str(Path(checkout).resolve()/'scripts'))
    from vipe_benchmark.config import ROOT
    from vipe_benchmark.files import file_record,read_json,verify_record,write_json
    require(ROOT.resolve()==Path(checkout).resolve(),'exact checkout import required')
    return file_record,read_json,verify_record,write_json


def validate_findings(checkout,manifest_path,findings_path):
    record,read,verify,write=api(checkout)
    manifest_record=record(manifest_path);manifest=read(manifest_path)
    findings_record=record(findings_path);findings=read(findings_path)
    from vipe_benchmark.video_environment import FRAME_RECIPE
    from vipe_benchmark.depth_environment import _requirements
    recipe=read(FRAME_RECIPE)
    require(manifest.get('schema')=='plan069-depth-installed-dependencies/v1' and
        manifest.get('record_kind')=='actual' and manifest.get('candidate') in ('D9','D10') and
        manifest.get('runtime_recipe')==record(FRAME_RECIPE),'actual frame recipe dependency manifest required')
    setup=read(verify(manifest['setup'])['path'])
    require(setup.get('record_kind')=='actual' and setup.get('status')=='complete' and
        setup.get('candidate')==manifest['candidate'] and setup.get('source_revision')==manifest['source_revision'] and
        setup.get('runtime_recipe')==manifest['runtime_recipe'] and
        setup.get('runtime_environment')==manifest['runtime_environment'],'exact accepted setup manifest binding required')
    runtime=read(verify(setup['runtime_environment'])['path'])
    require(all(manifest.get(key)==runtime.get(key) for key in ('inventory','python','dependency_lock','python_executable')),
        'manifest differs from accepted runtime inventory/interpreter/lock')
    inventory=read(verify(manifest['inventory'])['path'])
    require(manifest.get('packages')==inventory.get('packages') and
        inventory.get('executable')==manifest['python_executable']==setup['python_executable'],
        'exact installed inventory package closure required')
    verify(manifest['python']);verify(manifest['dependency_lock'])
    files=[r for package in inventory['packages'] for r in package['files']]
    legacy_notices=[r for r in files if any(token in Path(r['path']).name.upper() for token in ('LICENSE','NOTICE'))]
    notices=[r for r in files if any(token in Path(r['path']).name.upper() for token in ('LICENSE','LICENCE','COPYING','NOTICE'))]
    require(manifest.get('files')==files and manifest.get('notices')==legacy_notices,
        'manifest must retain exact full installed file and derived notice closure')
    def name(value):return value.lower().replace('_','-').replace('.','-')
    pins={name(row.name):str(row.specifier)[2:] for row in _requirements(recipe['constraints'])}
    packages={name(row['name']):row for row in manifest['packages']}
    require(len(pins)==len(packages)==len(manifest['packages'])==48 and
        {key:row['version'] for key,row in packages.items()}==pins and
        not {'decord','xformers'}&packages.keys(),'exact48 reviewed distribution pins required')
    require(findings.get('schema')=='plan069-video-commercial-findings/v1' and
        findings.get('dependency_manifest')==manifest_record and
        findings.get('candidate')==manifest['candidate'] and findings.get('source_revision')==manifest['source_revision'] and
        findings.get('weights_revision')==setup['weight_revision'] and
        isinstance(findings.get('scope'),str) and bool(findings['scope'].strip()) and bool(identity(findings.get('author'))),'exact commercial findings bindings and explicit scope required')
    primary=[];covered=[]
    def evidence(row):
        require(row.get('permission')=='allowed' and isinstance(row.get('basis'),str) and bool(row['basis'].strip()),
            'explicit allowed finding and rationale required; labels cannot grant permission')
        sources=row.get('primary_evidence',[])
        require(bool(sources),'retained primary permission evidence required')
        for source in sources:
            require(str(source.get('url','')).startswith('https://'),'primary evidence URL required')
            verify(source['record']);primary.append(source['url'])
    rows=findings.get('packages',[])
    require(len(rows)==48 and len({name(row['name']) for row in rows})==48 and
        {name(row['name']) for row in rows}==set(packages),'findings must cover each installed distribution exactly once')
    for row in rows:
        package=packages[name(row['name'])]
        require(row.get('version')==package['version'],'commercial finding version differs')
        evidence(row)
        records=row.get('installed_evidence',[])
        require(bool(records) and all(r in package['files'] for r in records),'package findings need exact installed evidence')
        for r in records:verify(r)
        covered.extend(records)
    for row in findings.get('embedded_components',[]):
        evidence(row)
        require(bool(row.get('installed_evidence')) and all(r in manifest['files'] for r in row['installed_evidence']),
            'embedded findings need exact installed evidence')
        for r in row['installed_evidence']:verify(r)
        covered.extend(row['installed_evidence'])
    require(all(row in covered for row in notices),'installed notices require explicit package or embedded findings')
    scopes=findings.get('scopes',{})
    require(set(scopes)==set(SCOPES),'all commercial scopes require separate findings')
    for row in scopes.values():evidence(row)
    code_records=[item['record'] for item in scopes['code']['primary_evidence']]
    require(any(row in manifest['native_source_files'] for row in code_records),'code scope requires pinned native primary evidence')
    require(len(set(primary))>=2,'at least two distinct primary sources required')
    return manifest_record,manifest,findings_record,findings,setup,primary,scopes,rows


def permission_report(findings):
    scopes=findings['scopes'];rows=findings['packages']
    return ('# Exact video commercial permission findings\n\n'+findings.get('scope','')+'\n\n'+
        '\n'.join('## '+key+'\n\n'+scopes[key]['basis']+'\n' for key in SCOPES)+
        '\n## Installed distributions\n\n'+'\n'.join('- '+row['name']+' '+row['version']+': '+row['basis'] for row in rows)+
        '\n\n## Embedded components\n\n'+'\n'.join('- '+row['basis'] for row in findings.get('embedded_components',[]))+
        '\n\nIndependent review is required. Input-media rights, output copyrightability and redistribution are outside this assessment unless explicitly reviewed.\n')


def prepare(checkout,manifest_path,findings_path,output,*,preparer):
    identity(preparer)
    record,read,verify,write=api(checkout)
    manifest_record,manifest,findings_record,findings,setup,primary,scopes,rows=validate_findings(checkout,manifest_path,findings_path)
    out=Path(output).absolute();require(not out.exists(),'fresh immutable commercial preparation required');out.mkdir(parents=True)
    report=out/'permission-report.md';report.write_text(permission_report(findings))
    assessment=dict(schema='plan069-depth-commercial-assessment/v1',status='pending_independent_review',
        candidate=manifest['candidate'],source_revision=manifest['source_revision'],weights_revision=setup['weight_revision'],
        dependency_manifest=manifest_record,permission_report=record(report),primary_sources=sorted(set(primary)),
        explicit_findings=findings_record,setup=manifest['setup'],scope=findings.get('scope'),preparer=preparer,
        **{key:'pending' for key in SCOPES})
    require(len(assessment['primary_sources'])>=2,'at least two distinct primary sources required')
    write(out/'assessment-template.json',assessment)
    return assessment


def finalize(checkout,template_path,review_path,output):
    record,read,verify,write=api(checkout)
    template=read(template_path);review_record=record(review_path);review=read(review_path)
    require(template.get('schema')=='plan069-depth-commercial-assessment/v1' and
        template.get('status')=='pending_independent_review' and all(template.get(key)=='pending' for key in SCOPES),
        'unmodified pending commercial assessment required')
    for key in ('dependency_manifest','permission_report','explicit_findings','setup'):verify(template[key])
    manifest_record,manifest,findings_record,findings,setup,primary,scopes,rows=validate_findings(
        checkout,template['dependency_manifest']['path'],template['explicit_findings']['path'])
    require(template.get('candidate')==manifest['candidate'] and template.get('source_revision')==manifest['source_revision'] and
        template.get('weights_revision')==setup['weight_revision'] and template.get('setup')==manifest['setup'] and
        template.get('scope')==findings['scope'] and template.get('primary_sources')==sorted(set(primary)) and
        bool(identity(template.get('preparer'))) and
        Path(template['permission_report']['path']).read_text()==permission_report(findings),'pending template differs from fully validated findings')
    for row in [*findings['packages'],*findings.get('embedded_components',[]),*findings['scopes'].values()]:
        for source in row['primary_evidence']:verify(source['record'])
        for source in row.get('installed_evidence',[]):verify(source)
    require(review.get('schema')=='plan069-video-commercial-independent-review/v1' and
        review.get('status')=='passed' and identity(review.get('reviewer')) not in
        (identity(findings['author']),identity(template['preparer'])) and
        review.get('assessment_template')==record(template_path) and
        review.get('dependency_manifest')==template['dependency_manifest'] and
        review.get('permission_report')==template['permission_report'] and
        review.get('explicit_findings')==template['explicit_findings'] and
        review.get('scope_permissions')=={key:'allowed' for key in SCOPES},
        'exact independent scope permission review required')
    assessment=dict(template,status='passed',independent_review=dict(status='passed',review=review_record,reviewer=review['reviewer']),
        **{key:'allowed' for key in SCOPES})
    path=Path(output).absolute();require(not path.exists(),'fresh immutable commercial assessment required')
    path.parent.mkdir(parents=True,exist_ok=True);write(path,assessment);return assessment


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkout',required=True)
    sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('prepare');a.add_argument('--manifest',required=True);a.add_argument('--findings',required=True);a.add_argument('--output',required=True);a.add_argument('--preparer',required=True)
    a=sub.add_parser('finalize');a.add_argument('--template',required=True);a.add_argument('--review',required=True);a.add_argument('--output',required=True)
    args=p.parse_args()
    result=prepare(args.checkout,args.manifest,args.findings,args.output,preparer=args.preparer) if args.mode=='prepare' else finalize(args.checkout,args.template,args.review,args.output)
    print(json.dumps(dict(status=result['status'],candidate=result['candidate'])))


if __name__=='__main__':main()
