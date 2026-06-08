from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup

try:
    import FinanceDataReader as fdr
except ImportError:
    fdr = None


DEFAULT_TICKERS = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "035420": "NAVER",
    "035720": "카카오",
    "051910": "LG화학",
    "005380": "현대차",
    "068270": "셀트리온",
    "012450": "한화에어로스페이스",
    "042660": "한화오션",
    "055550": "신한지주",
    "105560": "KB금융",
    "207940": "삼성바이오로직스",
    "373220": "LG에너지솔루션",
    "247540": "에코프로비엠",
    "086520": "에코프로",
    "016880": "웅진",
    "095720": "웅진씽크빅",
    "103130": "웅진에너지",
    "000150": "두산",
    "241560": "두산밥캣",
    "034020": "두산에너빌리티",
    "336260": "두산퓨얼셀",
    "042670": "HD현대인프라코어",
    "034950": "한국기업평가",
    "214680": "디알텍",
    "060570": "드림어스컴퍼니",
    "192650": "드림텍",
    "348950": "제이알글로벌리츠",
    "028260": "삼성물산",
    "006400": "삼성SDI",
    "018260": "삼성에스디에스",
    "032830": "삼성생명",
    "000810": "삼성화재",
    "029780": "삼성카드",
    "016360": "삼성증권",
    "010140": "삼성중공업",
    "028050": "삼성E&A",
    "003550": "LG",
    "066570": "LG전자",
    "034220": "LG디스플레이",
    "096770": "SK이노베이션",
    "034730": "SK",
    "017670": "SK텔레콤",
    "033780": "KT&G",
    "003670": "포스코퓨처엠",
    "005490": "POSCO홀딩스",
    "086790": "하나금융지주",
    "316140": "우리금융지주",
    "323410": "카카오뱅크",
    "377300": "카카오페이",
    "352820": "하이브",
    "259960": "크래프톤",
    "251270": "넷마블",
    "036570": "엔씨소프트",
    "009150": "삼성전기",
    "000270": "기아",
    "012330": "현대모비스",
    "010130": "고려아연",
    "011200": "HMM",
    "010950": "S-Oil",
    "090430": "아모레퍼시픽",
    "128940": "한미약품",
    "196170": "알테오젠",
    "091990": "셀트리온헬스케어",
    "293490": "카카오게임즈",
    "041510": "에스엠",
    "035900": "JYP Ent.",
}

DEFAULT_STOCK_MARKETS = {
    "247540": ".KQ",
    "086520": ".KQ",
    "352820": ".KS",
    "259960": ".KS",
    "251270": ".KS",
    "036570": ".KS",
    "196170": ".KQ",
    "091990": ".KQ",
    "293490": ".KQ",
    "041510": ".KQ",
    "035900": ".KQ",
    "060570": ".KQ",
    "192650": ".KS",
}

STOCK_ALIASES = {
    "삼전": "삼성전자",
    "하닉": "SK하이닉스",
    "슼하이닉스": "SK하이닉스",
    "네이버": "NAVER",
    "카뱅": "카카오뱅크",
    "카카오페이": "카카오페이",
    "엘지화학": "LG화학",
    "엘지전자": "LG전자",
    "엘지엔솔": "LG에너지솔루션",
    "포홀": "POSCO홀딩스",
    "포스코홀딩스": "POSCO홀딩스",
    "한에": "한화에어로스페이스",
    "에코비": "에코프로비엠",
}

DEFAULT_COINS = {
    "KRW-BTC": "비트코인",
    "KRW-ETH": "이더리움",
    "KRW-XRP": "리플",
    "KRW-SOL": "솔라나",
    "KRW-DOGE": "도지코인",
    "KRW-ADA": "에이다",
    "KRW-LINK": "체인링크",
    "KRW-DOT": "폴카닷",
    "KRW-AVAX": "아발란체",
    "KRW-SUI": "수이",
}

DEFAULT_SCAN_KEYWORDS = {
    "주식": "삼성 두산 웅진 드림 카카오 네이버 현대 LG SK 셀트리온 한화 에코 포스코 금융 바이오 반도체 조선 방산 게임",
    "코인": "BTC ETH XRP SOL DOGE ADA LINK DOT AVAX SUI",
}

COIN_KEYWORDS = {
    "KRW-BTC": ["비트코인", "BTC", "Bitcoin"],
    "KRW-ETH": ["이더리움", "ETH", "Ethereum"],
    "KRW-XRP": ["리플", "XRP", "Ripple"],
    "KRW-SOL": ["솔라나", "SOL", "Solana"],
    "KRW-DOGE": ["도지", "도지코인", "DOGE", "Dogecoin"],
    "KRW-ADA": ["에이다", "ADA", "Cardano"],
}

UPBIT_PERIODS = {
    "1mo": 30,
    "3mo": 90,
    "6mo": 180,
    "1y": 365,
}

HISTORY_FILE = Path(__file__).with_name("view_history.json")
MAX_HISTORY = 30

HELP_TEXT = {
    "asset_type": "분석할 대상을 주식 또는 코인으로 전환합니다.",
    "stock_search": "회사 이름 일부나 6자리 종목 코드를 입력하면 KRX 종목을 검색합니다.",
    "period": "지표 계산에 사용할 과거 데이터 기간입니다. 단기 매매는 보통 6개월~1년을 먼저 봅니다.",
    "community": "게시글과 뉴스 제목의 긍정/부정 키워드를 집계한 참고 지표입니다. 매매 판단에 직접 사용하기보다는 분위기 확인용입니다.",
    "account_size": "이 앱에서 포지션 크기 계산에 사용할 총 운용 자금입니다.",
    "risk_pct": "한 번의 매매에서 잃어도 되는 최대 손실 비율입니다. 예: 1%면 100만원 기준 최대 손실 1만원.",
    "max_allocation": "한 종목이나 한 코인에 최대 몇 퍼센트까지 투입할지 제한합니다.",
    "atr_multiplier": "ATR은 최근 평균 변동폭입니다. 배수가 클수록 손절선은 멀어지고 수량은 줄어듭니다.",
    "auto_signal": "추세, 이동평균 교차, MACD, RSI, 거래량을 점수화한 참고 신호입니다.",
    "rsi": "RSI는 최근 상승/하락 강도를 나타냅니다. 보통 70 이상은 과열, 30 이하는 과매도로 봅니다.",
    "return_20d": "현재 가격이 20거래일 전보다 얼마나 올랐거나 내렸는지 보여줍니다.",
    "macd": "MACD는 단기/장기 이동평균 차이를 이용한 모멘텀 지표입니다. 시그널선 상향 돌파는 상승 모멘텀으로 봅니다.",
    "risk_grade": "변동성, 낙폭, 신호 강도, 뉴스/커뮤니티 분위기를 종합한 위험 등급입니다.",
    "stop_price": "ATR 기준으로 계산한 참고 손절가입니다. 이 가격을 깨면 손실 제한을 우선 고려합니다.",
    "position_value": "운용 자금, 허용 손실, 손절폭, 최대 투입 비중을 반영한 진입 가능 금액입니다.",
    "expected_loss": "기준 손절가에서 정리한다고 가정했을 때의 예상 손실 금액입니다.",
    "volatility": "최근 20일 일간 수익률의 표준편차입니다. 높을수록 가격 흔들림이 큽니다.",
    "drawdown": "최근 60일 고점 대비 현재 가격이 얼마나 내려와 있는지 나타냅니다.",
    "profit_grade": "목표가, 손익비, 모멘텀, 고점 여지, 분위기를 종합한 수익성 등급입니다.",
    "target_price": "ATR과 최근 고점을 기준으로 계산한 참고 목표가입니다.",
    "reward_risk": "목표 수익폭을 손절폭으로 나눈 값입니다. 2.0이면 손실 1 대비 기대 수익 2라는 뜻입니다.",
    "upside": "최근 20일 또는 60일 고점까지 남은 상승 여지입니다.",
    "momentum_5d": "최근 5거래일 수익률입니다. 단기 힘이 있는지 확인합니다.",
}


def configured_password() -> str:
    env_password = os.getenv("APP_PASSWORD", "").strip()
    if env_password:
        return env_password
    try:
        return str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        return ""


