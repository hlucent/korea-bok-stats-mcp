# DEVPLAN.md — 한국은행 ECOS Open API MCP

## 0. 개요

- **대상 API**: 한국은행 경제통계시스템(ECOS) Open API
- **베이스 URL**: `https://ecos.bok.or.kr/api/`
- **저장소명**: `korea-bok-stats-mcp`
- **인증 방식**: 요청 URL 경로에 인증키를 직접 삽입 (쿼리파라미터 아님, 서울시 방식과 유사)
- **환경변수명**: `BOK_API_KEY`
- **응답 포맷**: XML 또는 JSON (요청유형 파라미터로 지정) — **본 프로젝트는 JSON으로 통일해서 호출**
  (파싱 단순화를 위해 요청유형=json 고정, 언어구분=kr 고정)

---

## 1. URL 구조 공통 규칙

ECOS는 6개 서비스 모두 아래와 같은 **경로 기반(path-based)** URL 구조를 공유한다.
(공공데이터포털의 쿼리파라미터 방식과 다름 — 서울시 열린데이터광장과 유사한 방식)

```
https://ecos.bok.or.kr/api/{서비스명}/{인증키}/{요청유형}/{언어구분}/{요청시작건수}/{요청종료건수}/{서비스별 추가 파라미터...}
```

- 각 세그먼트는 `/`로 구분되며 **순서가 고정**되어 있다. 값이 없는 선택 파라미터는 세그먼트를
  비워두는 것이 아니라 **아예 잘라내는 방식**(뒤쪽 옵션 파라미터 생략)일 가능성이 높다 — 실측 필요
  (2절 "실측 필요 항목" 참고).
- 인증키는 URL 경로 세그먼트이므로, 절대 쿼리스트링 인코딩이 아니라 path segment로 그대로 삽입.

---

## 2. API 6종 상세 스펙

### 2-1. StatisticTableList (서비스 통계 목록)

**용도**: 어떤 통계표들이 존재하는지 목록/검색

**요청 파라미터** (경로 순서대로):
| 순서 | 파라미터 | 필수 | 예시 | 설명 |
|---|---|---|---|---|
| 1 | 서비스명 | Y | StatisticTableList | 고정값 |
| 2 | 인증키 | Y | (BOK_API_KEY) | |
| 3 | 요청유형 | Y | json | xml/json |
| 4 | 언어구분 | Y | kr | kr/en |
| 5 | 요청시작건수 | Y | 1 | |
| 6 | 요청종료건수 | Y | 10 | |
| 7 | 통계표코드 | **N** | 102Y004 | 특정 통계표만 조회 시 |

**출력 필드**:
| 필드(영문) | 크기 | 설명 |
|---|---|---|
| P_STAT_CODE | 8 | 상위통계표코드 |
| STAT_CODE | 8 | 통계표코드 |
| STAT_NAME | 200 | 통계명 |
| CYCLE | 2 | 주기(년/분기/월) |
| SRCH_YN | 1 | 검색가능여부(Y/N) |
| ORG_NAME | 50 | 출처 |

**샘플 URL**: `https://ecos.bok.or.kr/api/StatisticTableList/sample/xml/kr/1/10/102Y004`

---

### 2-2. StatisticSearch (통계 조회 조건 설정) — ★ 핵심 API, 실제 수치 데이터 조회

**용도**: 통계표코드 + 항목코드로 실제 시계열 수치 데이터를 가져온다.

**요청 파라미터** (경로 순서대로):
| 순서 | 파라미터 | 필수 | 예시 | 설명 |
|---|---|---|---|---|
| 1 | 서비스명 | Y | StatisticSearch | 고정값 |
| 2 | 인증키 | Y | (BOK_API_KEY) | |
| 3 | 요청유형 | Y | json | |
| 4 | 언어구분 | Y | kr | |
| 5 | 요청시작건수 | Y | 1 | |
| 6 | 요청종료건수 | Y | 10 | |
| 7 | 통계표코드 | Y | 200Y001 | StatisticTableList에서 확인 |
| 8 | 주기 | Y | A | 년:A, 반년:S, 분기:Q, 월:M, 반월:SM, 일:D |
| 9 | 검색시작일자 | Y | 2015 | 주기별 형식 다름 (아래 참고) |
| 10 | 검색종료일자 | Y | 2021 | |
| 11 | 통계항목코드1 | **N** | 10101 | StatisticItemList에서 확인 |
| 12 | 통계항목코드2 | **N** | ? | |
| 13 | 통계항목코드3 | **N** | ? | |
| 14 | 통계항목코드4 | **N** | ? | |

