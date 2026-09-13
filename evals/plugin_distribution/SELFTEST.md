# 평가 도구 자체 검증 기록

2026. 9. 13. 설계 세션에서 실행했다. **제품 평가·실제 앱 훅·한글 COM·교사 검토 결과가 아니다.** 제품 파일을 import하거나 제품 명령을 실행하지 않았다. 임시 합성 장부를 만들고 지우는 단위시험이며 실제 평가 장부는 초기화하지 않았다.

실행 환경: 현재 운영 PC의 Windows, `C:\Users\22\AppData\Local\Programs\Python\Python312\python.exe`, `-X utf8`.

| 검사 | 실제 결과 |
|---|---|
| `evaluate.py check` | 32개 사례 / 176개 행, schema=pass, product_evaluated=false, exit 0 |
| `python -X utf8 -m unittest discover -s evals/plugin_distribution -p test_evaluate.py -v` | 30개 통과, 18.949초, exit 0 |
| 패키지 JSON 파싱 및 Markdown 상대 링크 | JSON 10개 파싱 성공, 깨진 링크 0개 |

자체시험은 증거 없는 통과, 앱·평가자 불일치, 필수 환경 기록 누락, 손상된 체크, 누락/변경된 증거, 대상·fixture 변경, 누락 행, 기존 실행 폴더 덮어쓰기 등을 검사한다. 합성 양성 대조군은 집계 분기를 시험하기 위한 자료이며 실제 앱·사람 실적으로 합산하지 않는다.

실제 평가자는 START.md에 따라 별도 세션·동결된 후보·허용된 시험 자료로 시작한다. 모든 제품 판정은 미실행이며 배포 준비 완료를 주장하지 않는다.