def require_password() -> None:
    password = configured_password()
    if not password:
        return

    if st.session_state.get("authenticated"):
        return

    st.title("비공개 투자 분석 앱")
    entered = st.text_input("비밀번호", type="password", help="관리자가 설정한 앱 접속 비밀번호를 입력하세요.")
    if st.button("접속", type="primary"):
        if entered == password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("비밀번호가 맞지 않습니다.")
    st.stop()

CANDIDATE_COLUMN_HELP = {
    "수익성점수": "기술적 점수에 60일 고점 여지, 거래량, 과열/변동성 감점을 더한 후보 정렬용 점수입니다.",
    "점수": "자동 신호 점수입니다. 이동평균, MACD, RSI, 거래량 조건을 합산합니다. 높을수록 기술적 신호가 강합니다.",
    "신호": "점수를 사람이 읽기 쉽게 바꾼 상태입니다. 매수 관심이어도 바로 매수 뜻은 아닙니다.",
    "1일 변화율": "전일 종가 대비 오늘 종가 변화율입니다.",
    "5일 수익률": "최근 5거래일 가격 변화율입니다. 단기 모멘텀을 봅니다.",
    "20일 수익률": "최근 20거래일 가격 변화율입니다. 너무 높으면 과열일 수 있습니다.",
    "RSI14": "14일 RSI입니다. 보통 70 이상은 과열, 30 이하는 과매도로 봅니다.",
    "거래량배수": "현재 거래량이 20일 평균 거래량의 몇 배인지 나타냅니다. 1.5x 이상이면 관심도가 커진 상태일 수 있습니다.",
    "변동성20D": "최근 20일 일간 수익률의 표준편차입니다. 높을수록 가격 흔들림이 큽니다.",
    "60일낙폭": "최근 60일 고점 대비 현재 가격의 하락률입니다. 음수가 클수록 고점에서 많이 내려온 상태입니다.",
    "60일고점여지": "최근 60일 고점까지 남은 상승 여지입니다.",
    "위험메모": "후보를 볼 때 먼저 조심해야 할 포인트를 요약합니다.",
}

POSITIVE_WORDS = [
    "호재",
    "상승",
    "급등",
    "매수",
    "실적",
    "수주",
    "돌파",
    "반등",
    "저평가",
    "배당",
    "신고가",
    "흑자",
    "성장",
    "개선",
]

NEGATIVE_WORDS = [
    "악재",
    "하락",
    "급락",
    "매도",
    "손절",
    "적자",
    "유증",
    "상폐",
    "폭락",
    "고점",
    "물렸다",
    "리스크",
    "하한가",
    "부진",
    "청산",
    "공포",
    "규제",
    "해킹",
    "폐지",
]


@dataclass(frozen=True)
class SignalResult:
    action: str
    score: int
    summary: str
    reasons: list[str]


@dataclass(frozen=True)
class CommunityResult:
    source: str
    mood: str
    score: int
    positive_hits: int
    negative_hits: int
    status: str
    posts: pd.DataFrame


@dataclass(frozen=True)
class RiskPlan:
    grade: str
    risk_score: int
    stop_price: float
    stop_loss_pct: float
    risk_budget: float
    position_qty: float
    position_value: float
    expected_loss: float
    volatility_20d: float
    drawdown_60d: float
    distance_ma20: float
    notes: list[str]


@dataclass(frozen=True)
class ProfitPlan:
    grade: str
    profit_score: int
    target_price_1: float
    target_price_2: float
    target_return_1: float
    target_return_2: float
    reward_risk_1: float
    reward_risk_2: float
    upside_to_20d_high: float
    upside_to_60d_high: float
    momentum_5d: float
    notes: list[str]


def normalize_krx_ticker(raw: str, market_suffix: str) -> str:
    ticker = raw.strip().upper()
    if ticker.endswith((".KS", ".KQ")):
        return ticker
    digits = "".join(ch for ch in ticker if ch.isdigit())
    if len(digits) == 6:
        return f"{digits}{market_suffix}"
    return ticker


def krx_code(raw: str) -> str:
    ticker = raw.strip().upper().replace(".KS", "").replace(".KQ", "")
    digits = "".join(ch for ch in ticker if ch.isdigit())
    return digits[:6]


def coin_keywords(market: str) -> list[str]:
    normalized = market.strip().upper()
    if normalized in COIN_KEYWORDS:
        return COIN_KEYWORDS[normalized]
    symbol = normalized.replace("KRW-", "").replace("USDT-", "").replace("BTC-", "")
    return [symbol] if symbol else [normalized]


def coin_query(market: str) -> str:
    return coin_keywords(market)[0]


def asset_display_name(asset_type: str, raw_ticker: str) -> str:
    if asset_type == "주식":
        code = krx_code(raw_ticker)
        return f"종목 ({code})" if code else raw_ticker.strip().upper()

    market = raw_ticker.strip().upper()
    name = DEFAULT_COINS.get(market, "직접 입력 코인")
    return f"{name} ({market})" if market else "코인"


def app_title(asset_type: str, raw_ticker: str) -> str:
    return f"{asset_display_name(asset_type, raw_ticker)} 분석 및 자동 매매 신호"


def app_title_from_name(asset_type: str, raw_ticker: str, display_name: str = "") -> str:
    if display_name:
        code = krx_code(raw_ticker) if asset_type == "주식" else raw_ticker.strip().upper()
        return f"{display_name} ({code}) 분석 및 자동 매매 신호"
    return app_title(asset_type, raw_ticker)


def normalize_search_text(value: str) -> str:
    text = str(value).lower()
    text = text.replace("&", "앤")
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[\s\-_.,/·]", "", text)
    text = text.replace("주식회사", "").replace("(주)", "").replace("㈜", "")
    return text


def market_name_from_suffix(suffix: str) -> str:
    return "KOSDAQ" if suffix == ".KQ" else "KOSPI"


@st.cache_data(ttl=86400, show_spinner=False)
def load_krx_listing() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    errors: list[str] = []

    if fdr is None:
        errors.append("FinanceDataReader 미설치")
    else:
        try:
            listing = fdr.StockListing("KRX")
            expected_columns = {"Code", "Name", "Market"}
            if expected_columns.issubset(set(listing.columns)):
                listing = listing[["Code", "Name", "Market"]].dropna(subset=["Code", "Name"])
                frames.append(listing)
            else:
                errors.append("FinanceDataReader 컬럼 형식 불일치")
        except Exception:
            errors.append("FinanceDataReader 조회 실패")

    if not frames:
        empty = pd.DataFrame(columns=["Code", "Name", "Market"])
        empty.attrs["errors"] = errors
        return empty

    frame = pd.concat(frames, ignore_index=True)
    frame = frame[["Code", "Name", "Market"]].dropna(subset=["Code", "Name"])
    frame["Code"] = frame["Code"].astype(str).str.zfill(6)
    frame["Name"] = frame["Name"].astype(str)
    frame["Market"] = frame["Market"].astype(str)
    result = frame.drop_duplicates(subset=["Code"])
    result.attrs["errors"] = errors
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_yahoo_stock_search(query: str) -> pd.DataFrame:
    text = query.strip()
    if not text:
        return pd.DataFrame(columns=["Code", "Name", "Market"])

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    try:
        response = requests.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={
                "q": text,
                "quotesCount": 50,
                "newsCount": 0,
                "lang": "ko-KR",
                "region": "KR",
            },
            headers=headers,
            timeout=8,
        )
        response.raise_for_status()
        quotes = response.json().get("quotes", [])
    except (requests.RequestException, ValueError):
        return pd.DataFrame(columns=["Code", "Name", "Market"])

    rows: list[dict[str, str]] = []
    for quote in quotes:
        symbol = str(quote.get("symbol", ""))
        if not symbol.endswith((".KS", ".KQ")):
            continue
        code = symbol.split(".")[0]
        if not re.fullmatch(r"\d{6}", code):
            continue
        rows.append(
            {
                "Code": code,
                "Name": str(quote.get("shortname") or quote.get("longname") or symbol),
                "Market": "KOSDAQ" if symbol.endswith(".KQ") else "KOSPI",
            }
        )

    if not rows:
        return pd.DataFrame(columns=["Code", "Name", "Market"])

    return pd.DataFrame(rows).drop_duplicates(subset=["Code"])[["Code", "Name", "Market"]]


