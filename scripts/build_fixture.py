"""단기예보 응답 픽스처를 만든다.

인증키가 있으면 실제 호출을 녹화하고(--record), 없으면 활용가이드에 적힌
봉투 형식대로 합성한다. 합성본은 형식만 정확하고 값은 그럴듯한 가짜다.

    uv run python scripts/build_fixture.py            # 합성
    uv run python scripts/build_fixture.py --record   # 실제 호출 녹화
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent.parent / "tests" / "fixtures" / "vilage_fcst.json"
URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

# 시간대마다 실려 오는 카테고리와 값. 활용가이드의 출력 결과 예시를 따랐다.
_HOURLY = [
    ("TMP", "{tmp}"),
    ("UUU", "-1.5"),
    ("VVV", "0.8"),
    ("VEC", "297"),
    ("WSD", "1.7"),
    ("SKY", "{sky}"),
    ("PTY", "{pty}"),
    ("POP", "{pop}"),
    ("WAV", "0.5"),
    ("PCP", "{pcp}"),
    ("REH", "{reh}"),
    ("SNO", "적설없음"),
]

# (시각, 기온, 하늘, 강수형태, 강수확률, 강수량, 습도)
_SLOTS = [
    ("1500", "27", "1", "0", "0", "강수없음", "45"),
    ("1600", "27", "1", "0", "0", "강수없음", "45"),
    ("1700", "26", "3", "0", "20", "강수없음", "50"),
    ("1800", "24", "4", "1", "60", "1.0mm 미만", "70"),
    ("1900", "23", "4", "1", "80", "30.0~50.0mm", "85"),
    ("2000", "22", "4", "1", "70", "50.0mm 이상", "90"),
    ("2100", "22", "4", "0", "30", "강수없음", "80"),
]


def synthesize() -> dict:
    items = []
    for time, tmp, sky, pty, pop, pcp, reh in _SLOTS:
        for category, template in _HOURLY:
            items.append(
                {
                    "baseDate": "20260907",
                    "baseTime": "1400",
                    "category": category,
                    "fcstDate": "20260907",
                    "fcstTime": time,
                    "fcstValue": template.format(
                        tmp=tmp, sky=sky, pty=pty, pop=pop, pcp=pcp, reh=reh
                    ),
                    "nx": 60,
                    "ny": 127,
                }
            )
    # TMN/TMX는 하루에 한 번만 실려 온다.
    items.append(
        {
            "baseDate": "20260907",
            "baseTime": "1400",
            "category": "TMX",
            "fcstDate": "20260907",
            "fcstTime": "1500",
            "fcstValue": "27.0",
            "nx": 60,
            "ny": 127,
        }
    )
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
            "body": {
                "dataType": "JSON",
                "items": {"item": items},
                "pageNo": 1,
                "numOfRows": 1000,
                "totalCount": len(items),
            },
        }
    }


def record() -> dict:
    key = os.environ.get("KMA_SERVICE_KEY")
    if not key:
        sys.exit("KMA_SERVICE_KEY가 없다.")
    params = urllib.parse.urlencode(
        {
            "serviceKey": urllib.parse.unquote(key) if "%" in key else key,
            "pageNo": 1,
            "numOfRows": 300,
            "dataType": "JSON",
            "base_date": "20260907",
            "base_time": "1400",
            "nx": 60,
            "ny": 127,
        }
    )
    with urllib.request.urlopen(f"{URL}?{params}") as response:
        body = json.load(response)
    if key in json.dumps(body):
        sys.exit("응답에 인증키가 되울려 왔다. 저장하지 않는다.")
    return body


def main() -> None:
    body = record() if "--record" in sys.argv else synthesize()
    OUT.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{OUT} 에 {body['response']['body']['totalCount']}행 저장")


if __name__ == "__main__":
    main()
