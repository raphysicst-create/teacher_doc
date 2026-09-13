"""Read-only diagnostic scoring of five real Work runs; never generates documents or approvals."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import hwpdoc as h


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evidence_ok(entry, base):
    """Hash and locator establish an auditable reference, not semantic truth."""
    if not isinstance(entry, dict):
        return False
    path = Path(entry.get('path', ''))
    if not path.is_absolute():
        path = base / path
    return (path.is_file() and bool(entry.get('locator'))
            and entry.get('sha256') == digest(path))


def definitions(case, rubric):
    return {**rubric['common'], **{key: rubric['case'][key] for key in case['checks']}}


def init_record(case, suite, rubric):
    return dict(version=1, suite=suite['id'], case=case['id'], attempt=1,
                input_sha256=digest(HERE / case['prompt']),
                environment={'app': 'unconfirmed', 'model': 'unconfirmed',
                             'app_version': 'unconfirmed', 'engine_version': 'unconfirmed',
                             'reasoning_effort': 'unconfirmed', 'local': None, 'evidence': None},
                started_at=None, finished_at=None, transcript=None, outcome='not_run',
                checks={key: {'status': 'pending', 'reason': '', 'evidence': []}
                        for key in definitions(case, rubric)},
                runner_report=None, human_review={'approved': None, 'score': None, 'evidence': None},
                notes=[], failures=[])


def runner_diagnostics(entry, base):
    if not entry:
        return False, False, [{'code': 'NOT_GENERATED', 'status': 'pending', 'reason': '실제 실행기 보고서 미등록'}]
    if not evidence_ok(entry, base):
        return False, False, [{'code': 'STALE_REPORT', 'status': 'unverified', 'reason': '보고서 누락/해시 불일치'}]
    report_path = Path(entry['path'])
    if not report_path.is_absolute():
        report_path = base / report_path
    report = read(report_path)
    issues = []
    stage_codes = {'structure': 'PACKAGE', 'namespaces': 'PACKAGE', 'finalize': 'LAYOUT',
                   'layout': 'LAYOUT', 'page_guard': 'LAYOUT', 'hancom': 'COM', 'render': 'RENDER',
                   'visual_review': 'RENDER', 'content': 'CONTENT', 'values': 'CONTENT',
                   'gonmun': 'RULES', 'budget_names': 'BUDGET', 'related': 'INPUT',
                   'timetable': 'TIMETABLE', 'attachments': 'ATTACHMENT', 'compare': 'COMPARE'}
    try:
        if h.freshness(report):
            issues.append({'code': 'STALE_ARTIFACT', 'status': 'unverified', 'reason': '입력·원본·검증 파일 해시 변경'})
        state = h.result_state(report)
        if not report.get('dependencies'):
            issues.append({'code': 'MISSING_DEPENDENCIES', 'status': 'unverified', 'reason': '원본/검증 코드 해시 증거 없음'})
        for stage in h.STAGES:
            observed = report.get('stages', {}).get(stage, {})
            status = observed.get('status', 'unconfirmed')
            optional = {'render', 'visual_review', 'budget_names', 'related', 'timetable', 'compare'}
            if status == 'not_applicable' and (stage not in optional or not observed.get('reason')):
                issues.append({'code': stage_codes[stage], 'stage': stage, 'status': 'unverified',
                               'reason': '필수 단계의 해당 없음 처리 또는 적용 제외 근거 누락'})
            if status not in ('pass', 'not_applicable'):
                issues.append({'code': stage_codes[stage], 'stage': stage, 'status': status,
                               'reason': observed.get('reason', '미실행 또는 증거 없음')})
        if report.get('stages', {}).get('build', {}).get('status', 'pass') != 'pass':
            issues.append({'code': 'BUILD', 'status': 'unverified', 'reason': '문서 생성 미완료'})
        verified = state == 'pass' and not issues
        delivery = report.get('delivery', {})
        copy = report.get('copy', {})
        local = Path(delivery.get('local', ''))
        remote = Path(copy.get('directory', '')) / local.name
        delivered = (verified and copy.get('status') == 'pass' and local.is_file() and remote.is_file()
                     and digest(local) == report.get('validated_sha256') == digest(remote)
                     and delivery.get('sent') is False)
        if verified and not delivered:
            issues.append({'code': 'DELIVERY', 'status': 'pending', 'reason': 'output·OneDrive 최종본 해시/미발송 확인 필요'})
        return verified, delivered, issues
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return False, False, [{'code': 'REPORT_FORMAT', 'status': 'unverified', 'reason': str(exc)}]


def grade(record, case, suite, rubric, base):
    if record.get('case') != case['id'] or record.get('suite') != suite['id']:
        raise ValueError('사례/평가 세트 ID 불일치')
    issues = []
    if record.get('input_sha256') != digest(HERE / case['prompt']):
        issues.append({'code': 'INPUT_CHANGED', 'status': 'unverified', 'reason': '고정 입력이 바뀜; 이전 결과와 비교 불가'})
    started = bool(record.get('started_at')) and evidence_ok(record.get('transcript'), base)
    environment = record.get('environment', {})
    actual_work = (started and environment.get('app') == 'ChatGPT Work'
                   and environment.get('local') is True and evidence_ok(environment.get('evidence'), base))
    if not actual_work:
        issues.append({'code': 'ENV', 'status': 'unverified', 'reason': '실제 Work 로컬 실행의 대화·환경 증거 필요'})
    checks = record.get('checks', {})
    required = definitions(case, rubric)
    unexpected = set(checks) - set(required)
    if unexpected:
        raise ValueError('알 수 없는 평가 항목: ' + ', '.join(sorted(unexpected)))
    passed = failed = unverified = 0
    critical = []
    for key, (code, description) in required.items():
        observation = checks.get(key, {})
        status = observation.get('status', 'pending')
        if status not in ('pass', 'fail', 'pending', 'blocked'):
            raise ValueError('허용하지 않는 판정: ' + key + '=' + str(status))
        refs = observation.get('evidence', [])
        backed = bool(observation.get('reason')) and bool(refs) and all(evidence_ok(x, base) for x in refs)
        effective = status if backed else 'unverified'
        if effective == 'pass':
            passed += 1
        elif effective == 'fail':
            failed += 1
            if key in rubric['critical']:
                critical.append(key)
        else:
            unverified += 1
        if effective != 'pass':
            issues.append({'code': code, 'check': key, 'status': effective,
                           'reason': observation.get('reason') or description})
    expected = case['expected_checkpoint']
    allowed = {expected, 'verified_review_copy'}
    if record.get('outcome') not in allowed:
        issues.append({'code': 'OUTCOME', 'status': 'pending', 'reason': '기대 중간 결과: ' + expected})
    checkpoint_pass = not issues and actual_work
    verified, delivered, runner_issues = runner_diagnostics(record.get('runner_report'), base)
    issues.extend(runner_issues)
    review = record.get('human_review', {})
    reviewed = (type(review.get('score')) is int and 1 <= review['score'] <= 5
                and type(review.get('approved')) is bool and evidence_ok(review.get('evidence'), base))
    accepted = checkpoint_pass and delivered and reviewed and review['approved']
    return dict(case=case['id'], title=case['title'], real_work_started=actual_work,
                outcome=record.get('outcome'), checkpoint_pass=checkpoint_pass,
                checks={'pass': passed, 'fail': failed, 'unverified': unverified, 'total': len(required)},
                critical_failures=critical, document_verified=verified and actual_work,
                delivered=delivered and actual_work, human_reviewed=reviewed,
                accepted_document=accepted, quality_score=review.get('score') if reviewed else None,
                diagnostics=issues)


def summarize(rows):
    return dict(planned=len(rows), work_runs_started=sum(x['real_work_started'] for x in rows),
                checkpoint_passed=sum(x['checkpoint_pass'] for x in rows),
                documents_verified=sum(x['document_verified'] for x in rows),
                documents_delivered=sum(x['delivered'] for x in rows),
                documents_human_accepted=sum(x['accepted_document'] for x in rows),
                diagnostic_counts=dict(Counter(i['code'] for x in rows for i in x['diagnostics'])),
                note='미실행/보류를 작성 완료로 세지 않음. 5건은 탐색 평가이며 안정성 통계나 기존 36회 인수를 대체하지 않음.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'score'))
    parser.add_argument('--run-dir', required=True)
    args = parser.parse_args()
    folder = Path(args.run_dir).resolve()
    if not folder.is_relative_to(ROOT.resolve()):
        raise ValueError('실행 기록은 Hwp_doc 프로젝트 안에만 저장하세요')
    suite, rubric = read(HERE / 'suite.json'), read(HERE / 'rubric.json')
    if args.command == 'init':
        folder.mkdir(parents=True, exist_ok=True)
        if any((folder / (c['id'] + '.json')).exists() for c in suite['cases']):
            raise ValueError('기존 실행 기록을 덮어쓰지 않습니다. score를 사용하세요')
        for case in suite['cases']:
            target = folder / (case['id'] + '.json')
            with target.open('x', encoding='utf-8') as stream:
                json.dump(init_record(case, suite, rubric), stream, ensure_ascii=False, indent=2)
                stream.write('\n')
        print(json.dumps({'initialized': len(suite['cases']), 'work_runs_started': 0,
                          'documents_verified': 0, 'run_dir': str(folder)}, ensure_ascii=False, indent=2))
        return 2
    rows = [grade(read(folder / (c['id'] + '.json')), c, suite, rubric, folder) for c in suite['cases']]
    result = dict(at=datetime.now(timezone.utc).isoformat(), summary=summarize(rows), runs=rows)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(x['accepted_document'] for x in rows) else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
