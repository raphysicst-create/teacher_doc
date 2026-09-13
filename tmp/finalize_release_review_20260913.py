from pathlib import Path
from collections import Counter
from importlib import metadata
import copy, datetime, hashlib, importlib.util, json, re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'distribution/review-2026-09-13'
assert not OUT.exists(), 'Review snapshots are immutable; use a new revision'
OUT.mkdir()
REPORT='distribution/release-review-2026-09-13.md'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest=read(ROOT/'distribution/release-files.json')
rights=read(ROOT/'distribution/rights.pending.json')
save(OUT/'rights-before.json',rights)
bundle=read(ROOT/'distribution/source-bundle.json')
save(OUT/'source-bundle-before.json',bundle)
decision=read(ROOT/'distribution/pymupdf-agpl-decision-2026-09-13.json')
save(OUT/'agpl-decision-before.json',decision)
inventory=read(ROOT/'tmp/release-review-20260913/inventory.json')
previous_by={r['source']:r for r in inventory}
by_dest={x['destination']:x['source'] for x in manifest['files']}
for item in bundle['documents']+bundle['archives']:
    current=sha(ROOT/by_dest[item['destination']])
    if item in bundle['archives']:
        assert current==item['sha256'], 'Upstream source archives must remain unchanged'
    item['sha256']=current
save(ROOT/'distribution/source-bundle.json',bundle)
bundle_sha=sha(ROOT/'distribution/source-bundle.json')
decision['distribution_preparation']['source_bundle_sha256']=bundle_sha
decision['distribution_preparation']['latest_scope_review']=REPORT
save(ROOT/'distribution/pymupdf-agpl-decision-2026-09-13.json',decision)

evidence=read(ROOT/'distribution/license-evidence-2026-09-13/index.json')
dep_source={r['package']:r for r in evidence['dependencies']}
lic={'lxml':'BSD-3-Clause; component exceptions retained',
     'python-hwpx':'Apache-2.0','pypdf':'BSD-3-Clause','pywin32':'BSD-style Windows API/COM components; mixed component notices retained',
     'openpyxl':'MIT','et-xmlfile':'MIT AND Python-derived-code notices',
     'xlrd':'BSD-style main code AND legacy advertising-clause license',
     'PyMuPDF':'AGPL-3.0'}
notes={
 'lxml':'Uses etree, not isoschematron; no lxml binaries/source resources bundled. LICENSE and exception list retained. No approval for separately vendoring unlicensed XSL resources.',
 'python-hwpx':'Unmodified external install; Apache license and NOTICE attribution retained. Mandatory lxml dependency pinned. No source edits or vendored sample corpus.',
 'pypdf':'Unmodified external install; copyright, terms and disclaimer retained; no endorsement claims.',
 'pywin32':'Windows API/COM imports; original component notices retained. No binary/source redistribution of pywin32, adodbapi, MAPI or Scintilla.',
 'openpyxl':'Unmodified external install; MIT copyright and permission retained; et-xmlfile pinned.',
 'et-xmlfile':'MIT and Python-derived code notices both retained; no source edits.',
 'xlrd':'Unresolved AGPL compatibility of legacy advertising condition. Direct imports in refresh_reference and doctor; external pip install is not treated as an exemption.',
 'PyMuPDF':'Existing user-selected AGPL source/notice preparation rechecked with current bundle hash; complete unmodified PyMuPDF/MuPDF source archives preserved. Does not resolve xlrd compatibility.'}
dep_reviews=[]
for pin in manifest['dependency_reviews']:
    name,version=pin.split('==')
    assert metadata.version(name)==version
    source=dep_source[name]
    notice_hashes={}
    for artifact in source['artifacts']:
        path='distribution/legal/dependencies/'+artifact['path']
        assert sha(ROOT/path)==artifact['sha256'],path
        notice_hashes[path]=artifact['sha256']
    r={'dependency':pin,'license':lic[name],'source':source['pypi_url'],
       'reviewed_by':'Codex','reviewed_at':'2026-09-13','review_report':REPORT,
       'status':'blocked_agpl_combination' if name=='xlrd' else 'conditions_checked_current_scope',
       'scope':notes[name],'notice_hashes':notice_hashes,
       'installed_requires_dist':metadata.requires(name) or [],'binaries_bundled':False}
    dep_reviews.append(r)
    target=rights['dependencies'].setdefault(pin,{})
    target.update({k:r[k] for k in ('license','source','reviewed_by','reviewed_at','review_report')})
    target['review_status']=r['status'];target['scope']=r['scope'];target['notice_hashes']=notice_hashes
    if name=='xlrd':
        target.pop('conditions_review',None)
        target['blocking_reason']='legacy_advertising_clause_agpl_compatibility_unresolved'
    else:
        target['conditions_review']=REPORT+'#의존성별-적용-조건'
    if name=='PyMuPDF':target['source_bundle_sha256']=bundle_sha
save(OUT/'dependencies.json',dep_reviews)

