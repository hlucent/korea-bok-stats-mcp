# DEVLOG.md — korea-bok-stats-mcp

기록 형식:
```
## YYYY-MM-DD

### 시도한 것
- ...

### 확인된 것
- ...

### 아직 미확인
- ...
```

---

## 2026-08-17

### 시도한 것
- 한국은행 ECOS Open API 개발명세서 6종(서비스 통계 목록, 통계 조회 조건 설정,
  통계 세부항목 목록, 100대 통계지표, 통계메타DB, 통계용어사전) xls 파일을 확보하고
  DEVPLAN.md에 스펙을 정리함.

### 확인된 것
- ECOS는 서울시/공공데이터포털과 달리 **경로 세그먼트 기반 URL**을 사용함
  (쿼리파라미터 아님, `/서비스명/인증키/요청유형/언어구분/시작건수/종료건수/...` 순서 고정).
- 6개 API 모두 동일한 에러코드 체계(정보-100/200, 에러-100/101/200/300/301/400/500/600/601/602)
  를 공유함.
- 실제 수치 데이터를 가져오는 API는 `StatisticSearch`이며, 통계표코드+주기+기간이 필수,
  통계항목코드1~4는 선택.

### 아직 미확인 (당시)
- StatisticSearch의 선택 파라미터(통계항목코드1~4) 생략 방식 — 샘플 URL에 `?/?/?`로 표기된
  것의 실제 의미 (Claude Code 실측 단계에서 확인 예정)
- 한글이 경로에 들어가는 StatisticMeta/StatisticWord의 URL 인코딩 자동 처리 여부
- JSON 응답 시 최상위 구조 및 에러 응답 형태

---

## 2026-08-17 (실측 단계)

### 시도한 것
- 사용자로부터 실제 BOK_API_KEY를 받아 `.env`에 UTF-8(BOM 없음)로 저장.
- `bok_api.py`, `server.py` 1차 구현 후, 실제 키로 6개 API 전부를 직접 호출하여 검증.
- StatisticSearch 선택 파라미터(통계항목코드1~4)에 대해 "전부 생략", "항목1만 채움",
  "항목1 채우고 2~4는 `?` 리터럴" 3가지 조합을 각각 테스트 (통계표코드 722Y001, 한국은행
  기준금리 사용 — 명세서 샘플의 200Y001/10101 조합은 데이터가 없어 INFO-200만 반환되어
  재선정함).
- StatisticTableList의 통계표코드(선택) 생략 시 세그먼트 완전 제거로 테스트.
- StatisticMeta("경제심리지수"), StatisticWord("소비자동향지수")에 한글을 그대로 붙인 경우와
  `urllib.parse.quote`로 명시 인코딩한 경우를 비교 테스트.
- 콘솔 출력 시 한글이 깨져 보여서, 실제로 잘못된 인코딩으로 온 것인지 raw bytes를 파일로
  저장해 확인.

### 확인된 것
- **선택 파라미터(통계항목코드1~4)**: 세그먼트 완전 생략 / 항목1만 채움 / `?` 리터럴 채움
  3가지 모두 동일하게 정상 동작. "부분 채움 금지" 같은 제약 없음.
- **StatisticTableList 통계표코드 생략**: 세그먼트 완전 제거 방식으로 정상 동작 확인.
- **한글 경로 세그먼트**: httpx가 한글 문자열을 그대로 넘겨도 자동으로 UTF-8 URL 인코딩
  처리함. `urllib.parse.quote` 명시 적용과 결과 동일 (수동 인코딩 불필요).
- **JSON 응답 최상위 구조**: 정상 시 `{"<서비스명>": {"list_total_count": N, "row": [...]}}`,
  에러/데이터없음 시 `{"RESULT": {"CODE": "...", "MESSAGE": "..."}}`. `INFO-200`(데이터 없음)은
  코드상 정상적인 빈 결과로 변환 처리, 그 외 코드는 에러로 취급.
  존재하지 않는 통계표코드(`ZZZZZZZ`)로 조회 시 예외 없이 `INFO-200` → 빈 결과로 처리됨을 확인.
- **응답 인코딩**: 콘솔에서 한글이 깨져 보인 것은 Windows 터미널 코드페이지 문제였고,
  raw bytes는 유효한 UTF-8 (`content-type: application/json; charset=UTF-8`과 일치).
  실제 디코딩/파싱에는 문제없음.
- FastMCP 서버가 `stateless_http=True`로 정상 기동하며 `initialize` 요청에 정상 응답함을
  로컬 스모크 테스트로 확인.

### 아직 미확인
- 없음 (DEVPLAN.md 4절의 실측 필요 항목 5가지 전부 확인 완료).

---

## 2026-08-17 (배포 후 rate limit 디버깅)