**검색시작/종료일자 형식 (주기별)**:
| 주기 | 형식 예시 |
|---|---|
| A(년) | 2015 |
| S(반년) | 2015S1 |
| Q(분기) | 2015Q1 |
| M(월) | 201501 |
| SM(반월) | 201501S1 |
| D(일) | 20150101 |

**출력 필드**:
| 필드(영문) | 크기 | 설명 |
|---|---|---|
| STAT_CODE | 8 | 통계표코드 |
| STAT_NAME | 200 | 통계명 |
| ITEM_CODE1~4 | 20 | 통계항목코드1~4 |
| ITEM_NAME1~4 | 200 | 통계항목명1~4 |
| UNIT_NAME | 200 | **단위** (예: 십억원, %, ㎍/㎥ 등 — 툴 docstring에 반드시 명시) |
| WGT | 22 | 가중치 |
| TIME | 8 | 시점 |
| DATA_VALUE | 23 | **값 (실제 수치)** |

**샘플 URL**: `https://ecos.bok.or.kr/api/StatisticSearch/sample/xml/kr/1/10/200Y001/A/2015/2021/10101/?/?/?`

> ⚠️ 샘플 URL에 `?/?/?`가 그대로 노출됨 — 선택 파라미터(통계항목코드2~4)를 생략할 때
> 실제로 물음표 문자를 넣는 것인지, 세그먼트 자체를 잘라내는 것인지 명세서만으로는 불명확.
> **실측 필수 항목** (아래 3절 참고).

---

### 2-3. StatisticItemList (통계 세부항목 목록)

**용도**: 특정 통계표코드에 속한 항목코드(ITEM_CODE) 체계를 조회. StatisticSearch에 넣을
통계항목코드를 알아내는 데 사용.

**요청 파라미터**:
| 순서 | 파라미터 | 필수 | 예시 |
|---|---|---|---|
| 1 | 서비스명 | Y | StatisticItemList |
| 2 | 인증키 | Y | |
| 3 | 요청유형 | Y | json |
| 4 | 언어구분 | Y | kr |
| 5 | 요청시작건수 | Y | 1 |
| 6 | 요청종료건수 | Y | 10 |
| 7 | 통계표코드 | Y | 601Y002 |

**출력 필드**:
| 필드(영문) | 크기 | 설명 |
|---|---|---|
| STAT_CODE | 8 | 통계표코드 |
| STAT_NAME | 200 | 통계명 |
| GRP_CODE | 20 | 항목그룹코드 |
| GRP_NAME | 60 | 항목그룹명 |
| ITEM_CODE | 20 | 통계항목코드 |
| ITEM_NAME | 200 | 통계항목명 |
| P_ITEM_CODE | 8 | 상위통계항목코드 |
| P_ITEM_NAME | 200 | 상위통계항목명 |
| CYCLE | 2 | 주기 |
| START_TIME | 8 | 수록시작일자 |
| END_TIME | 8 | 수록종료일자 |
| DATA_CNT | 22 | 자료수 |
| UNIT_NAME | 200 | **단위** |
| WEIGHT | 22 | 가중치 |

**샘플 URL**: `https://ecos.bok.or.kr/api/StatisticItemList/sample/xml/kr/1/10/043Y070/`

---

### 2-4. KeyStatisticList (100대 통계지표)

**용도**: 한국은행/타기관 100대 주요 통계지표 요약 조회. 통계표코드 불필요 — 파라미터 단순.

**요청 파라미터**:
| 순서 | 파라미터 | 필수 | 예시 |
|---|---|---|---|
| 1 | 서비스명 | Y | KeyStatisticList |
| 2 | 인증키 | Y | |
| 3 | 요청유형 | Y | json |
| 4 | 언어구분 | Y | kr |
| 5 | 요청시작건수 | Y | 1 |
| 6 | 요청종료건수 | Y | 10 |

**출력 필드**:
| 필드(영문) | 크기 | 설명 |
|---|---|---|
| CLASS_NAME | 400 | 통계그룹명 |
| KEYSTAT_NAME | 200 | 통계명 |
| DATA_VALUE | 23 | 값 |
| CYCLE | 13 | 시점(최근 수록시점, 필드명은 CYCLE이지만 실제로는 시점값) |
| UNIT_NAME | 200 | **단위** |

**샘플 URL**: `https://ecos.bok.or.kr/api/KeyStatisticList/sample/xml/kr/1/10`

---

### 2-5. StatisticMeta (통계메타DB)

**용도**: 특정 데이터명(예: "경제심리지수")에 대한 작성기준/연혁 등 메타데이터 조회.
15개 통계에 대해서만 제공(명세서 기준).

