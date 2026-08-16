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

> ⚠️ 실측으로 확인된 제약사항이나 명세서와 다른 실제 동작은 아래 "알려진 제약사항" 절에
> Claude Code가 개발 완료 후 채워 넣습니다.

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

## 라이선스 / 출처

본 서비스는 한국은행 ECOS Open API가 제공하는 공개 데이터를 활용합니다.
데이터 저작권 및 이용 조건은 [한국은행 경제통계 OPEN API 이용약관](https://ecos.bok.or.kr/)을
따릅니다.

## 알려진 제약사항

_(개발 완료 후 Claude Code가 실측 결과를 기준으로 채워 넣습니다. 예: 선택 파라미터
부분 채움 가능 여부, 한글 파라미터 URL 인코딩 처리 방식 등)_