def extract_stock_items_from_json(value: object) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if isinstance(value, dict):
        code = str(value.get("code") or value.get("cd") or value.get("symbol") or "")
        name = str(value.get("name") or value.get("nm") or value.get("title") or "")
        market = str(value.get("market") or value.get("marketName") or value.get("type") or "KOSPI")
        if re.fullmatch(r"\d{6}", code) and name:
            found.append({"Code": code, "Name": name, "Market": market})
        for child in value.values():
            found.extend(extract_stock_items_from_json(child))
    elif isinstance(value, list):
        text_values = [str(item) for item in value]
        code = next((item for item in text_values if re.fullmatch(r"\d{6}", item)), "")
        market = next((item for item in text_values if "KOSDAQ" in item.upper() or "KOSPI" in item.upper()), "KOSPI")
        name = ""
        for item in text_values:
            if item != code and not item.startswith("http") and not re.fullmatch(r"\d+", item):
                if normalize_search_text(item):
                    name = BeautifulSoup(item, "html.parser").get_text(" ", strip=True)
                    break
        if code and name:
            found.append({"Code": code, "Name": name, "Market": market})
        for child in value:
            found.extend(extract_stock_items_from_json(child))
    return found


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_naver_stock_search(query: str) -> pd.DataFrame:
    text = query.strip()
    if not text:
        return pd.DataFrame(columns=["Code", "Name", "Market"])

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    rows: list[dict[str, str]] = []

    try:
        response = requests.get(
            "https://ac.finance.naver.com/ac",
            params={"q": text, "q_enc": "UTF-8", "st": "111", "r_lt": "111"},
            headers=headers,
            timeout=6,
        )
        response.raise_for_status()
        rows.extend(extract_stock_items_from_json(response.json()))
    except (requests.RequestException, ValueError):
        pass

    try:
        response = requests.get(
            "https://finance.naver.com/search/searchList.naver",
            params={"query": text},
            headers=headers,
            timeout=6,
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "euc-kr"
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.select("a[href*='code=']"):
            href = link.get("href", "")
            match = re.search(r"code=(\d{6})", href)
            name = link.get_text(" ", strip=True)
            if match and name:
                surrounding = link.find_parent().get_text(" ", strip=True) if link.find_parent() else ""
                market = "KOSDAQ" if "코스닥" in surrounding or "KOSDAQ" in surrounding.upper() else "KOSPI"
                rows.append({"Code": match.group(1), "Name": name, "Market": market})
    except requests.RequestException:
        pass

    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=["Code", "Name", "Market"])
    frame["Code"] = frame["Code"].astype(str).str.zfill(6)
    frame["Name"] = frame["Name"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    frame["Market"] = frame["Market"].astype(str).fillna("KOSPI")
    return frame.drop_duplicates(subset=["Code"])[["Code", "Name", "Market"]]


def search_krx_listing(query: str, listing: pd.DataFrame, limit: int = 50) -> pd.DataFrame:
    text = query.strip()
    if not text:
        return pd.DataFrame(columns=["Code", "Name", "Market", "Label"])

    alias_text = STOCK_ALIASES.get(text, text)
    normalized_query = normalize_search_text(alias_text)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 6:
        direct = pd.DataFrame(
            [{"Code": digits, "Name": f"종목코드 {digits}", "Market": "KOSPI"}]
        )
    else:
        direct = pd.DataFrame(columns=["Code", "Name", "Market"])

    naver_matches = fetch_naver_stock_search(alias_text)
    yahoo_matches = fetch_yahoo_stock_search(alias_text)
    candidates = pd.concat([listing, naver_matches, yahoo_matches, direct], ignore_index=True).drop_duplicates(subset=["Code"])
    if candidates.empty:
        return pd.DataFrame(columns=["Code", "Name", "Market", "Label"])
    candidates["NormalizedName"] = candidates["Name"].map(normalize_search_text)
    candidates["Score"] = 0.0

    if len(digits) >= 2:
        candidates.loc[candidates["Code"].str.startswith(digits, na=False), "Score"] += 120
        candidates.loc[candidates["Code"].str.contains(digits, na=False), "Score"] += 80

    exact_mask = candidates["NormalizedName"].eq(normalized_query)
    starts_mask = candidates["NormalizedName"].str.startswith(normalized_query, na=False)
    contains_mask = candidates["NormalizedName"].str.contains(normalized_query, na=False)
    raw_contains_mask = candidates["Name"].astype(str).str.contains(alias_text, case=False, regex=False, na=False)

    candidates.loc[exact_mask, "Score"] += 150
    candidates.loc[starts_mask, "Score"] += 110
    candidates.loc[contains_mask, "Score"] += 80
    candidates.loc[raw_contains_mask, "Score"] += 80

    if normalized_query:
        candidates["Similarity"] = candidates["NormalizedName"].apply(
            lambda name: SequenceMatcher(None, normalized_query, name).ratio()
        )
        candidates["Score"] += candidates["Similarity"] * 45
    else:
        candidates["Similarity"] = 0.0

    market_bonus = candidates["Market"].astype(str).str.upper().map(
        lambda market: 5 if "KOSPI" in market else (3 if "KOSDAQ" in market else 0)
    )
    candidates["Score"] += market_bonus

    matched = candidates[candidates["Score"] >= 35].sort_values(
        ["Score", "Market", "Name"], ascending=[False, True, True]
    )
    matched = matched.head(limit).copy()
    if matched.empty:
        return pd.DataFrame(columns=["Code", "Name", "Market", "Label"])

    matched["Label"] = matched["Name"] + " (" + matched["Code"] + ", " + matched["Market"].astype(str) + ")"
    return matched[["Code", "Name", "Market", "Label"]]


def stock_search_status(listing: pd.DataFrame) -> str:
    sources = []
    sources.extend(["네이버 금융 실시간 검색", "Yahoo Finance 실시간 검색"])
    source_text = ", ".join(sources)
    if len(listing) > 0:
        source_text = f"FinanceDataReader 목록 + {source_text}"
    return f"검색 소스: {source_text}"


def stock_search_debug_status(listing: pd.DataFrame) -> str:
    errors = listing.attrs.get("errors", [])
    if not errors:
        return "추가 오류 없음"
    return ", ".join(errors)


def online_stock_universe(query_text: str, limit: int) -> pd.DataFrame:
    listing = load_krx_listing()
    frames: list[pd.DataFrame] = []
    for keyword in query_text.split():
        matches = search_krx_listing(keyword, listing, limit=limit)
        if not matches.empty:
            frames.append(matches[["Code", "Name", "Market"]])

    if not frames:
        return pd.DataFrame(columns=["Code", "Name", "Market"])

    frame = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["Code"])
    return frame.head(limit)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_upbit_markets() -> pd.DataFrame:
    response = requests.get("https://api.upbit.com/v1/market/all", params={"isDetails": "false"}, timeout=8)
    response.raise_for_status()
    frame = pd.DataFrame(response.json())
    if frame.empty:
        return pd.DataFrame(columns=["Code", "Name"])
    frame = frame[frame["market"].astype(str).str.startswith("KRW-")].copy()
    frame = frame.rename(columns={"market": "Code", "korean_name": "Name"})
    return frame[["Code", "Name"]].drop_duplicates(subset=["Code"])


def online_coin_universe(query_text: str, limit: int) -> pd.DataFrame:
    try:
        markets = fetch_upbit_markets()
    except requests.RequestException:
        markets = pd.DataFrame([{"Code": code, "Name": name} for code, name in DEFAULT_COINS.items()])

    if markets.empty:
        return pd.DataFrame(columns=["Code", "Name"])

    keywords = [normalize_search_text(keyword) for keyword in query_text.split() if keyword.strip()]
    if not keywords:
        return markets.head(limit)

    frame = markets.copy()
    frame["SearchText"] = (frame["Code"].astype(str) + " " + frame["Name"].astype(str)).map(normalize_search_text)
    mask = frame["SearchText"].apply(lambda value: any(keyword in value for keyword in keywords))
    return frame[mask][["Code", "Name"]].head(limit)


def market_suffix_from_name(market_name: str) -> str:
    market = str(market_name).upper()
    return ".KQ" if "KOSDAQ" in market else ".KS"


