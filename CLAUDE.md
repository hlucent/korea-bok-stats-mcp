# CLAUDE.md — Claude Code 실행 지침 (korea-bok-stats-mcp)

## 0. 절대 규칙

- **DEVPLAN.md 하나만 먼저 읽고 시작한다.** 다른 문서(README, DEVLOG)는 이 시점에 재탐색하지 않는다.
- **웹서치 금지.** API 스펙은 DEVPLAN.md에 이미 정리되어 있다.
- 불확실하면 추측성 재설계 대신 **기본값 1개로 구현 후 DEVLOG.md에 "확인 필요"로 기록**한다.
- 동일 오류 최대 3회까지만 재시도. 3회 실패 시 기록하고 사용자에게 보고한다.
- **너(Claude Code)의 역할은 "코드 구현 + 로컬 실측 테스트"까지다.**
  `fly launch`, `fly secrets set`, `flyctl deploy`, `fly logs` 등 fly.io 관련 명령은
  **절대 스스로 실행하지 않는다.** 배포는 사용자가 PowerShell에서 직접 수행한다.
- 배포 준비(코드 구현, 로컬 테스트, git commit/push)가 끝나면 아래 "작업 순서"의 정지 시점에서
  멈추고, "정지 시 출력할 안내 문구"를 그대로 출력한다.

---

## 1. 기술적으로 반드시 적용할 것

### 1-1. `.env` 관련
- `.env`를 새로 쓸 때는 항상 **UTF-8(BOM 없음)**으로 저장한다.
  ```python
  # [System.IO.File]::WriteAllText(경로, "KEY=값", [System.Text.UTF8Encoding]::new($false))
  ```
- BOM 문제로 `python-dotenv`가 키를 못 읽는 사례가 있었으니 이 가능성을 항상 인지할 것.

### 1-2. `server.py`의 `mcp.run()`은 항상 `stateless_http=True` 포함
```python
mcp.run(transport="streamable-http", host="0.0.0.0", port=port, stateless_http=True)
```
이유: fly.io가 머신을 2대(고가용성) 띄우는데, 세션이 프로세스 인메모리에만 저장되면
다른 머신으로 라우팅될 때 404가 발생한다. **이 옵션 없이 배포하면 Claude.ai 커넥터에서
"사용 가능한 도구 없음"으로 보이는 문제가 발생하므로 절대 빠뜨리지 않는다.**

### 1-3. ECOS 특유의 URL 구조 처리 (DEVPLAN.md 1절 참고)
- ECOS는 **경로 세그먼트(path segment) 기반** URL이다. 쿼리파라미터가 아니다.
  `https://ecos.bok.or.kr/api/{서비스명}/{인증키}/{요청유형}/{언어구분}/{시작건수}/{종료건수}/...`
- 인증키를 URL 경로에 삽입할 때 `os.environ["BOK_API_KEY"]`로 읽고, f-string으로 조립한다.
  **절대 하드코딩 금지.**
- 한글이 경로 세그먼트로 들어가는 API(StatisticMeta의 데이터명, StatisticWord의 용어)는
  `urllib.parse.quote()`로 인코딩 후 삽입한다. httpx가 자동으로 처리해주는지 실측 테스트에서
  반드시 확인하고, 자동 처리가 안 되면 명시적으로 quote를 적용한다.
- 요청유형은 무조건 `json`, 언어구분은 무조건 `kr`로 고정해서 호출한다(파싱 단순화).

---

## 2. API 키 취급 원칙

- 실제 키 값은 코드에 하드코딩하지 않고 항상 `os.environ`으로 읽는다.
- `.env` 파일을 갱신했다고 사용자가 말하면, **재테스트 전에 실제로 값이 바뀌었는지 확인하는
  단계를 거친다.** 파일 크기(바이트 수) 또는 값의 앞 몇 글자만이라도 이전 값과 달라졌는지 비교.
- 키를 표준출력에 그대로 찍는 디버깅 코드는 피하고, 꼭 필요하면 일부만 마스킹해서 출력한다
  (예: 앞 4자리 + `...` + 길이).
- 재테스트 요청을 받으면 "이전과 동일한 키인지, 새 키인지"를 먼저 확인하고 진행한다.

---

## 3. 작업 순서

1. `requirements.txt` (`fastmcp`, `httpx`, `python-dotenv`)
2. `bok_api.py` — API 호출 + 에러코드 매핑(DEVPLAN.md 3절) + URL 경로 조립 헬퍼
   - 6개 서비스 공통으로 쓸 수 있는 저수준 호출 함수 하나를 만들고, 서비스별 파라미터만
     리스트로 넘기는 구조를 권장 (중복 최소화)
3. `server.py` — 툴 6개 정의(DEVPLAN.md 5절 표 그대로), docstring에 필드/단위 명시,
   `stateless_http=True` 필수 반영, **아래 5절 rate limit 미들�지어 포함**
4. `.env.example` (`BOK_API_KEY=`), `.gitignore`
5. 로컬 테스트 (실제 키로 6개 툴 전부 호출, 응답 건수(list_total_count 등) 실측 확인)
   - **DEVPLAN.md 4절 "실측 필요 항목" 5가지를 전부 순서대로 검증한다.**
     특히 StatisticSearch의 통계항목코드1~4 선택 파라미터는 아래 조합을 모두 테스트:
     - 항목코드 전부 생략 (세그먼트 자체 제거)
     - 항목코드1만 채우고 나머지 생략
     - 항목코드 전부 채움
     어떤 조합이 정상 동작하고 어떤 조합이 에러(500 등)를 내는지 확인 후 6절 절차대로 처리.
