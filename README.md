# korea-bok-stats-mcp

한국은행 경제통계시스템(ECOS) Open API를 Claude에서 바로 조회할 수 있게 해주는 MCP 서버입니다.

## 제공하는 도구 (Tools)

| 도구 | 설명 |
|---|---|
| `search_statistic_tables` | 통계표 목록 검색/조회 (예: "본원통화 구성내역" 통계표 코드 찾기) |
| `get_statistic_data` | ★ 실제 시계열 수치 데이터 조회 (예: 2015~2021년 GDP 값) |
| `get_statistic_items` | 특정 통계표의 세부 항목코드 목록 조회 |
| `get_key_statistics` | 100대 주요 통계지표 요약 조회 (경제성장률, 기준금리 등) |
| `get_statistic_meta` | 통계 메타데이터(작성기준, 연혁 등) 조회 |
| `search_statistic_word` | 경제/통계 용어 설명 조회 (803개 용어) |

> ⚠️ 실측으로 확인된 제약사항이나 명세서와 다른 실제 동작은 아래 "알려진 제약사항" 절을 참고하세요.

## 일반적인 사용 흐름

1. `search_statistic_tables`로 원하는 통계의 **통계표코드**를 찾는다
2. (필요시) `get_statistic_items`로 해당 통계표의 **항목코드**를 확인한다
3. `get_statistic_data`로 실제 수치를 조회한다

간단한 지표는 `get_key_statistics`(100대 통계지표)만으로 충분할 수 있습니다.

## 환경 변수

| 변수명 | 설명 |
|---|---|
| `BOK_API_KEY` | 한국은행 ECOS에서 발급받은 Open API 인증키 |

인증키는 [ECOS Open API 서비스](https://ecos.bok.or.kr/api/)에서 회원가입 후 신청하면
보통 1일 이내 발급됩니다.

## 설치 및 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env  # BOK_API_KEY 값을 채워넣기
python server.py
```

## 배포 (Fly.io)

```bash
fly launch --no-deploy
fly secrets set BOK_API_KEY=발급받은키
flyctl deploy
```

## Claude.ai 커넥터 연결

배포 완료 후 나온 주소 뒤에 반드시 `/mcp`를 붙여서 연결합니다.

```
https://<앱이름>.fly.dev/mcp
```

연결 후에는 **새 대화창**을 열어서 도구 목록이 정상적으로 뜨는지 확인하세요.
(기존에 열려 있던 대화창에는 새 커넥터가 자동 반영되지 않을 수 있습니다.)

## 이용 제한 (Rate Limit)

이 서버는 API 키 인증 없이 공개되어 있어 아래 제한이 적용됩니다:
- 1분당 3회 초과 호출 시 일시 차단
- 1시간 내 5회 이상 제한 초과 시 24시간 차단
- 하루 총 30회 초과 호출 시 제한

정상적인 대화 중 필요한 만큼만 도구를 호출하는 경우에는 문제가 되지 않습니다.

> ⚠️ **차단되어도 HTTP 상태 코드는 200 OK로 옵니다.** 이 서버는 MCP(JSON-RPC over HTTP)
> 프로토콜을 쓰기 때문에, rate limit에 걸린 요청도 HTTP 레벨에서는 정상 응답(200)이고,
> 대신 JSON-RPC 응답 바디 안에 `"isError": true`와 `"Rate limit exceeded..."` 메시지가
> 담겨 옵니다. 따라서 `curl` 등으로 직접 테스트할 때 HTTP 상태 코드만 보고 "차단이 안 된다"고
> 판단하면 안 되고, 반드시 응답 바디의 `isError`/`content[].text`를 확인해야 합니다
> (2026-08-17 배포 환경 실측으로 확인).

## 라이선스 / 출처

본 서비스는 한국은행 ECOS Open API가 제공하는 공개 데이터를 활용합니다.
데이터 저작권 및 이용 조건은 [한국은행 경제통계 OPEN API 이용약관](https://ecos.bok.or.kr/)을
따릅니다.

## 알려진 제약사항

2026-08-17 실제 키로 6개 API 전부 호출하여 확인한 내용입니다.

- **StatisticSearch 선택 파라미터(통계항목코드1~4)**: 세그먼트를 완전히 생략(예:
  `.../722Y001/M/202301/202312`)해도, 통계항목코드1만 채우고 2~4를 생략해도, 명세서 샘플처럼
  `?`를 리터럴로 채워도(`.../0101000/?/?/?`) 모두 동일하게 정상 동작함을 확인했습니다.
  즉 "부분 채움 금지" 같은 제약은 없습니다.
- **StatisticTableList의 통계표코드(선택)**: 생략 시 세그먼트를 완전히 제거하면 정상
  동작합니다 (빈 세그먼트를 남길 필요 없음).
- **한글 경로 세그먼트 URL 인코딩** (StatisticMeta의 데이터명, StatisticWord의 용어):
  httpx가 한글 문자열을 그대로 전달해도 자동으로 UTF-8 URL 인코딩을 처리합니다. 별도로
  `urllib.parse.quote`를 적용한 결과와 동일했으므로, 이 서버는 한글을 그대로 전달합니다.
- **JSON 응답 최상위 구조**: 정상 응답은 `{"<서비스명>": {"list_total_count": N, "row": [...]}}`
  형태이고, 에러/데이터없음 응답은 `{"RESULT": {"CODE": "...", "MESSAGE": "..."}}` 형태입니다.
  `CODE`가 `INFO-200`(데이터 없음)인 경우는 에러로 취급하지 않고 빈 결과(`list_total_count: 0`)로
  변환해서 반환합니다. 그 외 코드는 에러로 처리되어 도구 응답에 `{"error": "[코드] 메시지"}`
  형태로 담깁니다.
- **응답 인코딩**: HTTP 헤더는 `charset=UTF-8`로 표기되며 실제로도 유효한 UTF-8 바이트입니다.
  (일부 터미널에서 콘솔 출력 시 한글이 깨져 보일 수 있으나, 이는 콘솔 코드페이지 문제일 뿐
  응답 데이터 자체는 정상입니다.)
- **Rate limit 클라이언트 IP 추출**: fly.io 배포 환경에서는 `Fly-Client-IP` 헤더(가장 신뢰할
  수 있는 실제 클라이언트 IP)를 우선 사용하고, 없으면 `X-Forwarded-For`의 첫 번째 값을
  사용합니다. 배포 환경 실측(2026-08-17)으로 `Fly-Client-IP`가 정상적으로 들어오고
  IP별로 카운터가 올바르게 분리됨을 확인했습니다.
- **Rate limit 차단 시 HTTP 상태 코드**: 위 "이용 제한" 절 참고 — 차단되어도 HTTP 200이
  오며, 차단 여부는 JSON-RPC 응답 바디의 `isError` 필드로 판단해야 합니다.
