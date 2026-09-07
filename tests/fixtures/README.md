# 테스트 픽스처

| 파일 | 출처 |
|---|---|
| `kma_grid_table.csv` | 기상청 동네예보 격자 좌표표 (최종 업데이트 파일_20241031). 공공누리 제1유형. |
| `auth_error.xml` | 공공데이터포털이 인증 실패 시 돌려주는 XML. 활용가이드 기재 형식. |
| `vilage_fcst.json` | **합성본.** 활용가이드의 출력 결과 예시대로 만든 것으로 형식만 정확하다. `uv run python scripts/build_fixture.py --record`로 실제 응답을 녹화해 교체한다. |

픽스처에는 인증키가 들어가면 안 된다. `build_fixture.py --record`는 저장 전에
응답에 키가 되울려 왔는지 확인하고, 있으면 저장하지 않는다.