### 증상
- 사용자가 배포된 서버에 같은 IP로 5회 연속 curl 호출 → 전부 HTTP 200으로 관측,
  rate limit(1분당 3회 초과 차단)이 작동하지 않는 것으로 의심됨.

### 시도한 것
1. `_extract_ip()`가 `context.fastmcp_context.get_http_request()`를 호출하고 있었는데,
   이는 존재하지 않는 API(`Context`에 해당 메서드 없음)라 매 요청 `AttributeError` 발생 후
   `except Exception`으로 조용히 삼켜짐을 로컬에서 확인. `fastmcp.server.dependencies`의
   모듈 레벨 함수 `get_http_headers()`/`get_http_request()`를 쓰도록 수정하고,
   `Fly-Client-IP` 헤더를 우선 사용(없으면 `X-Forwarded-For`)하도록 변경.
2. 위 수정을 로컬 curl 테스트로 검증 — 동일 IP 5회 연속 호출 시 4번째부터 정상 차단됨을 확인.
   그러나 사용자가 배포 환경에서 재현했을 때도 여전히 전부 200으로 보임.
3. `RateLimitMiddleware.on_call_tool`에 임시 디버그 로그(추출된 IP, 누적 카운트,
   `middleware_id`/`call_log_id`(인스턴스 재생성 여부 확인용), 전체 요청 헤더)를 추가.
   `fly logs`는 CLAUDE.md가 금지한 명령이라 Claude Code가 직접 실행하지 않고,
   사용자가 PowerShell에서 직접 실행해 로그를 붙여넣는 방식으로 진행.
4. 1차 재현 시도: `fly logs`에 `[RATE_LIMIT_DEBUG]` 로그가 전혀 없음 → 확인 결과
   사용자가 디버그 로그 커밋 이전 버전을 배포한 상태였음. 재배포 요청.
5. 재배포 후 2차 재현 시도: PowerShell에서 작은따옴표로 감싼 JSON을 curl에 전달했더니
   따옴표 이스케이핑이 깨져 서버가 `-32700 Parse error`(HTTP 400)로 응답 — 애초에
   `tools/call`까지 도달하지 못해 미들웨어 자체가 실행되지 않은 것이었음. JSON을
   파일로 저장 후 `--data-binary @file`로 전달하는 방식으로 변경.
6. 3차 재현: 올바른 JSON-RPC 요청 5회 연속 전송 후 `fly logs` 확인 결과,
   `[RATE_LIMIT_DEBUG]`에서 `ip=180.70.169.230`(Fly-Client-IP 헤더에서 정확히 추출됨)
   기준으로 1~3번째 `allowed=True`, 4~5번째 `allowed=False`로 **정상 차단됨**을 확인.
   `middleware_id`/`call_log_id`도 5회 요청 내내 동일 — 인스턴스 재생성 문제 없음.

### 확인된 것 (최종 원인)
- **rate limit 로직 자체는 정상 동작하고 있었다.** 애초의 "5회 전부 200" 관측은
  MCP(JSON-RPC over HTTP) 프로토콜의 특성 때문이었다: 툴 호출이 rate limit에 걸려
  차단되어도 **HTTP 상태 코드는 200 OK**로 오고, 대신 JSON-RPC 응답 바디 안에
  `"isError": true`와 `"Rate limit exceeded..."` 메시지가 담겨서 온다. uvicorn access
  log(`"POST /mcp HTTP/1.1" 200 OK`)만 보면 차단 여부를 알 수 없음 — 반드시 응답 바디의
  `isError`/`content.text`를 확인해야 한다.
- 초기 IP 추출 버그(`get_http_request`가 `Context`에 없는 API였던 점)는 실존하는 버그였고
  수정이 필요했던 것은 맞지만, 이번 "rate limit 미작동" 증상의 직접 원인은 아니었다
  (수정 전 코드도 `ip="unknown"`으로나마 전체 클라이언트를 하나의 버킷으로 묶어
  차단 자체는 동작했을 것으로 추정됨. 다만 IP별 분리가 안 되는 것은 실제 버그였으므로
  수정 자체는 유효함).
- 디버깅 중간 단계에서 나온 "재현 안 됨" 두 번은 모두 테스트 방법의 문제였다:
  (1) 디버그 로그가 아직 배포 안 된 이전 버전으로 테스트, (2) PowerShell 작은따옴표
  JSON 이스케이핑 오류로 요청 자체가 400으로 실패.

### 조치
- 디버그 로그는 원인 확정 후 제거하고 원래 코드로 복원.
- `_extract_ip()`의 `get_http_headers`/`get_http_request` 사용은 그대로 유지
  (실제로 정상 동작하며 필요한 수정이었음).
- README.md "알려진 제약사항"에 "차단 시에도 HTTP 200이 오며 응답 바디의 isError로
  판단해야 한다"는 내용 반영.

### 아직 미확인
- 없음.
