"""HWPX 슬롯 추출 (양식 등록부는 0.2.0에서 폐지)."""
from __future__ import annotations

import sys
from zipfile import BadZipFile

import hwpdoc as h


def extracted(path):
    from lxml.etree import XMLSyntaxError
    sys.path.insert(0, str(h.SKILL))
    from hwpx_slots import collect_slots
    try:
        result = collect_slots(path, preview_len=1000000)
    except (BadZipFile, XMLSyntaxError, KeyError) as exc:
        raise ValueError('읽을 수 없는 HWPX 패키지: ' + str(exc)) from exc
    result['source'] = path.name
    return result