def load_view_history() -> list[dict[str, str]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def save_view_history(history: list[dict[str, str]]) -> None:
    try:
        with HISTORY_FILE.open("w", encoding="utf-8") as file:
            json.dump(history[:MAX_HISTORY], file, ensure_ascii=False, indent=2)
    except OSError:
        pass


def history_label(item: dict[str, str]) -> str:
    return f"{item.get('asset_type', '')} · {item.get('name', '')} ({item.get('code', '')})"


def add_view_history(asset_type: str, code: str, name: str, market_name: str) -> None:
    if not code:
        return
    history = load_view_history()
    item = {
        "asset_type": asset_type,
        "code": code,
        "name": name,
        "market": market_name,
        "viewed_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    history = [
        existing
        for existing in history
        if not (existing.get("asset_type") == asset_type and existing.get("code") == code)
    ]
    save_view_history([item] + history)


def load_price_data(ticker: str, period: str) -> pd.DataFrame:
    data = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if data.empty:
        return data

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.rename(columns=str.title)
    return data.dropna(subset=["Close"])


def load_upbit_daily_data(market: str, period: str) -> pd.DataFrame:
    count = UPBIT_PERIODS.get(period, 180)
    url = "https://api.upbit.com/v1/candles/days"
    rows: list[dict] = []
    to_time: str | None = None

    while len(rows) < count:
        batch_count = min(200, count - len(rows))
        params = {"market": market, "count": batch_count}
        if to_time:
            params["to"] = to_time

        response = requests.get(url, params=params, timeout=8)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break

        rows.extend(batch)
        oldest = pd.to_datetime(batch[-1]["candle_date_time_utc"])
        to_time = (oldest - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%S")

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    frame["Date"] = pd.to_datetime(frame["candle_date_time_kst"])
    frame = frame.sort_values("Date").set_index("Date")
    frame = frame.rename(
        columns={
            "opening_price": "Open",
            "high_price": "High",
            "low_price": "Low",
            "trade_price": "Close",
            "candle_acc_trade_volume": "Volume",
        }
    )
    return frame[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])


@st.cache_data(ttl=300, show_spinner=False)
def fetch_naver_board(code: str, pages: int = 1) -> pd.DataFrame:
    posts: list[dict[str, str]] = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }

    for page in range(1, pages + 1):
        url = f"https://finance.naver.com/item/board.naver?code={code}&page={page}"
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "euc-kr"
        soup = BeautifulSoup(response.text, "html.parser")

        for row in soup.select("table.type2 tr"):
            title_cell = row.select_one("td.title")
            link = title_cell.select_one("a") if title_cell else None
            if not link:
                continue

            title = link.get_text(" ", strip=True)
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            posts.append(
                {
                    "출처": "네이버",
                    "날짜": cells[0] if cells else "",
                    "제목": title,
                    "링크": urljoin("https://finance.naver.com", link.get("href", "")),
                }
            )

    return pd.DataFrame(posts).drop_duplicates(subset=["제목", "링크"]).head(50)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_daum_finance_news(code: str) -> pd.DataFrame:
    url = f"https://m.finance.daum.net/quotes/A{code}/news"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=8)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    posts: list[dict[str, str]] = []
    for link in soup.select("a"):
        title = link.get_text(" ", strip=True)
        href = link.get("href", "")
        if len(title) < 8:
            continue
        if "/news/" not in href and "v.daum.net" not in href:
            continue
        posts.append(
            {
                "출처": "다음",
                "날짜": "",
                "제목": title,
                "링크": urljoin("https://m.finance.daum.net", href),
            }
        )

    return pd.DataFrame(posts).drop_duplicates(subset=["제목", "링크"]).head(50)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_cointok_posts(keywords: tuple[str, ...]) -> pd.DataFrame:
    url = "https://www.cointok.co.kr/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=8)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    posts: list[dict[str, str]] = []
    lowered_keywords = [keyword.lower() for keyword in keywords]
    for link in soup.select("a"):
        title = link.get_text(" ", strip=True)
        if len(title) < 6:
            continue
        if not any(keyword in title.lower() for keyword in lowered_keywords):
            continue
        posts.append(
            {
                "출처": "코인톡",
                "날짜": "",
                "제목": title,
                "링크": urljoin(url, link.get("href", "")),
            }
        )

    return pd.DataFrame(posts).drop_duplicates(subset=["제목", "링크"]).head(50)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_naver_news_search(query: str) -> pd.DataFrame:
    url = "https://search.naver.com/search.naver"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    response = requests.get(url, params={"where": "news", "query": query}, headers=headers, timeout=8)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    posts: list[dict[str, str]] = []
    for link in soup.select("a.news_tit, a[href*='n.news.naver.com'], a[href*='news.naver.com']"):
        title = link.get("title") or link.get_text(" ", strip=True)
        href = link.get("href", "")
        if len(title) < 8:
            continue
        posts.append({"출처": "네이버뉴스", "날짜": "", "제목": title, "링크": href})

    return pd.DataFrame(posts).drop_duplicates(subset=["제목", "링크"]).head(50)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_daum_news_search(query: str) -> pd.DataFrame:
    url = "https://search.daum.net/search"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    response = requests.get(url, params={"w": "news", "q": query}, headers=headers, timeout=8)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    posts: list[dict[str, str]] = []
    for link in soup.select("a[href*='v.daum.net'], a[href*='news.v.daum.net']"):
        title = link.get_text(" ", strip=True)
        href = link.get("href", "")
        if len(title) < 8:
            continue
        posts.append({"출처": "다음뉴스", "날짜": "", "제목": title, "링크": href})

    return pd.DataFrame(posts).drop_duplicates(subset=["제목", "링크"]).head(50)


def toss_unavailable_result() -> CommunityResult:
    return CommunityResult(
        source="토스",
        mood="수집 불가",
        score=0,
        positive_hits=0,
        negative_hits=0,
        status="토스증권 커뮤니티는 앱/WTS 로그인 기반이라 공개 페이지에서 게시글을 안정적으로 가져오기 어렵습니다.",
        posts=pd.DataFrame(columns=["출처", "날짜", "제목", "링크"]),
    )


def analyze_community(source: str, posts: pd.DataFrame, status: str = "수집 완료") -> CommunityResult:
    positive_hits = 0
    negative_hits = 0

    for title in posts.get("제목", pd.Series(dtype=str)).astype(str):
        positive_hits += sum(word in title for word in POSITIVE_WORDS)
        negative_hits += sum(word in title for word in NEGATIVE_WORDS)

    score = positive_hits - negative_hits
    if score >= 5:
        mood = "낙관 우세"
    elif score >= 2:
        mood = "약한 낙관"
    elif score <= -5:
        mood = "비관 우세"
    elif score <= -2:
        mood = "약한 비관"
    else:
        mood = "중립/혼재"

    return CommunityResult(
        source=source,
        mood=mood,
        score=score,
        positive_hits=positive_hits,
        negative_hits=negative_hits,
        status=status,
        posts=posts,
    )


def community_summary_frame(results: list[CommunityResult]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "출처": result.source,
                "분위기": result.mood,
                "점수": result.score,
                "긍정 키워드": result.positive_hits,
                "부정 키워드": result.negative_hits,
                "수집 글": len(result.posts),
                "상태": result.status,
            }
            for result in results
        ]
    )


def failed_community_result(source: str, error: requests.RequestException) -> CommunityResult:
    return CommunityResult(
        source=source,
        mood="오류",
        score=0,
        positive_hits=0,
        negative_hits=0,
        status=f"수집 실패: {error}",
        posts=pd.DataFrame(columns=["출처", "날짜", "제목", "링크"]),
    )


