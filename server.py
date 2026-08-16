"""한국은행 ECOS Open API MCP 서버."""

import os
import time
from collections import defaultdict

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from starlette.requests import Request
from starlette.responses import JSONResponse

from bok_api import call_ecos_api, BokApiError

load_dotenv()

mcp = FastMCP("korea-bok-stats-mcp")

# ---------------------------------------------------------------------------
# CLAUDE.md 5절 — IP 기반 rate limit (in-memory)
# ---------------------------------------------------------------------------

MINUTE_LIMIT = 3
MINUTE_WINDOW = 60
VIOLATION_LIMIT = 5
VIOLATION_WINDOW = 3600
BLOCK_DURATION = 24 * 3600
DAILY_LIMIT = 30
DAILY_WINDOW = 24 * 3600

_call_log: dict[str, list[float]] = defaultdict(list)
_violation_log: dict[str, list[float]] = defaultdict(list)
_blocked_until: dict[str, float] = {}


def _prune(timestamps: list[float], window: float, now: float) -> list[float]:
    return [t for t in timestamps if now - t < window]


def check_rate_limit(ip: str) -> tuple[bool, str]:
    """호출 허용 여부를 (허용여부, 메시지) 형태로 반환한다."""
    now = time.time()

    blocked_at = _blocked_until.get(ip)
    if blocked_at is not None:
        if now < blocked_at:
            return False, "Rate limit exceeded. Try again later. (temporarily blocked)"
        del _blocked_until[ip]
        _violation_log[ip] = []

    calls = _prune(_call_log[ip], DAILY_WINDOW, now)
    _call_log[ip] = calls

    minute_calls = [t for t in calls if now - t < MINUTE_WINDOW]
    if len(minute_calls) >= MINUTE_LIMIT:
        _violation_log[ip] = _prune(_violation_log[ip], VIOLATION_WINDOW, now)
        _violation_log[ip].append(now)
        if len(_violation_log[ip]) >= VIOLATION_LIMIT:
            _blocked_until[ip] = now + BLOCK_DURATION
        return False, "Rate limit exceeded. Try again later. (per-minute limit)"

    if len(calls) >= DAILY_LIMIT:
        return False, "Rate limit exceeded. Try again later. (daily limit)"

    _call_log[ip].append(now)
    return True, ""


def _extract_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        request: Request | None = None
        try:
            request = context.fastmcp_context.get_http_request()
        except Exception:
            request = None

        ip = _extract_ip(request) if request is not None else "unknown"
        allowed, message = check_rate_limit(ip)
        if not allowed:
            raise RuntimeError(message)

        return await call_next(context)


mcp.add_middleware(RateLimitMiddleware())


# ---------------------------------------------------------------------------
# MCP 툴 6종 (DEVPLAN.md 5절)
# ---------------------------------------------------------------------------


@mcp.tool()
async def search_statistic_tables(
    start: int = 1,
    end: int = 100,
    stat_code: str | None = None,
) -> dict:
    """한국은행 ECOS 통계표 목록을 검색/조회한다 (StatisticTableList API).

    통계표 계층 구조(대분류 -> 세부 통계표)를 조회할 수 있다. stat_code를 지정하면
    해당 통계표코드 하나만 조회한다. 다른 툴(get_statistic_data 등)에 넣을
    통계표코드(STAT_CODE)를 찾을 때 사용한다.

    Args:
        start: 요청시작건수 (1부터 시작)
        end: 요청종료건수
        stat_code: 특정 통계표코드로 좁혀서 조회 (예: "102Y004"). 생략 시 전체 목록.

    Returns:
        list_total_count: 전체 건수
        row: 각 항목에 P_STAT_CODE(상위통계표코드), STAT_CODE(통계표코드),
             STAT_NAME(통계명), CYCLE(주기: 년/분기/월 등), SRCH_YN(검색가능여부),
             ORG_NAME(출처) 포함
    """
    try:
        return await call_ecos_api("StatisticTableList", [start, end, stat_code])
    except BokApiError as e:
        return {"error": str(e)}