6. FastMCP 서버 스모크 테스트 (initialize 요청까지만 — 세션 재사용 시나리오는 배포 후 검증)
7. `Dockerfile`, `fly.toml`
8. README/DEVLOG 갱신 (README에는 실측으로 확인된 제약사항을 실제 동작 기준으로 정확히 기술.
   명세서상 스펙과 실제 동작이 다르면 실제 동작을 기준으로 서술)
9. `git add/commit/push`까지 수행 (push는 자동으로 진행해도 됨 — 본인 소유 private 저장소 백업)
10. **여기서 정지** — 아래 "정지 시 출력할 안내 문구"를 그대로 출력

---

## 4. 하지 말 것

- 툴 개수를 6개보다 늘리거나 줄이지 않기 (DEVPLAN.md 5절 표 그대로)
- 인증키 하드코딩 금지
- `stateless_http=True` 누락 금지
- `fly launch` / `fly secrets set` / `flyctl deploy` / `fly logs` 자동 실행 금지
- rate limit 미들웨어 누락 금지 (인증키 없이 공개하는 서버이므로 5절 필수 적용)
- 매 파일 생성마다 개별 승인이 반복되면, 사용자에게 "이번 세션 전체 편집 허용"으로 넘어가라고
  첫 승인 시점에 안내 (단, 실제 API 키로 네트워크 호출하는 `python -c` 류는 매번 개별 확인 권장)

---

## 5. MCP 서버 보안 정책 (rate limit — 필수 적용)

이 MCP는 API 키 인증 없이 URL만으로 Claude.ai 커넥터 연결이 가능하도록 공개 배포되므로,
**반드시** 아래 3단계 IP 기반 rate limit을 기본 적용한다. server.py(또는 별도 미들웨어 파일)에
FastMCP 서버 초기화 전/중간 계층으로 구현하며, 항상 아래 순서로 검사한다.

1. **분당 호출 제한**: 같은 IP 기준 1분(60초) 슬라이딩 윈도우 내 3회 초과 시 429 반환
2. **반복 위반 시 임시 차단**: 1시간 내 429 응답을 5회 이상 받은 IP는 24시간 동안 완전 차단
3. **일일 총량 제한**: IP당 24시간(rolling) 기준 총 호출 30회 초과 시 429 반환

**구현 원칙**:
- 저장 방식은 in-memory(Map/dict 등)로 충분하다. 서버 재시작 시 초기화되는 것은 허용한다.
- IP는 `X-Forwarded-For` 헤더(fly.io 프록시 환경)에서 추출, 없으면 요청의 remote address 사용.
- 429 응답 시 원인을 간단히 알 수 있는 메시지 포함 (예: "Rate limit exceeded. Try again later.").
- `stateless_http=True`와 별개 — IP 카운터는 멀티 머신 환경에서 완전히 공유되지 않아도 무방.

---

## 6. 실측 필요 항목 처리 절차

명세서와 실제 API 동작이 다르다는 게 실측으로 확인되면, 아래 순서로 처리한다.

1. **재현 확인**: 같은 조건으로 최소 2회 이상 같은 결과가 나오는지 확인.
2. **원인 분리**: 코드/URL 구조 문제인지, API 자체의 특이 동작인지 구분. 필요하면 원시 URL
   직접 호출 등으로 코드를 거치지 않은 최소 재현을 시도.
3. **스스로 판단 가능한 검증을 다 시도한 후에만** DEVLOG.md에 미확인 사항으로 남긴다. 사용자에게
   자동으로 묻지 않는다. 키 문제, URL 인코딩 문제, 파라미터 조합 문제 등은 "동일 오류 3회 재시도"
   원칙 안에서 순서대로 검증.
4. **검증 결과를 DEVLOG.md에 기록**: 무엇을 시도했고, 무엇이 확인됐고, 무엇이 아직 미확인인지
   명확히 남긴다.
5. **코드에 사전 검증 로직 반영**: 발견된 제약을 클라이언트 코드가 미리 걸러서, API 호출 전에
   명확한 에러 메시지로 안내하도록 한다.
6. **README.md/DEVPLAN.md 기술 갱신**: 명세서 스펙과 실제 동작이 다른 부분은 실제 동작 기준으로
   문서를 고친다. 이 갱신도 커밋 대상에 포함한다.

---

## 정지 시 출력할 안내 문구

작업 순서 10번(정지)에 도달하면 아래를 그대로 출력한다:

```
코드 구현과 로컬 실측 테스트가 끝났습니다. 여기서 멈춥니다.

이제 Claude Code 창이 아니라 PowerShell 창에서 아래를 순서대로 직접 실행해주세요:

cd "C:\Users\hwang\Projects\korea-bok-stats-mcp"
fly launch --no-deploy
fly secrets set BOK_API_KEY=발급받은키
flyctl deploy

배포 완료 메시지에 나온 주소 뒤에 "/mcp"를 붙여서
Claude.ai > 설정 > 커넥터 에서 연결하세요.
예: https://<앱이름>.fly.dev/mcp

연결 후에는 반드시 "새 대화창"을 열어서 도구 목록이 뜨는지 확인해주세요.
```
