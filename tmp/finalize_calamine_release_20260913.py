from pathlib import Path
import ast,datetime,hashlib,json,re,shutil,sys,urllib.request
ROOT=Path(__file__).resolve().parents[1];RUN=ROOT/'tmp/package-lifecycle-20260913'
REVIEW=ROOT/'distribution/review-2026-09-13/calamine'
assert not REVIEW.exists();REVIEW.mkdir()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
for n in ['calamine-cell-comparison.json','budget-json-comparison.json','calamine-source-inspection.json','calamine-dependency-license-review.json']:
    shutil.copy2(RUN/n,REVIEW/n)
licenses=ROOT/'distribution/legal/dependencies/python-calamine';licenses.mkdir()
shutil.copy2(RUN/'calamine-source-review/LICENSE',licenses/'LICENSE')
url='https://raw.githubusercontent.com/tafia/calamine/v0.35.0/LICENSE-MIT.md'
(licenses/'calamine-LICENSE-MIT.md').write_bytes(urllib.request.urlopen(url,timeout=30).read())
manifest=read(ROOT/'distribution/release-files.json');rights=read(ROOT/'distribution/rights.pending.json');bundle=read(ROOT/'distribution/source-bundle.json')
for p in licenses.iterdir():manifest['files'].append({'source':p.relative_to(ROOT).as_posix(),'destination':'licenses/dependencies/python-calamine/'+p.name})
manifest['dependency_reviews']=['python-calamine==0.7.0' if d=='xlrd==2.0.2' else d for d in manifest['dependency_reviews']]
save(ROOT/'distribution/release-files.json',manifest)
destmap={i['destination']:ROOT/i['source'] for i in manifest['files']}
for d in bundle['documents']:d['sha256']=sha(destmap[d['destination']])
for p in licenses.iterdir():bundle['documents'].append({'destination':'licenses/dependencies/python-calamine/'+p.name,'sha256':sha(p)})
save(ROOT/'distribution/source-bundle.json',bundle)
decision=read(ROOT/'distribution/pymupdf-agpl-decision-2026-09-13.json')
decision['distribution_preparation'].update(source_bundle_sha256=sha(ROOT/'distribution/source-bundle.json'),latest_scope_review='distribution/calamine-review-2026-09-13.md')
save(ROOT/'distribution/pymupdf-agpl-decision-2026-09-13.json',decision)
rights.setdefault('historical_dependencies',{})['xlrd==2.0.2']=rights['dependencies'].pop('xlrd==2.0.2')
rights['dependencies']['python-calamine==0.7.0']={'license':'MIT (binding and calamine); pinned transitive permissive-license expressions recorded separately','source':'https://pypi.org/project/python-calamine/0.7.0/','conditions_review':'Binding sdist MIT text and calamine v0.35.0 MIT text read and preserved. Cargo.lock 70 packages matched to pinned checksums and publisher license metadata: MIT/Apache-2.0/LLVM exception/BSD-3-Clause/Unicode-3.0/Zlib and permissive OR alternatives. No xlrd runtime import or requirement remains. No dependency wheel/binary is redistributed in this source package. Existing AGPL source/notices retained.','reviewed_by':'Codex','reviewed_at':stamp(),'review_report':'distribution/calamine-review-2026-09-13.md','notice_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in licenses.iterdir()}}
rights['dependencies']['PyMuPDF==1.28.0']['source_bundle_sha256']=sha(ROOT/'distribution/source-bundle.json')
allowed={'scripts/refresh_reference.py','scripts/hwpdoc_runtime.py','distribution/requirements-school-data.txt','distribution/README.md','distribution/legal/NOTICE.md','distribution/legal/CHANGES.md','distribution/source-bundle.json',*[p.relative_to(ROOT).as_posix() for p in licenses.iterdir()]}
changes=[]
for item in manifest['files']:
    p=ROOT/item['source'];digest=sha(p);old=rights['files'].get(item['source'])
    if old and old['sha256']==digest:continue
    assert item['source'] in allowed,item['source']
    text=p.read_text(encoding='utf-8-sig')
    assert not re.search(r'(?i)[a-z]:[/\\]Users[/\\]|화동중|Desktop[/\\]maintain|sk-[A-Za-z0-9]{20}',text),p
    if p.suffix=='.py':assert not any(isinstance(n,ast.Import) and any(a.name=='xlrd' for a in n.names) or isinstance(n,ast.ImportFrom) and n.module=='xlrd' for n in ast.walk(ast.parse(text)))
    review=dict(old or {})
    review.update(sha256=digest,privacy_sha256=digest,reviewed_by='Codex',reviewed_at=stamp(),privacy_review='Current text/diff read; public license attribution retained; no local operational identifiers or data added. distribution/calamine-review-2026-09-13.md',permission_record='Existing AGPL user choice and MIT upstream license, current migration review: distribution/calamine-review-2026-09-13.md')
    if not old:review.update(license='MIT',source=url if p.name.startswith('calamine-') else 'https://pypi.org/project/python-calamine/0.7.0/ (verified sdist LICENSE)')
    rights['files'][item['source']]=review;changes.append({'path':item['source'],'previous_sha256':old.get('sha256') if old else None,'sha256':digest})
save(ROOT/'distribution/rights.pending.json',rights)
save(REVIEW/'changed-files.json',changes)
report=ROOT/'distribution/calamine-review-2026-09-13.md'
report.write_text('''# XLS 읽기 의존성 교체 검토 — 2026. 9. 13.

실제 배포 패키지 시험 요청에 따라, 기존 xlrd 광고 조항의 허락을 새로 만들어 승인하는 대신 XLS 읽기 의존성을 python-calamine 0.7.0으로 교체했다. 기존 README의 저작자 표시와 배포자 약속, xlrd LICENSE·과거 검토 기록은 보존한다. 현재 후보는 xlrd를 import하거나 설치하지 않는다.

## 기능 보존

기존 사업관리카드 사본의 106행 × 3열(318개 사용 셀)을 xlrd와 calamine으로 읽어 값과 타입이 모두 일치했다. 두 구현의 파생 JSON은 바이트 단위로 동일하며 세부사업 12개·산출내역 67개다. 행 위치를 보존하는 `skip_empty_area=False`와 들여쓰기·숫자·상위 항목 누락·원본 경로 보호 회귀시험 6개가 통과했다. 원본이나 운영 파생 데이터를 다시 저장하지 않았다. 고정 Python312에 새 라이브러리를 추가했으며 기존 xlrd 및 다른 패키지는 제거하지 않았다.

## 라이선스와 제공 범위

[python-calamine 0.7.0](https://pypi.org/project/python-calamine/0.7.0/)의 고정 소스 압축본 SHA256을 PyPI와 대조하고 실제 MIT 전문을 읽었다. [calamine 0.35.0 MIT 전문](https://raw.githubusercontent.com/tafia/calamine/v0.35.0/LICENSE-MIT.md)도 보존했다. 추가 광고 조항은 두 MIT 전문에 없다.

Cargo.lock의 70개 구성요소는 registry 체크섬 또는 고정 Git 리비전 및 배포자 라이선스 선언과 대조했다. MIT/Apache-2.0 계열, LLVM 예외, BSD-3-Clause, Unicode-3.0, Zlib 및 이들의 허용적 선택 조건이다. 호환성 판단의 일반 근거는 [GNU 목록](https://www.gnu.org/licenses/license-list.html)과 [Apache의 GPLv3 호환성 설명](https://www.apache.org/licenses/GPL-compatibility.html)이다. 이번 후보에서 기존 xlrd 결합 차단 사유를 제거할 수 있다고 판단한다. 이는 상류 코드 전수 감사나 법적 보증이 아니다.

패키지에는 새로운 wheel·DLL·PYD를 넣지 않는다. 설치기가 고정 PyPI 배포를 설치하며 원래 wheel의 고지를 유지한다. 두 MIT 전문은 소스 패키지에도 포함한다. 기존 PyMuPDF/MuPDF 소스 압축본·AGPL 전문·고지는 그대로 제공한다. Rust/C++ 전체 재빌드는 수행하지 않았다.

## 추적

- [사용 셀 비교](review-2026-09-13/calamine/calamine-cell-comparison.json)
- [파생 JSON 비교](review-2026-09-13/calamine/budget-json-comparison.json)
- [고정 소스 검토](review-2026-09-13/calamine/calamine-source-inspection.json)
- [전이 구성요소 선언·체크섬](review-2026-09-13/calamine/calamine-dependency-license-review.json)
- [변경 파일의 새 검토 해시](review-2026-09-13/calamine/changed-files.json)

기존 배포 검토 보고서는 당시의 xlrd 차단 결과로 보존한다. 이 후속 기록과 새 패키지 게이트를 함께 확인한다. 파일 포장 가능과 실제 앱 인수·공개 배포 판단은 별개다.
''',encoding='utf-8')
sys.path.insert(0,str(ROOT/'scripts'));import build_distribution as b
gate=b.check_release(manifest,rights);save(REVIEW/'gate.json',gate)
assert gate['status']=='ready_to_package',gate['issues']
print('ready_to_package',len(gate['files']),'files',len(changes),'new/re-reviewed hashes')