@mcp.tool()
async def get_statistic_data(
    stat_code: str,
    cycle: str,
    start_date: str,
    end_date: str,
    start: int = 1,
    end: int = 100,
    item_code1: str | None = None,
    item_code2: str | None = None,
    item_code3: str | None = None,
    item_code4: str | None = None,
) -> dict:
    """한국은행 ECOS 실제 시계열 통계 수치 데이터를 조회한다 (StatisticSearch API). ★ 핵심 툴

    통계표코드(STAT_CODE)는 search_statistic_tables로, 통계항목코드(item_code1~4)는
    get_statistic_items로 먼저 확인해야 한다.

    Args:
        stat_code: 통계표코드 (예: "722Y001")
        cycle: 주기 — A(년), S(반년), Q(분기), M(월), SM(반월), D(일)
        start_date: 검색시작일자. 주기에 따라 형식이 다르다:
            A -> "2015", S -> "2015S1", Q -> "2015Q1",
            M -> "201501", SM -> "201501S1", D -> "20150101"
        end_date: 검색종료일자 (형식은 start_date와 동일 규칙)
        start: 요청시작건수
        end: 요청종료건수
        item_code1~4: 통계항목코드 (선택, 계층순으로 채운다). 실측 결과 item_code1만
            채우고 2~4를 생략해도 정상 동작하며, 세그먼트를 완전히 생략하는 방식과
            "?"를 리터럴로 채우는 방식 모두 동일하게 동작함을 확인함 (2026-08-17 실측).

    Returns:
        list_total_count: 전체 건수
        row: 각 항목에 STAT_CODE, STAT_NAME, ITEM_CODE1~4, ITEM_NAME1~4,
             UNIT_NAME(단위 — 예: 십억원, %), WGT(가중치), TIME(시점),
             DATA_VALUE(실제 수치값, 문자열) 포함
    """
    try:
        return await call_ecos_api(
            "StatisticSearch",
            [start, end, stat_code, cycle, start_date, end_date,
             item_code1, item_code2, item_code3, item_code4],
        )
    except BokApiError as e:
        return {"error": str(e)}


@mcp.tool()
async def get_statistic_items(
    stat_code: str,
    start: int = 1,
    end: int = 100,
) -> dict:
    """특정 통계표의 세부 항목코드 체계를 조회한다 (StatisticItemList API).

    get_statistic_data에 넣을 item_code1~4 값을 찾는 데 사용한다.

    Args:
        stat_code: 통계표코드 (예: "601Y002")
        start: 요청시작건수
        end: 요청종료건수

    Returns:
        list_total_count: 전체 건수
        row: 각 항목에 STAT_CODE, STAT_NAME, GRP_CODE/GRP_NAME(항목그룹),
             ITEM_CODE(통계항목코드), ITEM_NAME(통계항목명),
             P_ITEM_CODE/P_ITEM_NAME(상위항목), CYCLE(주기),
             START_TIME/END_TIME(수록기간), DATA_CNT(자료수),
             UNIT_NAME(단위), WEIGHT(가중치) 포함
    """
    try:
        return await call_ecos_api("StatisticItemList", [start, end, stat_code])
    except BokApiError as e:
        return {"error": str(e)}


@mcp.tool()
async def get_key_statistics(
    start: int = 1,
    end: int = 100,
) -> dict:
    """한국은행 100대 주요 통계지표를 조회한다 (KeyStatisticList API).

    통계표코드 없이 바로 조회 가능한 요약 지표 목록이다.

    Args:
        start: 요청시작건수
        end: 요청종료건수

    Returns:
        list_total_count: 전체 건수
        row: 각 항목에 CLASS_NAME(통계그룹명), KEYSTAT_NAME(통계명),
             DATA_VALUE(값), CYCLE(최근 수록시점 — 필드명은 CYCLE이지만 실제로는
             시점값), UNIT_NAME(단위) 포함
    """
    try:
        return await call_ecos_api("KeyStatisticList", [start, end])
    except BokApiError as e:
        return {"error": str(e)}


@mcp.tool()
async def get_statistic_meta(
    data_name: str,
    start: int = 1,
    end: int = 100,
) -> dict:
    """특정 통계 데이터명에 대한 메타데이터(작성기준, 연혁 등)를 조회한다 (StatisticMeta API).

    명세서 기준 15개 통계에 대해서만 메타데이터가 제공된다. 지원하지 않는 데이터명을
    조회하면 INFO-200(데이터 없음)이 반환된다.

    Args:
        data_name: 데이터명 (예: "경제심리지수"). 한글 그대로 전달하면 된다 —
            httpx가 UTF-8 URL 인코딩을 자동 처리함을 실측으로 확인함 (2026-08-17).
        start: 요청시작건수
        end: 요청종료건수

    Returns:
        list_total_count: 전체 건수
        row: 각 항목에 LVL(레벨), P_CONT_CODE(상위통계항목코드), CONT_CODE(통계항목코드),
             CONT_NAME(통계항목명), META_DATA(메타데이터 내용) 포함
    """
    try:
        return await call_ecos_api("StatisticMeta", [start, end, data_name])
    except BokApiError as e:
        return {"error": str(e)}


@mcp.tool()
async def search_statistic_word(
    word: str,
    start: int = 1,
    end: int = 100,
) -> dict:
    """경제/통계 용어를 검색하여 설명을 조회한다 (StatisticWord API, 총 803개 용어).

    Args:
        word: 조회할 용어 (예: "소비자동향지수"). 한글 그대로 전달하면 된다 —
            httpx가 UTF-8 URL 인코딩을 자동 처리함을 실측으로 확인함 (2026-08-17).
        start: 요청시작건수
        end: 요청종료건수

    Returns:
        list_total_count: 전체 건수
        row: 각 항목에 WORD(용어), CONTENT(용어설명) 포함
    """
    try:
        return await call_ecos_api("StatisticWord", [start, end, word])
    except BokApiError as e:
        return {"error": str(e)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, stateless_http=True)