def show_candidate_help() -> None:
    with st.expander("단기 후보 표 용어 설명", expanded=False):
        help_frame = pd.DataFrame(
            [{"항목": key, "설명": value} for key, value in CANDIDATE_COLUMN_HELP.items()]
        )
        st.dataframe(help_frame, use_container_width=True, hide_index=True)


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def add_indicators(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    close = frame["Close"]
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            frame["High"] - frame["Low"],
            (frame["High"] - previous_close).abs(),
            (frame["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    frame["MA5"] = close.rolling(5).mean()
    frame["MA20"] = close.rolling(20).mean()
    frame["MA60"] = close.rolling(60).mean()
    frame["ATR20"] = true_range.rolling(20).mean()
    frame["RSI14"] = rsi(close)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    frame["MACD"] = ema12 - ema26
    frame["MACD_SIGNAL"] = frame["MACD"].ewm(span=9, adjust=False).mean()
    frame["MACD_HIST"] = frame["MACD"] - frame["MACD_SIGNAL"]

    frame["VOL20"] = frame["Volume"].rolling(20).mean()
    frame["RETURN_20D"] = close.pct_change(20) * 100
    frame["RETURN_5D"] = close.pct_change(5) * 100
    frame["VOLATILITY_20D"] = close.pct_change().rolling(20).std() * 100
    frame["HIGH_20D"] = close.rolling(20).max()
    frame["HIGH_60D"] = close.rolling(60).max()
    frame["DRAWDOWN_60D"] = ((close / frame["HIGH_60D"]) - 1) * 100
    return frame


def crossed_above(series_a: pd.Series, series_b: pd.Series) -> bool:
    if len(series_a.dropna()) < 2 or len(series_b.dropna()) < 2:
        return False
    return series_a.iloc[-2] <= series_b.iloc[-2] and series_a.iloc[-1] > series_b.iloc[-1]


def crossed_below(series_a: pd.Series, series_b: pd.Series) -> bool:
    if len(series_a.dropna()) < 2 or len(series_b.dropna()) < 2:
        return False
    return series_a.iloc[-2] >= series_b.iloc[-2] and series_a.iloc[-1] < series_b.iloc[-1]


def make_signal(data: pd.DataFrame) -> SignalResult:
    latest = data.iloc[-1]
    score = 0
    reasons: list[str] = []

    if latest["Close"] > latest["MA20"] > latest["MA60"]:
        score += 2
        reasons.append("종가가 20일선과 60일선 위에 있어 중기 추세가 우호적입니다.")
    elif latest["Close"] < latest["MA20"] < latest["MA60"]:
        score -= 2
        reasons.append("종가가 20일선과 60일선 아래에 있어 중기 추세가 약합니다.")

    if crossed_above(data["MA5"], data["MA20"]):
        score += 2
        reasons.append("5일선이 20일선을 상향 돌파했습니다.")
    elif crossed_below(data["MA5"], data["MA20"]):
        score -= 2
        reasons.append("5일선이 20일선을 하향 이탈했습니다.")

    if crossed_above(data["MACD"], data["MACD_SIGNAL"]):
        score += 2
        reasons.append("MACD가 시그널선을 상향 돌파했습니다.")
    elif crossed_below(data["MACD"], data["MACD_SIGNAL"]):
        score -= 2
        reasons.append("MACD가 시그널선을 하향 이탈했습니다.")

    if latest["RSI14"] < 30:
        score += 1
        reasons.append("RSI가 30 아래로 과매도 구간입니다.")
    elif latest["RSI14"] > 70:
        score -= 1
        reasons.append("RSI가 70 위로 과열 구간입니다.")

    if latest["Volume"] > latest["VOL20"] * 1.5 and latest["Close"] >= latest["HIGH_20D"] * 0.995:
        score += 1
        reasons.append("거래량이 20일 평균보다 크고 20일 고점권에 있습니다.")

    if score >= 4:
        action = "강한 매수 관심"
        summary = "추세와 모멘텀이 동시에 개선되는 구간입니다."
    elif score >= 2:
        action = "매수 관심"
        summary = "일부 상승 신호가 확인됩니다."
    elif score <= -4:
        action = "강한 매도/회피"
        summary = "추세와 모멘텀이 동시에 약해지는 구간입니다."
    elif score <= -2:
        action = "매도/관망"
        summary = "하락 또는 약세 신호가 우세합니다."
    else:
        action = "중립"
        summary = "명확한 방향성이 부족합니다."

    if not reasons:
        reasons.append("주요 신호가 뚜렷하지 않아 관망 성격이 강합니다.")

    return SignalResult(action=action, score=score, summary=summary, reasons=reasons)


def make_risk_plan(
    data: pd.DataFrame,
    asset_type: str,
    signal_score: int,
    community_score: int,
    account_size: float,
    risk_pct: float,
    max_allocation_pct: float,
    atr_multiplier: float,
) -> RiskPlan:
    latest = data.iloc[-1]
    close = float(latest["Close"])
    atr = float(latest["ATR20"]) if pd.notna(latest["ATR20"]) else close * 0.03
    stop_price = max(close - (atr * atr_multiplier), 0)
    stop_loss_pct = ((stop_price / close) - 1) * 100 if close else 0
    risk_budget = account_size * (risk_pct / 100)
    max_position_value = account_size * (max_allocation_pct / 100)
    per_unit_risk = max(close - stop_price, close * 0.005)
    raw_qty = risk_budget / per_unit_risk if per_unit_risk else 0
    capped_qty = min(raw_qty, max_position_value / close if close else 0)
    position_qty = np.floor(capped_qty) if asset_type == "주식" else round(capped_qty, 6)
    position_value = position_qty * close
    expected_loss = position_qty * per_unit_risk

    volatility_20d = float(latest["VOLATILITY_20D"]) if pd.notna(latest["VOLATILITY_20D"]) else 0
    drawdown_60d = float(latest["DRAWDOWN_60D"]) if pd.notna(latest["DRAWDOWN_60D"]) else 0
    distance_ma20 = ((close / float(latest["MA20"])) - 1) * 100 if latest["MA20"] else 0

    risk_score = 0
    notes: list[str] = []
    volatility_limit = 4.0 if asset_type == "주식" else 8.0

    if volatility_20d > volatility_limit:
        risk_score += 2
        notes.append("최근 변동성이 높아 진입 금액을 줄이는 편이 안전합니다.")
    if drawdown_60d < -15:
        risk_score += 2
        notes.append("60일 고점 대비 낙폭이 커서 반등 실패 리스크가 있습니다.")
    if latest["RSI14"] > 70:
        risk_score += 1
        notes.append("RSI 과열권이라 추격 매수는 불리할 수 있습니다.")
    if distance_ma20 > 12:
        risk_score += 1
        notes.append("20일선과 가격 차이가 커서 단기 되돌림을 조심해야 합니다.")
    if signal_score < 2:
        risk_score += 2
        notes.append("기술적 신호가 충분히 강하지 않아 관망 비중을 높이는 편이 좋습니다.")
    if community_score <= -2:
        risk_score += 1
        notes.append("커뮤니티/뉴스 분위기가 부정적입니다.")
    elif community_score >= 5 and latest["RSI14"] > 65:
        risk_score += 1
        notes.append("낙관 분위기와 가격 과열이 겹쳐 과매수 가능성이 있습니다.")

    if position_value <= 0:
        risk_score += 2
        notes.append("설정한 손실 한도 기준으로 진입 가능 수량이 매우 작습니다.")

    if risk_score >= 6:
        grade = "고위험: 회피/대기"
    elif risk_score >= 3:
        grade = "주의: 소액/분할"
    else:
        grade = "관리 가능"

    if not notes:
        notes.append("현재 설정 기준에서는 손실 한도 안에서 접근 가능한 구간입니다.")

    return RiskPlan(
        grade=grade,
        risk_score=risk_score,
        stop_price=stop_price,
        stop_loss_pct=stop_loss_pct,
        risk_budget=risk_budget,
        position_qty=position_qty,
        position_value=position_value,
        expected_loss=expected_loss,
        volatility_20d=volatility_20d,
        drawdown_60d=drawdown_60d,
        distance_ma20=distance_ma20,
        notes=notes,
    )


def make_profit_plan(data: pd.DataFrame, signal_score: int, community_score: int, stop_price: float) -> ProfitPlan:
    latest = data.iloc[-1]
    close = float(latest["Close"])
    atr = float(latest["ATR20"]) if pd.notna(latest["ATR20"]) else close * 0.03
    high_20d = float(latest["HIGH_20D"]) if pd.notna(latest["HIGH_20D"]) else close
    high_60d = float(latest["HIGH_60D"]) if pd.notna(latest["HIGH_60D"]) else close
    momentum_5d = float(latest["RETURN_5D"]) if pd.notna(latest["RETURN_5D"]) else 0

    target_price_1 = max(close + atr, high_20d)
    target_price_2 = max(close + (atr * 2), high_60d)
    target_return_1 = ((target_price_1 / close) - 1) * 100 if close else 0
    target_return_2 = ((target_price_2 / close) - 1) * 100 if close else 0

    downside = max(close - stop_price, close * 0.005)
    reward_risk_1 = (target_price_1 - close) / downside if downside else 0
    reward_risk_2 = (target_price_2 - close) / downside if downside else 0
    upside_to_20d_high = ((high_20d / close) - 1) * 100 if close else 0
    upside_to_60d_high = ((high_60d / close) - 1) * 100 if close else 0

    profit_score = 0
    notes: list[str] = []

    if signal_score >= 4:
        profit_score += 3
        notes.append("기술적 신호 점수가 높아 수익 후보로 볼 근거가 있습니다.")
    elif signal_score >= 2:
        profit_score += 1
        notes.append("상승 신호가 일부 확인됩니다.")

    if reward_risk_1 >= 2:
        profit_score += 2
        notes.append("1차 목표 기준 손익비가 2 이상입니다.")
    elif reward_risk_1 >= 1.2:
        profit_score += 1
        notes.append("1차 목표 기준 손익비가 최소 기준은 충족합니다.")
    else:
        profit_score -= 2
        notes.append("1차 목표 대비 손익비가 낮아 진입 매력이 약합니다.")

    if 0 < momentum_5d < 12:
        profit_score += 1
        notes.append("최근 5일 모멘텀이 양호하지만 과도하지는 않습니다.")
    elif momentum_5d >= 12:
        profit_score -= 1
        notes.append("최근 단기 급등 폭이 커서 되돌림을 조심해야 합니다.")

    if upside_to_60d_high >= 8:
        profit_score += 1
        notes.append("60일 고점까지 남은 상승 여지가 있습니다.")
    elif upside_to_20d_high <= 1 and latest["RSI14"] > 65:
        profit_score -= 1
        notes.append("단기 고점권과 RSI 과열이 겹쳐 목표 수익 여지가 좁습니다.")

    if community_score >= 2:
        profit_score += 1
        notes.append("커뮤니티/뉴스 분위기가 수익 모멘텀에 우호적입니다.")
    elif community_score <= -2:
        profit_score -= 1
        notes.append("커뮤니티/뉴스 분위기가 부정적이라 상승 지속성을 확인해야 합니다.")

    if profit_score >= 5:
        grade = "수익성 우수"
    elif profit_score >= 2:
        grade = "수익성 보통"
    else:
        grade = "수익성 낮음"

    if not notes:
        notes.append("뚜렷한 수익성 우위가 부족해 손익비를 먼저 확인해야 합니다.")

    return ProfitPlan(
        grade=grade,
        profit_score=profit_score,
        target_price_1=target_price_1,
        target_price_2=target_price_2,
        target_return_1=target_return_1,
        target_return_2=target_return_2,
        reward_risk_1=reward_risk_1,
        reward_risk_2=reward_risk_2,
        upside_to_20d_high=upside_to_20d_high,
        upside_to_60d_high=upside_to_60d_high,
        momentum_5d=momentum_5d,
        notes=notes,
    )


def scan_candidates(
    asset_type: str,
    period: str,
    stock_suffix: str = ".KS",
    universe_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if universe_frame is None or universe_frame.empty:
        universe = pd.DataFrame(columns=["Code", "Name", "Market"])
    else:
        universe = universe_frame.copy()

    for _, item in universe.iterrows():
        code = str(item["Code"])
        name = str(item["Name"])
        market_name = str(item.get("Market", "KOSPI"))
        try:
            ticker = normalize_krx_ticker(code, market_suffix_from_name(market_name) if asset_type == "주식" else stock_suffix) if asset_type == "주식" else code
            raw_data = load_price_data(ticker, period) if asset_type == "주식" else load_upbit_daily_data(ticker, period)
            if raw_data.empty or len(raw_data) < 70:
                continue

            data = add_indicators(raw_data).dropna()
            if len(data) < 2:
                continue

            signal = make_signal(data)
            latest = data.iloc[-1]
            previous = data.iloc[-2]
            rows.append(
                {
                    "자산": asset_type,
                    "코드": code,
                    "이름": name,
                    "신호": signal.action,
                    "점수": signal.score,
                    "종가": latest["Close"],
                    "1일 변화율": ((latest["Close"] / previous["Close"]) - 1) * 100,
                    "20일 수익률": latest["RETURN_20D"],
                    "5일 수익률": latest["RETURN_5D"],
                    "RSI14": latest["RSI14"],
                    "거래량배수": latest["Volume"] / latest["VOL20"] if latest["VOL20"] else np.nan,
                    "변동성20D": latest["VOLATILITY_20D"],
                    "60일낙폭": latest["DRAWDOWN_60D"],
                    "60일고점여지": ((latest["HIGH_60D"] / latest["Close"]) - 1) * 100 if latest["Close"] else np.nan,
                    "위험메모": "과열 주의" if latest["RSI14"] > 70 else ("추세 약함" if signal.score < 2 else "확인 필요"),
                }
            )
        except (KeyError, ValueError, requests.RequestException):
            continue

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    frame["수익성점수"] = (
        frame["점수"]
        + np.where(frame["60일고점여지"] >= 8, 1, 0)
        + np.where(frame["거래량배수"] >= 1.3, 1, 0)
        - np.where(frame["RSI14"] >= 75, 2, 0)
        - np.where(frame["변동성20D"] >= 8, 1, 0)
    )
    frame = frame.sort_values(["수익성점수", "점수", "거래량배수"], ascending=[False, False, False])
    return frame.head(8)


def price_chart(data: pd.DataFrame, ticker: str, unit: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="가격",
        )
    )
    for column, color in [("MA5", "#2f80ed"), ("MA20", "#f2994a"), ("MA60", "#27ae60")]:
        fig.add_trace(go.Scatter(x=data.index, y=data[column], mode="lines", name=column, line=dict(color=color)))
    fig.update_layout(
        title=f"{ticker} 가격 및 이동평균 ({unit})",
        height=520,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def macd_chart(data: pd.DataFrame) -> go.Figure:
    colors = np.where(data["MACD_HIST"] >= 0, "#2f80ed", "#eb5757")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=data.index, y=data["MACD_HIST"], name="Histogram", marker_color=colors))
    fig.add_trace(go.Scatter(x=data.index, y=data["MACD"], mode="lines", name="MACD", line=dict(color="#111827")))
    fig.add_trace(
        go.Scatter(x=data.index, y=data["MACD_SIGNAL"], mode="lines", name="Signal", line=dict(color="#f2994a"))
    )
    fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h"))
    return fig


def rsi_chart(data: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data["RSI14"], mode="lines", name="RSI14", line=dict(color="#7b61ff")))
    fig.add_hline(y=70, line_dash="dash", line_color="#eb5757")
    fig.add_hline(y=30, line_dash="dash", line_color="#2f80ed")
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=30, b=20), showlegend=False)
    return fig