**요청 파라미터**:
| 순서 | 파라미터 | 필수 | 예시 |
|---|---|---|---|
| 1 | 서비스명 | Y | StatisticMeta |
| 2 | 인증키 | Y | |
| 3 | 요청유형 | Y | json |
| 4 | 언어구분 | Y | kr |
| 5 | 요청시작건수 | Y | 1 |
| 6 | 요청종료건수 | Y | 10 |
| 7 | 데이터명 | Y | 경제심리지수 |

> ⚠️ 데이터명이 한글 문자열 그대로 URL 경로에 들어감 — URL 인코딩(quote) 필수.
> httpx가 자동 처리하는지, 수동으로 `urllib.parse.quote` 해야 하는지 실측 필요.

**출력 필드**:
| 필드(영문) | 크기 | 설명 |
|---|---|---|
| LVL | 2 | 레벨 |
| P_CONT_CODE | 8 | 상위통계항목코드 |
| CONT_CODE | 8 | 통계항목코드 |
| CONT_NAME | 200 | 통계항목명 |
| META_DATA | 200 | 메타데이터 내용 |

**샘플 URL**: `https://ecos.bok.or.kr/api/StatisticMeta/sample/xml/kr/1/10/경제심리지수`

---

### 2-6. StatisticWord (통계용어사전)

**용도**: 경제/통계 용어 설명 조회 (총 803개 용어).

**요청 파라미터**:
| 순서 | 파라미터 | 필수 | 예시 |
|---|---|---|---|
| 1 | 서비스명 | Y | StatisticWord |
| 2 | 인증키 | Y | |
| 3 | 요청유형 | Y | json |
| 4 | 언어구분 | Y | kr |
| 5 | 요청시작건수 | Y | 1 |
| 6 | 요청종료건수 | Y | 10 |
| 7 | 용어 | Y | 소비자동향지수 |

> ⚠️ StatisticMeta와 마찬가지로 한글 경로 세그먼트 — URL 인코딩 실측 필요.

**출력 필드**:
| 필드(영문) | 크기 | 설명 |
|---|---|---|
| WORD | 100 | 용어 |
| CONTENT | 4000 | 용어설명 |

**샘플 URL**: `https://ecos.bok.or.kr/api/StatisticWord/sample/xml/kr/1/10/소비자동향지수`

---

## 3. 에러코드 체계 (6개 API 공통)

| 타입 | 코드 | 설명 |
|---|---|---|
| 정보 | 100 | 인증키가 유효하지 않음 |
| 정보 | 200 | 해당하는 데이터가 없음 |
| 에러 | 100 | 필수 값 누락 |
| 에러 | 101 | 주기와 다른 형식의 날짜 형식 |
| 에러 | 200 | 파일타입 값 누락/유효하지 않음 |
| 에러 | 300 | 조회건수 값 누락 |
| 에러 | 301 | 조회건수 값 타입이 유효하지 않음(정수 아님) |
| 에러 | 400 | 검색범위 초과로 60초 TIMEOUT |
| 에러 | 500 | 서버 오류 |
| 에러 | 600 | DB Connection 오류 |
| 에러 | 601 | SQL 오류 |
| 에러 | 602 | 과도한 호출로 이용 제한 |

서울시 API와 코드 체계가 유사(INFO-100/200, ERROR-1xx/2xx/3xx/4xx/5xx/6xx)하나
**한국은행은 "정보"/"에러"라는 한글 타입 필드로 구분**되는 점이 다름. 응답 JSON/XML 최상위에
`RESULT` 객체(code, message)로 오는지, 아니면 개별 서비스 루트 엘리먼트 안에 있는지는
StatisticSearch 등 실제 호출 결과로 실측 확인 필요.

---

## 4. 실측 필요 항목 (★ Claude Code가 반드시 조합별로 검증)

1. **StatisticSearch의 통계항목코드1~4 (선택 파라미터) 생략 방식**
   - 샘플 URL에 `?/?/?`로 표기된 것이 실제 호출 시에도 물음표 문자를 그대로 보내는 규칙인지,
     아니면 세그먼트 자체를 완전히 잘라내야 하는지 확인 필요.
   - 과거 서울시 개별공시지가 API 사례처럼 "선택 파라미터 부분 채움 금지" 제약이 있을 가능성.
     예: 통계항목코드1만 채우고 2~4를 비우는 조합, 전부 채우는 조합, 전부 생략(세그먼트 자체 제거)
     조합을 각각 테스트.

2. **StatisticTableList의 통계표코드(선택) 생략 시 URL 구조**
   - 마지막 세그먼트를 통째로 제거하는지, 빈 문자열 세그먼트(`//`)를 남기는지 확인.

