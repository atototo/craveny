"""
한국 증시 시장 시간 유틸리티

시장 단계별 동적 TTL 및 임계값 제공
"""
from datetime import datetime, time
from pytz import timezone


def get_market_phase() -> str:
    """현재 한국 증시 단계 반환
    
    Returns:
        str: pre_market | market_open | trading | market_close | after_hours
    """
    kst = timezone('Asia/Seoul')
    now = datetime.now(kst).time()

    if time(0, 0) <= now < time(9, 0):
        return "pre_market"
    elif time(9, 0) <= now < time(9, 30):
        return "market_open"
    elif time(9, 30) <= now < time(15, 30):
        return "trading"
    elif time(15, 30) <= now < time(15, 36):
        return "market_close"
    else:
        return "after_hours"


def get_ttl_hours(market_phase: str) -> int:
    """시장 단계별 리포트 TTL 반환
    
    Args:
        market_phase: 시장 단계 (get_market_phase() 결과)
    
    Returns:
        int: TTL (시간)
    """
    ttl_map = {
        "pre_market": 3,
        "market_open": 1,
        "trading": 2,
        "market_close": 1,
        "after_hours": 6,
    }
    return ttl_map[market_phase]


def get_price_threshold(market_phase: str) -> float:
    """시장 단계별 주가 변동 감지 임계값 (%)
    
    Args:
        market_phase: 시장 단계
    
    Returns:
        float: 임계값 (%)
    """
    return 3.0 if market_phase == "trading" else 5.0


def get_direction_threshold(market_phase: str) -> float:
    """시장 단계별 예측 방향 변화 감지 임계값

    Args:
        market_phase: 시장 단계

    Returns:
        float: 임계값 (0.0 ~ 1.0)
    """
    return 0.15 if market_phase in ["trading", "market_open", "market_close"] else 0.20


def is_market_open() -> bool:
    """한국 증시 개장 여부 확인

    Returns:
        bool: 장중이면 True, 아니면 False
    """
    phase = get_market_phase()
    return phase in ["market_open", "trading", "market_close"]