st.set_page_config(page_title="한국 주식 자동 매매 신호", page_icon="📈", layout="wide")
require_password()

title_area = st.empty()
st.caption("기술적 지표 기반의 참고용 신호입니다. 실제 매매 전에는 재무, 뉴스, 수급, 변동성, 리스크를 함께 확인하세요.")

with st.sidebar:
    st.header("분석 설정")
    asset_type = st.radio("자산", options=["주식", "코인"], horizontal=True, help=HELP_TEXT["asset_type"])
    selected_asset_name = ""
    view_history = load_view_history()
    selected_history = None
    if view_history:
        history_options = ["선택 안 함"] + [history_label(item) for item in view_history]
        history_choice = st.selectbox("최근 본 항목", history_options)
        if history_choice != "선택 안 함":
            selected_history = view_history[history_options.index(history_choice) - 1]

    if asset_type == "주식":
        listing = load_krx_listing()
        st.caption(stock_search_status(listing))
        with st.expander("검색 진단", expanded=False):
            st.write(f"전체 KRX 목록 로드 수: {len(listing):,}개")
            st.write(stock_search_debug_status(listing))
        default_stock_query = (
            selected_history["code"]
            if selected_history and selected_history.get("asset_type") == "주식"
            else "삼성전자"
        )
        stock_query = st.text_input("종목 이름 또는 코드", value=default_stock_query, help=HELP_TEXT["stock_search"])
        matches = search_krx_listing(stock_query, listing)
        if matches.empty:
            st.warning(
                "실시간 검색 결과가 없습니다. 종목명을 더 짧게 입력하거나 6자리 종목 코드를 직접 입력해 주세요."
            )
            raw_ticker = st.text_input("종목 코드 직접 입력", value="005930")
            market = st.radio("시장", options=[("KOSPI", ".KS"), ("KOSDAQ", ".KQ")], format_func=lambda item: item[0])
        else:
            result_labels = matches["Label"].head(15).tolist()
            selected_label = st.radio(
                "검색 결과 선택",
                result_labels,
                label_visibility="visible",
            )
            selected = matches[matches["Label"] == selected_label].iloc[0]
            raw_ticker = str(selected["Code"])
            selected_asset_name = str(selected["Name"])
            market = (str(selected["Market"]), market_suffix_from_name(str(selected["Market"])))
        period = st.selectbox("기간", ["6mo", "1y", "2y", "5y"], index=1, help=HELP_TEXT["period"])
        include_community = st.checkbox("커뮤니티/뉴스 분위기 비교", value=True, help=HELP_TEXT["community"])
        community_sources = st.multiselect(
            "비교 소스",
            options=["네이버", "토스", "다음"],
            default=["네이버", "토스", "다음"],
            disabled=not include_community,
        )
        board_pages = st.slider("네이버 토론실 수집 페이지", min_value=1, max_value=5, value=1, disabled=not include_community)
    else:
        preset = st.selectbox("대표 코인", ["직접 입력"] + [f"{code} · {name}" for code, name in DEFAULT_COINS.items()])
        if selected_history and selected_history.get("asset_type") == "코인":
            default_code = selected_history["code"]
        else:
            default_code = "KRW-BTC" if preset == "직접 입력" else preset.split(" · ")[0]
        raw_ticker = st.text_input("업비트 마켓", value=default_code, help="예: KRW-BTC, KRW-ETH, KRW-XRP")
        selected_asset_name = DEFAULT_COINS.get(raw_ticker.strip().upper(), raw_ticker.strip().upper())
        market = ("UPBIT", "")
        period = st.selectbox("기간", ["3mo", "6mo", "1y"], index=1, help=HELP_TEXT["period"])
        include_community = st.checkbox("코인 커뮤니티/뉴스 분위기 비교", value=True, help=HELP_TEXT["community"])
        community_sources = st.multiselect(
            "비교 소스",
            options=["코인톡", "네이버뉴스", "다음뉴스"],
            default=["코인톡", "네이버뉴스", "다음뉴스"],
            disabled=not include_community,
        )
        board_pages = 1

    st.header("리스크 관리")
    account_size = st.number_input("운용 자금", min_value=10000, value=1000000, step=100000, help=HELP_TEXT["account_size"])
    risk_pct = st.slider("1회 허용 손실", min_value=0.2, max_value=5.0, value=1.0, step=0.1, help=HELP_TEXT["risk_pct"])
    max_allocation_pct = st.slider("종목당 최대 투입", min_value=1, max_value=50, value=10, step=1, help=HELP_TEXT["max_allocation"])
    atr_multiplier = st.slider("ATR 손절 배수", min_value=1.0, max_value=4.0, value=2.0, step=0.25, help=HELP_TEXT["atr_multiplier"])

    st.header("단기 후보 스캔")
    scan_limit = st.slider("스캔 후보 수", min_value=5, max_value=50, value=20, step=5)

    run = st.button("분석 실행", type="primary", use_container_width=True)
    scan_short_term = st.button("단기 후보 스캔", use_container_width=True)

