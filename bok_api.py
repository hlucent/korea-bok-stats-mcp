"""한국은행 ECOS Open API 호출 헬퍼."""

import os
import httpx

BASE_URL = "https://ecos.bok.or.kr/api"

# CLAUDE.md 3절 에러코드 체계
ERROR_MESSAGES = {
    "INFO-100": "인증키가 유효하지 않습니다.",
    "INFO-200": "해당하는 데이터가 없습니다.",
    "ERROR-100": "필수 값이 누락되었습니다.",
    "ERROR-101": "주기와 다른 형식의 날짜 형식입니다.",
    "ERROR-200": "파일타입 값이 누락되었거나 유효하지 않습니다.",
    "ERROR-300": "조회건수 값이 누락되었습니다.",
    "ERROR-301": "조회건수 값의 타입이 유효하지 않습니다(정수 아님).",
    "ERROR-400": "검색범위 초과로 60초 TIMEOUT 되었습니다.",
    "ERROR-500": "서버 오류가 발생했습니다.",
    "ERROR-600": "DB Connection 오류가 발생했습니다.",
    "ERROR-601": "SQL 오류가 발생했습니다.",
    "ERROR-602": "과도한 호출로 이용이 제한되었습니다.",
}


class BokApiError(Exception):
    """ECOS API가 RESULT 객체로 에러를 반환한 경우."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        friendly = ERROR_MESSAGES.get(code, message)
        super().__init__(f"[{code}] {friendly}")


async def call_ecos_api(service: str, segments: list) -> dict:
    """ECOS API 저수준 호출 함수.

    service: 서비스명 (예: StatisticSearch)
    segments: 인증키/요청유형/언어구분 이후에 오는 경로 세그먼트 리스트
              (요청시작건수, 요청종료건수, 서비스별 파라미터 등). None 값은 세그먼트에서 제외한다.

    요청유형은 json, 언어구분은 kr로 고정한다.
    반환값은 최상위 서비스명 키 아래의 dict (예: {"list_total_count": N, "row": [...]})
    에러 시 BokApiError를 발생시킨다.
    """
    api_key = os.environ["BOK_API_KEY"]
    parts = [BASE_URL, service, api_key, "json", "kr"]
    parts.extend(str(s) for s in segments if s is not None)
    url = "/".join(parts)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30)
        response.raise_for_status()

    data = response.json()

    if "RESULT" in data:
        result = data["RESULT"]
        code = result.get("CODE", "")
        message = result.get("MESSAGE", "")
        if code == "INFO-200":
            return {"list_total_count": 0, "row": []}
        raise BokApiError(code, message)

    if service in data:
        return data[service]

    raise BokApiError("UNKNOWN", f"예상치 못한 응답 구조: {list(data.keys())}")