3. **한글 경로 세그먼트 URL 인코딩** (StatisticMeta의 데이터명, StatisticWord의 용어)
   - httpx가 자동으로 UTF-8 URL 인코딩하는지, `urllib.parse.quote`를 명시적으로 적용해야
     정상 응답이 오는지 확인.

4. **요청시작건수/요청종료건수의 실제 페이징 동작**
   - "1~10건 요청" 시 정말 최대 10건까지 오는지, 아니면 특정 서비스(예: KeyStatisticList)는
     최신 데이터만 반환하는지 실측.

5. **JSON 응답 시 최상위 구조**
   - `{"StatisticSearch": {"list_total_count": N, "row": [...]}}` 형태로 오는지,
     에러 시 `{"RESULT": {"CODE": "...", "MESSAGE": "..."}}` 형태로 오는지 실제 호출로 확인
     후 파싱 로직에 반영.

각 항목은 발견 즉시 DEVLOG.md에 기록하고, 필요 시 코드에 사전 검증 로직을 추가한다
(CLAUDE.md 2-6절 절차 준수).

---

## 5. MCP 툴 설계 (6개 — 명세서 서비스 1:1 매핑)

| 툴 이름 | 대응 API | 설명 |
|---|---|---|
| `search_statistic_tables` | StatisticTableList | 통계표 목록 검색/조회 |
| `get_statistic_data` | StatisticSearch | ★ 실제 시계열 수치 데이터 조회 |
| `get_statistic_items` | StatisticItemList | 통계표의 항목코드 목록 조회 |
| `get_key_statistics` | KeyStatisticList | 100대 주요 통계지표 조회 |
| `get_statistic_meta` | StatisticMeta | 통계 메타데이터(작성기준 등) 조회 |
| `search_statistic_word` | StatisticWord | 경제/통계 용어 설명 조회 |

각 툴의 docstring에는 반드시:
- 파라미터별 형식 제약 (예: 검색시작일자는 주기에 따라 형식이 다름을 명시)
- 출력 필드의 단위(UNIT_NAME 등)가 응답에 포함된다는 점
- 선택 파라미터 생략 시 주의사항 (실측 결과 반영, 미확정 시 "확인 필요"로 명시)

---

## 6. 기술 스택

- Python 3.11+, `fastmcp`, `httpx`, `python-dotenv`
- 배포: Fly.io (Dockerfile + fly.toml), `stateless_http=True` 필수
- 인증키 없이 공개 배포 → **2-7절 rate limit 미들웨어 필수 적용**

---

## 7. 디렉토리 구조

```
korea-bok-stats-mcp/
├── requirements.txt
├── bok_api.py        # API 호출 + 에러코드 매핑 + rate limit용 헬퍼
├── server.py          # MCP 툴 6종 정의, stateless_http=True, rate limit 미들웨어
├── .env.example        # BOK_API_KEY=
├── .gitignore
├── Dockerfile
├── fly.toml
├── DEVPLAN.md / CLAUDE.md / README.md / DEVLOG.md
```

---

## 8. 진행 순서

CLAUDE.md 2-4절 "작업 순서"를 그대로 따른다 (요약):
1. requirements.txt
2. bok_api.py (API 호출 + 에러코드 매핑, URL path 세그먼트 조립 로직 — 선택파라미터 실측 전까지는
   "전부 채우거나 전부 생략" 가정으로 1차 구현 후 실측으로 검증/수정)
3. server.py (6개 툴 + stateless_http=True + rate limit 미들웨어)
4. .env.example, .gitignore
5. 로컬 실측 테스트 (6개 API 전부, 특히 StatisticSearch 선택파라미터 조합별)
6. FastMCP 스모크 테스트
7. Dockerfile, fly.toml
8. README/DEVLOG 갱신 (실측 기준으로 정확히 기술)
9. git add/commit/push
10. 정지 → 사용자에게 배포 안내

---

## 9. 사용자가 먼저 할 일

1. 한국은행 ECOS(https://ecos.bok.or.kr) 회원가입 → OPEN API 인증키 신청 (보통 1일 이내 승인)
2. 발급받은 키를 `C:\Users\hwang\Scripts\api-keys.env.example`에 `BOK_API_KEY=<키>` 형식으로
   본인만 보는 곳에 기록 (6-1절 API 키 관리 원칙 참고)
3. 이 문서 포함 4종 문서를 `mcp-docs` 폴더에 저장 후 부트스트랩 스크립트 실행
   (자세한 절차는 채팅에서 안내한 순서 그대로 진행)
