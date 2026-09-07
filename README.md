# pykma

기상청 단기예보 API Python SDK. 위경도만 넣으면 된다.

```python
from pykma import KMA

kma = KMA(service_key="...")
print(kma.now(37.5665, 126.9780).temperature)
```

## 설치

```bash
pip install pykma
```

## 인증키

[공공데이터포털](https://www.data.go.kr/data/15084084/openapi.do)에서 **단기예보 조회서비스**를
활용신청한다. 승인에 하루 정도 걸린다. 발급된 키는 `KMA(service_key=...)`로 넘기거나
환경변수 `KMA_SERVICE_KEY`에 둔다.