file_reviews=[]
for item in manifest['files']:
    path=item['source'];p=ROOT/path;h=sha(p);prior=previous_by[path]
    record=copy.deepcopy(prior)
    record['sha256']=h;record['bytes']=p.stat().st_size
    if h!=prior['sha256']:
        assert path in ('distribution/README.md','distribution/legal/NOTICE.md','distribution/source-bundle.json'),path
        record['previous_sha256']=prior['sha256']
        record['change_review']='Read review-status update/legacy attribution; source bundle only refreshes NOTICE hash. No operational material added.'
    for k in ('local_identity','personal_number','phone','credential'):
        assert not prior['matches'].get(k),(path,k)
    upstream=prior.get('upstream')
    if upstream or path.endswith(('references/editing-details.md','references/xml-authoring.md')):
        source=('https://github.com/Canine89/hwpxskill/tree/cb5f25b6557b47b0339398d3b5d45a57bdcb4b28/'+upstream['path']) if upstream else 'Canine89 SKILL.md reorganized with project-authored changes; local Git introduction recorded'
        license_name='MIT original component; AGPL-3.0-only combined distribution and project changes'
        permission='distribution/canine89-mit-permission-2026-09-13.json; '+REPORT
    elif path.startswith(('distribution/legal/','distribution/sources/')):
        old=rights['files'][path]
        source=old['source'];license_name=old['license'];permission=old['permission_record']+'; '+REPORT
    else:
        source='teacher_doc project-authored source/configuration; Git and current implementation history in '+REPORT
        license_name='AGPL-3.0-only'
        permission='distribution/pymupdf-agpl-decision-2026-09-13.json; '+REPORT
    if path.endswith('.png'):
        privacy='Full image opened by Codex: blank white page; PNG text/EXIF chunks absent; no local school identity.'
    elif 'xml_text' in prior:
        privacy='Parsed all text nodes and attributes; inspected placeholders/style labels; no local identity or embedded fonts/assets.'
    elif path.endswith('.tar.gz'):
        privacy='Hash equals previously verified unmodified public upstream archive; no local material added; not a new manual review of every upstream test asset.'
    elif path.startswith('distribution/legal/'):
        privacy='Verbatim public license/attribution or publisher notice; public author/contact emails preserved, not local school/student data.'
    else:
        privacy='Complete text pattern scan plus source/metadata and flagged-content review; no local school/account identifiers, phone, personal-number or credential matches.'
    record.update(reviewed_by='Codex',reviewed_at='2026-09-13',rights_status='reviewed_current_hash',
                  privacy_status='reviewed_current_hash',license=license_name,permission_record=permission,
                  origin_source=source,privacy_observation=privacy)
    file_reviews.append(record)
    rights['files'][path]={'sha256':h,'license':license_name,'source':source,
       'permission_record':permission,'reviewed_by':'Codex','reviewed_at':'2026-09-13',
       'privacy_review':REPORT+' — '+privacy,'privacy_sha256':h}
save(OUT/'files.json',file_reviews)
rights['status']='file_reviews_complete_dependency_combination_blocked'
rights['source_review'].update(latest_review=REPORT,latest_file_inventory='distribution/review-2026-09-13/files.json',
                               latest_dependency_review='distribution/review-2026-09-13/dependencies.json',release_approval=False)
rights['notes']=[
 'User-confirmed Canine89 MIT permission and free AGPL choice are settled; no new license exception or third-party grant invented.',
 '101 allowlisted files reviewed at current SHA256 for origin/rights/privacy. Prior review input preserved in distribution/review-2026-09-13/rights-before.json.',
 'Seven dependency conditions checked for the current source-only, external-install scope. xlrd 2.0.2 legacy advertising-clause compatibility with AGPL remains blocked.',
 'The xlrd conditions_review completion field is intentionally absent; a reviewed issue is not a satisfied condition.',
 'No release package/publication or new app acceptance is asserted. Any file/dependency/scope change requires re-review.'
]
save(ROOT/'distribution/rights.pending.json',rights)
spec=importlib.util.spec_from_file_location('review_packaging',ROOT/'scripts/build_distribution.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
result=mod.check_release(manifest,rights)
save(OUT/'release-gate.json',result)
assert result['issues']==[{'dependency':'xlrd==2.0.2','reason':'dependency_license_unconfirmed'}], result['issues']
assert len(result['files'])==len(file_reviews)==101
assert all(sha(ROOT/r['source'])==r['sha256'] for r in file_reviews)
save(OUT/'validation.json',{
 'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files_reviewed':101,
 'rights_unconfirmed':0,'privacy_unconfirmed':0,'dependency_conditions_checked':7,'dependency_conditions_blocked':1,
 'gate_status':result['status'],'gate_issues':result['issues'],'source_archives_unchanged':True,
 'all_current_file_hashes_match':True,'package_created':False,'new_app_tests_run':False,
 'report_sha256':sha(ROOT/REPORT),'rights_input_sha256':sha(ROOT/'distribution/rights.pending.json'),
 'source_bundle_sha256':bundle_sha})
with (ROOT/'logs/audit.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps({'ts':datetime.datetime.now(datetime.timezone.utc).isoformat(),'agent':'codex',
                       'action':'review_distribution_rights_privacy_dependencies','target':REPORT,
                       'result':'review_complete_release_blocked','detail':{
                       'files_reviewed':101,'dependencies_checked':7,'blocked_dependency':'xlrd==2.0.2',
                       'package_created':False}},ensure_ascii=False)+'\n')
print(json.dumps({'files_reviewed':101,'dependencies_checked':7,'remaining_gate_issues':result['issues']},ensure_ascii=False))