ticker = normalize_krx_ticker(raw_ticker, market[1]) if asset_type == "주식" else raw_ticker.strip().upper()
code = krx_code(raw_ticker) if asset_type == "주식" else ""
unit = "원" if asset_type in {"주식", "코인"} else ""
title_area.title(app_title_from_name(asset_type, raw_ticker, selected_asset_name))

if scan_short_term:
    st.subheader("단기 매매 후보")
    st.caption("온라인 검색으로 후보군을 만든 뒤 기술적 신호로 걸러낸 결과입니다. 추천/투자 조언이 아니라 추가 확인용 관심 목록입니다.")
    show_candidate_help()

    with st.spinner("주식과 코인 후보를 스캔하는 중입니다..."):
        stock_universe = online_stock_universe(DEFAULT_SCAN_KEYWORDS["주식"], scan_limit)
        coin_universe = online_coin_universe(DEFAULT_SCAN_KEYWORDS["코인"], scan_limit)
        stock_candidates = scan_candidates("주식", "6mo", ".KS", stock_universe)
        coin_candidates = scan_candidates("코인", "6mo", universe_frame=coin_universe)

    left, right = st.columns(2)
    with left:
        st.write(f"주식 후보 분석 결과 ({len(stock_universe)}개 검색)")
        if stock_candidates.empty:
            st.info("표시할 주식 후보가 없습니다. 검색어를 바꾸거나 후보 수를 늘려보세요.")
        else:
            st.dataframe(
                stock_candidates.style.format(
                    {
                        "종가": "{:,.0f}",
                        "1일 변화율": "{:.2f}%",
                        "5일 수익률": "{:.2f}%",
                        "20일 수익률": "{:.2f}%",
                        "RSI14": "{:.1f}",
                        "거래량배수": "{:.2f}x",
                        "변동성20D": "{:.2f}%",
                        "60일낙폭": "{:.2f}%",
                        "60일고점여지": "{:.2f}%",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with right:
        st.write(f"코인 후보 분석 결과 ({len(coin_universe)}개 검색)")
        if coin_candidates.empty:
            st.info("표시할 코인 후보가 없습니다. 검색어를 바꾸거나 후보 수를 늘려보세요.")
        else:
            st.dataframe(
                coin_candidates.style.format(
                    {
                        "종가": "{:,.0f}",
                        "1일 변화율": "{:.2f}%",
                        "5일 수익률": "{:.2f}%",
                        "20일 수익률": "{:.2f}%",
                        "RSI14": "{:.1f}",
                        "거래량배수": "{:.2f}x",
                        "변동성20D": "{:.2f}%",
                        "60일낙폭": "{:.2f}%",
                        "60일고점여지": "{:.2f}%",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.divider()

if run or raw_ticker:
    with st.spinner(f"{ticker} 데이터를 불러오는 중입니다..."):
        try:
            raw_data = load_price_data(ticker, period) if asset_type == "주식" else load_upbit_daily_data(ticker, period)
        except requests.RequestException as error:
            st.error(f"데이터를 불러오지 못했습니다: {error}")
            st.stop()

    if raw_data.empty or len(raw_data) < 70:
        st.error("데이터를 충분히 불러오지 못했습니다. 코드와 시장 구분을 확인해 주세요.")
        st.stop()

    data = add_indicators(raw_data).dropna()
    signal = make_signal(data)
    latest = data.iloc[-1]
    previous = data.iloc[-2]
    community_results: list[CommunityResult] = []
    if asset_type == "주식":
        history_code = krx_code(raw_ticker)
        history_name = selected_asset_name or asset_display_name(asset_type, raw_ticker).split(" (")[0]
        add_view_history(asset_type, history_code, history_name, market[0])
    else:
        history_code = ticker
        history_name = DEFAULT_COINS.get(ticker, asset_display_name(asset_type, raw_ticker).split(" (")[0])
        add_view_history(asset_type, history_code, history_name, "UPBIT")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("자동 신호", signal.action, f"점수 {signal.score:+d}", help=HELP_TEXT["auto_signal"])
    col2.metric("종가", f"{latest['Close']:,.0f}{unit}", f"{latest['Close'] - previous['Close']:,.0f}{unit}")
    col3.metric("RSI14", f"{latest['RSI14']:.1f}", help=HELP_TEXT["rsi"])
    col4.metric("20일 수익률", f"{latest['RETURN_20D']:.2f}%", help=HELP_TEXT["return_20d"])

    st.plotly_chart(price_chart(data, ticker, unit), use_container_width=True)

    left, right = st.columns([1, 1])
    with left:
        st.subheader("MACD", help=HELP_TEXT["macd"])
        st.plotly_chart(macd_chart(data), use_container_width=True)
    with right:
        st.subheader("RSI", help=HELP_TEXT["rsi"])
        st.plotly_chart(rsi_chart(data), use_container_width=True)

    st.subheader("신호 해석")
    st.write(signal.summary)
    for reason in signal.reasons:
        st.write(f"- {reason}")

    if include_community and asset_type == "주식":
        st.subheader("커뮤니티/뉴스 분위기 비교")
        if len(code) != 6:
            st.info("커뮤니티/뉴스 비교를 보려면 6자리 종목 코드가 필요합니다.")
        else:
            results: list[CommunityResult] = []

            if "네이버" in community_sources:
                try:
                    board = fetch_naver_board(code, pages=board_pages)
                    status = "수집 완료" if not board.empty else "수집된 글이 없습니다."
                    results.append(analyze_community("네이버", board, status=status))
                except requests.RequestException as error:
                    results.append(
                        CommunityResult(
                            source="네이버",
                            mood="오류",
                            score=0,
                            positive_hits=0,
                            negative_hits=0,
                            status=f"수집 실패: {error}",
                            posts=pd.DataFrame(columns=["출처", "날짜", "제목", "링크"]),
                        )
                    )

            if "토스" in community_sources:
                results.append(toss_unavailable_result())

            if "다음" in community_sources:
                try:
                    daum_posts = fetch_daum_finance_news(code)
                    status = "종목 뉴스 수집 완료" if not daum_posts.empty else "수집된 뉴스가 없습니다."
                    results.append(analyze_community("다음", daum_posts, status=status))
                except requests.RequestException as error:
                    results.append(
                        CommunityResult(
                            source="다음",
                            mood="오류",
                            score=0,
                            positive_hits=0,
                            negative_hits=0,
                            status=f"수집 실패: {error}",
                            posts=pd.DataFrame(columns=["출처", "날짜", "제목", "링크"]),
                        )
                    )

            if results:
                community_results = results
                summary = community_summary_frame(results)
                st.dataframe(summary, use_container_width=True, hide_index=True)
                st.caption(
                    "네이버는 종목토론실 제목, 다음은 공개 종목 뉴스 제목 기준입니다. "
                    "토스 커뮤니티는 로그인 기반이라 공개 수집 대신 상태만 표시합니다."
                )

                combined_posts = pd.concat([result.posts for result in results if not result.posts.empty], ignore_index=True)
                if not combined_posts.empty:
                    st.write("최근 수집 글")
                    st.dataframe(combined_posts[["출처", "날짜", "제목", "링크"]].head(30), use_container_width=True)
            else:
                st.info("선택된 비교 소스가 없습니다.")

    if include_community and asset_type == "코인":
        st.subheader("코인 커뮤니티/뉴스 분위기 비교")
        keywords = coin_keywords(ticker)
        query = coin_query(ticker)
        results: list[CommunityResult] = []

        if "코인톡" in community_sources:
            try:
                cointok_posts = fetch_cointok_posts(tuple(keywords))
                status = "수집 완료" if not cointok_posts.empty else "해당 코인명이 들어간 글이 없습니다."
                results.append(analyze_community("코인톡", cointok_posts, status=status))
            except requests.RequestException as error:
                results.append(failed_community_result("코인톡", error))

        if "네이버뉴스" in community_sources:
            try:
                naver_news = fetch_naver_news_search(query)
                status = "뉴스 검색 수집 완료" if not naver_news.empty else "수집된 뉴스가 없습니다."
                results.append(analyze_community("네이버뉴스", naver_news, status=status))
            except requests.RequestException as error:
                results.append(failed_community_result("네이버뉴스", error))

        if "다음뉴스" in community_sources:
            try:
                daum_news = fetch_daum_news_search(query)
                status = "뉴스 검색 수집 완료" if not daum_news.empty else "수집된 뉴스가 없습니다."
                results.append(analyze_community("다음뉴스", daum_news, status=status))
            except requests.RequestException as error:
                results.append(failed_community_result("다음뉴스", error))

        if results:
            community_results = results
            summary = community_summary_frame(results)
            st.dataframe(summary, use_container_width=True, hide_index=True)
            st.caption(
                "코인톡은 공개 페이지에서 선택 코인명이 들어간 글, 네이버뉴스/다음뉴스는 코인명 검색 결과 제목 기준입니다. "
                "커뮤니티와 뉴스는 가격보다 늦거나 과열될 수 있어 참고 지표로만 보세요."
            )

            combined_posts = pd.concat([result.posts for result in results if not result.posts.empty], ignore_index=True)
            if not combined_posts.empty:
                st.write("최근 수집 글")
                st.dataframe(combined_posts[["출처", "날짜", "제목", "링크"]].head(30), use_container_width=True)
        else:
            st.info("선택된 비교 소스가 없습니다.")

    community_score = sum(result.score for result in community_results)
    risk_plan = make_risk_plan(
        data=data,
        asset_type=asset_type,
        signal_score=signal.score,
        community_score=community_score,
        account_size=float(account_size),
        risk_pct=float(risk_pct),
        max_allocation_pct=float(max_allocation_pct),
        atr_multiplier=float(atr_multiplier),
    )
    profit_plan = make_profit_plan(
        data=data,
        signal_score=signal.score,
        community_score=community_score,
        stop_price=risk_plan.stop_price,
    )

    st.subheader("손실 최소화 계획")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("위험 등급", risk_plan.grade, f"위험점수 {risk_plan.risk_score}", help=HELP_TEXT["risk_grade"])
    r2.metric("기준 손절가", f"{risk_plan.stop_price:,.0f}{unit}", f"{risk_plan.stop_loss_pct:.2f}%", help=HELP_TEXT["stop_price"])
    r3.metric("진입 금액", f"{risk_plan.position_value:,.0f}원", help=HELP_TEXT["position_value"])
    r4.metric("예상 최대손실", f"{risk_plan.expected_loss:,.0f}원", f"한도 {risk_plan.risk_budget:,.0f}원", help=HELP_TEXT["expected_loss"])

    detail1, detail2, detail3 = st.columns(3)
    detail1.metric("계산 수량", f"{risk_plan.position_qty:,.6g}")
    detail2.metric("20일 변동성", f"{risk_plan.volatility_20d:.2f}%", help=HELP_TEXT["volatility"])
    detail3.metric("60일 고점 대비", f"{risk_plan.drawdown_60d:.2f}%", help=HELP_TEXT["drawdown"])
    for note in risk_plan.notes:
        st.write(f"- {note}")

    st.subheader("수익성 강화 지표")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("수익성 등급", profit_plan.grade, f"점수 {profit_plan.profit_score:+d}", help=HELP_TEXT["profit_grade"])
    p2.metric("1차 목표가", f"{profit_plan.target_price_1:,.0f}{unit}", f"{profit_plan.target_return_1:.2f}%", help=HELP_TEXT["target_price"])
    p3.metric("2차 목표가", f"{profit_plan.target_price_2:,.0f}{unit}", f"{profit_plan.target_return_2:.2f}%", help=HELP_TEXT["target_price"])
    p4.metric("손익비", f"{profit_plan.reward_risk_1:.2f} / {profit_plan.reward_risk_2:.2f}", help=HELP_TEXT["reward_risk"])

    pp1, pp2, pp3 = st.columns(3)
    pp1.metric("20일 고점 여지", f"{profit_plan.upside_to_20d_high:.2f}%", help=HELP_TEXT["upside"])
    pp2.metric("60일 고점 여지", f"{profit_plan.upside_to_60d_high:.2f}%", help=HELP_TEXT["upside"])
    pp3.metric("5일 모멘텀", f"{profit_plan.momentum_5d:.2f}%", help=HELP_TEXT["momentum_5d"])
    for note in profit_plan.notes:
        st.write(f"- {note}")

    st.subheader("최근 지표")
    recent = data[["Close", "MA5", "MA20", "MA60", "ATR20", "RSI14", "RETURN_5D", "RETURN_20D", "MACD", "MACD_SIGNAL", "Volume"]].tail(10)
    st.dataframe(recent.style.format("{:,.2f}"), use_container_width=True)

    st.caption(f"마지막 데이터 기준일: {data.index[-1].date() if hasattr(data.index[-1], 'date') else date.today()}")
