"""Render all PDF pages for review; no visual approval is inferred."""
import argparse
import hashlib
import json
from pathlib import Path

from hwpdoc_config import current_context


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(pdf, output, context):
    import fitz
    pdf, output = Path(pdf).resolve(), Path(output).resolve()
    if not pdf.is_relative_to(context.workspace) or not output.is_relative_to(context.workspace):
        raise ValueError('검토 PDF와 이미지 폴더는 작업 폴더 안에 있어야 합니다')
    receipt = output / 'preview.json'
    if output.exists():
        if not receipt.is_file():
            raise ValueError('기존 미완성 이미지 폴더는 덮어쓰지 않습니다')
        result = json.loads(receipt.read_text(encoding='utf-8'))
        if result.get('pdf', {}).get('sha256') != digest(pdf) or not result.get('images'):
            raise ValueError('기존 이미지 기록과 PDF가 다릅니다')
        for item in result['images']:
            if digest(context.local(item['path'])) != item['sha256']:
                raise ValueError('기존 검토 이미지가 변경됐습니다')
        return result
    with fitz.open(pdf) as document:
        if not document.page_count:
            raise ValueError('PDF에 페이지가 없습니다')
        output.mkdir(parents=True)
        images = []
        for index, page in enumerate(document):
            target = output / f'page-{index + 1:03d}.png'
            page.get_pixmap(dpi=120, alpha=False).save(str(target))
            images.append({'path': target.relative_to(context.workspace).as_posix(), 'sha256': digest(target), 'page': index + 1})
    result = {'pdf': {'path': pdf.relative_to(context.workspace).as_posix(), 'sha256': digest(pdf)},
              'images': images, 'visual_review': 'unconfirmed'}
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    try:
        result = render(args.pdf, args.output_dir, current_context())
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ImportError, ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'unconfirmed', 'reason': str(exc)}, ensure_ascii=False))
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
