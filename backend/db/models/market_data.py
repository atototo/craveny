"""
KIS 시장 데이터 모델 (호가, 투자자매매동향, 종목정보, 업종지수).
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, BigInteger, Index
from datetime import datetime
from backend.db.base import Base


class StockOrderbook(Base):
    """
    호가 데이터 모델 (10단계 매수/매도호가).

    Attributes:
        id: Primary key
        stock_code: 종목 코드
        datetime: 호가 시간
        askp1~10: 매도 1~10호가
        askp_rsqn1~10: 매도 1~10호가 잔량
        bidp1~10: 매수 1~10호가
        bidp_rsqn1~10: 매수 1~10호가 잔량
        total_askp_rsqn: 총 매도 잔량
        total_bidp_rsqn: 총 매수 잔량
        created_at: 생성일시
    """

    __tablename__ = "stock_orderbook"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    datetime = Column(DateTime, nullable=False, index=True)

    # 매도 호가 (1~10)
    askp1 = Column(Float, nullable=True)
    askp2 = Column(Float, nullable=True)
    askp3 = Column(Float, nullable=True)
    askp4 = Column(Float, nullable=True)
    askp5 = Column(Float, nullable=True)
    askp6 = Column(Float, nullable=True)
    askp7 = Column(Float, nullable=True)
    askp8 = Column(Float, nullable=True)
    askp9 = Column(Float, nullable=True)
    askp10 = Column(Float, nullable=True)

    # 매도 호가 잔량 (1~10)
    askp_rsqn1 = Column(BigInteger, nullable=True)
    askp_rsqn2 = Column(BigInteger, nullable=True)
    askp_rsqn3 = Column(BigInteger, nullable=True)
    askp_rsqn4 = Column(BigInteger, nullable=True)
    askp_rsqn5 = Column(BigInteger, nullable=True)
    askp_rsqn6 = Column(BigInteger, nullable=True)
    askp_rsqn7 = Column(BigInteger, nullable=True)
    askp_rsqn8 = Column(BigInteger, nullable=True)
    askp_rsqn9 = Column(BigInteger, nullable=True)
    askp_rsqn10 = Column(BigInteger, nullable=True)

    # 매수 호가 (1~10)
    bidp1 = Column(Float, nullable=True)
    bidp2 = Column(Float, nullable=True)
    bidp3 = Column(Float, nullable=True)
    bidp4 = Column(Float, nullable=True)
    bidp5 = Column(Float, nullable=True)
    bidp6 = Column(Float, nullable=True)
    bidp7 = Column(Float, nullable=True)
    bidp8 = Column(Float, nullable=True)
    bidp9 = Column(Float, nullable=True)
    bidp10 = Column(Float, nullable=True)

    # 매수 호가 잔량 (1~10)
    bidp_rsqn1 = Column(BigInteger, nullable=True)
    bidp_rsqn2 = Column(BigInteger, nullable=True)
    bidp_rsqn3 = Column(BigInteger, nullable=True)
    bidp_rsqn4 = Column(BigInteger, nullable=True)
    bidp_rsqn5 = Column(BigInteger, nullable=True)
    bidp_rsqn6 = Column(BigInteger, nullable=True)
    bidp_rsqn7 = Column(BigInteger, nullable=True)
    bidp_rsqn8 = Column(BigInteger, nullable=True)
    bidp_rsqn9 = Column(BigInteger, nullable=True)
    bidp_rsqn10 = Column(BigInteger, nullable=True)

    # 총 호가 잔량
    total_askp_rsqn = Column(BigInteger, nullable=True)
    total_bidp_rsqn = Column(BigInteger, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)

    __table_args__ = (
        Index("idx_orderbook_stock_datetime", "stock_code", "datetime"),
    )

    def __repr__(self) -> str:
        return (
            f"<StockOrderbook(stock_code='{self.stock_code}', datetime={self.datetime}, "
            f"bid1={self.bidp1}, ask1={self.askp1})>"
        )


class StockCurrentPrice(Base):
    """
    현재가 시세 데이터 (체결가, 거래량, PER, PBR, EPS, 시가총액).

    Attributes:
        id: Primary key
        stock_code: 종목 코드
        datetime: 시세 시간
        stck_prpr: 주식 현재가
        prdy_vrss: 전일 대비
        prdy_vrss_sign: 전일 대비 부호 (1:상한,2:상승,3:보합,4:하한,5:하락)
        prdy_ctrt: 전일 대비율
        acml_vol: 누적 거래량
        acml_tr_pbmn: 누적 거래대금
        per: PER (Price Earning Ratio)
        pbr: PBR (Price Book-value Ratio)
        eps: EPS (주당순이익)
        bps: BPS (주당순자산가치)
        hts_avls: 시가총액 (HTS 시가총액)
        created_at: 생성일시
    """

    __tablename__ = "stock_current_price"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    datetime = Column(DateTime, nullable=False, index=True)

    # 가격 정보
    stck_prpr = Column(Float, nullable=True)  # 주식 현재가
    prdy_vrss = Column(Float, nullable=True)  # 전일 대비
    prdy_vrss_sign = Column(String(1), nullable=True)  # 전일 대비 부호
    prdy_ctrt = Column(Float, nullable=True)  # 전일 대비율

    # 거래량 정보
    acml_vol = Column(BigInteger, nullable=True)  # 누적 거래량
    acml_tr_pbmn = Column(BigInteger, nullable=True)  # 누적 거래대금

    # 투자지표
    per = Column(Float, nullable=True)  # PER
    pbr = Column(Float, nullable=True)  # PBR
    eps = Column(Float, nullable=True)  # EPS
    bps = Column(Float, nullable=True)  # BPS
    hts_avls = Column(BigInteger, nullable=True)  # 시가총액

    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)

    __table_args__ = (
        Index("idx_current_price_stock_datetime", "stock_code", "datetime"),
    )

    def __repr__(self) -> str:
        return (
            f"<StockCurrentPrice(stock_code='{self.stock_code}', datetime={self.datetime}, "
            f"price={self.stck_prpr}, per={self.per}, pbr={self.pbr})>"
        )


class InvestorTrading(Base):
    """
    투자자별 매매동향 데이터.

    Attributes:
        id: Primary key
        stock_code: 종목 코드
        date: 거래일
        stck_clpr: 주식 종가
        prsn_ntby_qty: 개인 순매수 수량
        frgn_ntby_qty: 외국인 순매수 수량
        orgn_ntby_qty: 기관계 순매수 수량
        prsn_ntby_tr_pbmn: 개인 순매수 거래대금
        frgn_ntby_tr_pbmn: 외국인 순매수 거래대금
        orgn_ntby_tr_pbmn: 기관계 순매수 거래대금
        created_at: 생성일시
    """

    __tablename__ = "investor_trading"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)

    stck_clpr = Column(Float, nullable=True)  # 주식 종가

    # 수량 기준
    prsn_ntby_qty = Column(BigInteger, nullable=True)  # 개인 순매수 수량
    frgn_ntby_qty = Column(BigInteger, nullable=True)  # 외국인 순매수 수량
    orgn_ntby_qty = Column(BigInteger, nullable=True)  # 기관계 순매수 수량

    # 거래대금 기준
    prsn_ntby_tr_pbmn = Column(BigInteger, nullable=True)  # 개인 순매수 거래대금
    frgn_ntby_tr_pbmn = Column(BigInteger, nullable=True)  # 외국인 순매수 거래대금
    orgn_ntby_tr_pbmn = Column(BigInteger, nullable=True)  # 기관계 순매수 거래대금

    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)

    __table_args__ = (
        Index("idx_investor_trading_stock_date", "stock_code", "date"),
    )

    def __repr__(self) -> str:
        return (
            f"<InvestorTrading(stock_code='{self.stock_code}', date={self.date}, "
            f"frgn_net={self.frgn_ntby_qty}, orgn_net={self.orgn_ntby_qty})>"
        )


class StockInfo(Base):
    """
    종목 기본정보 (업종, 시가총액, 상장주식수, 자본금).

    Attributes:
        id: Primary key
        stock_code: 종목 코드
        std_idst_clsf_cd: 표준산업분류코드
        std_idst_clsf_cd_name: 업종명
        hts_avls: 시가총액
        lstn_stcn: 상장주식수
        cpfn: 자본금
        updated_at: 수정일시
    """

    __tablename__ = "stock_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), unique=True, nullable=False, index=True)

    std_idst_clsf_cd = Column(String(10), nullable=True)  # 표준산업분류코드
    std_idst_clsf_cd_name = Column(String(100), nullable=True)  # 업종명
    hts_avls = Column(BigInteger, nullable=True)  # 시가총액
    lstn_stcn = Column(BigInteger, nullable=True)  # 상장주식수
    cpfn = Column(BigInteger, nullable=True)  # 자본금

    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<StockInfo(stock_code='{self.stock_code}', "
            f"sector='{self.std_idst_clsf_cd_name}', market_cap={self.hts_avls})>"
        )


class SectorIndex(Base):
    """
    업종 지수 데이터.

    Attributes:
        id: Primary key
        sector_code: 업종 코드 (0001:KOSPI, 1001:KOSDAQ, 0050:IT 등)
        datetime: 지수 시간
        bstp_nmix_prpr: 업종 현재지수
        bstp_nmix_prdy_vrss: 전일 대비
        bstp_nmix_prdy_ctrt: 전일 대비율
        acml_vol: 누적 거래량
        acml_tr_pbmn: 누적 거래대금
        created_at: 생성일시
    """

    __tablename__ = "sector_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sector_code = Column(String(10), nullable=False, index=True)
    datetime = Column(DateTime, nullable=False, index=True)

    bstp_nmix_prpr = Column(Float, nullable=True)  # 업종 현재지수
    bstp_nmix_prdy_vrss = Column(Float, nullable=True)  # 전일 대비
    bstp_nmix_prdy_ctrt = Column(Float, nullable=True)  # 전일 대비율
    acml_vol = Column(BigInteger, nullable=True)  # 누적 거래량
    acml_tr_pbmn = Column(BigInteger, nullable=True)  # 누적 거래대금

    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)

    __table_args__ = (
        Index("idx_sector_index_code_datetime", "sector_code", "datetime"),
    )

    def __repr__(self) -> str:
        return (
            f"<SectorIndex(sector_code='{self.sector_code}', datetime={self.datetime}, "
            f"index={self.bstp_nmix_prpr})>"
        )


class IndexDailyPrice(Base):
    """
    업종/지수 일자별 데이터 모델 (KIS API)

    KOSPI, KOSDAQ, 업종별 지수의 일봉 데이터
    - 데이터 출처: KIS API (FHPUP02120000)
    - 수집 주기: 매일 1회 (장마감 후)
    - 보관 기간: 최근 100일

    Attributes:
        id: Primary key
        index_code: 지수 코드 (0001:KOSPI, 1001:KOSDAQ, 2001:KOSPI200 등)
        index_name: 지수명 (선택, 조회 편의용)
        date: 영업일자
        open: 시가
        high: 최고가
        low: 최저가
        close: 종가
        volume: 누적 거래량
        trading_value: 누적 거래대금
        change: 전일 대비
        change_rate: 전일 대비율
        change_sign: 전일 대비 부호 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락)
        created_at: 생성일시
    """

    __tablename__ = "index_daily_price"

    id = Column(Integer, primary_key=True, autoincrement=True)
    index_code = Column(String(10), nullable=False, index=True)
    index_name = Column(String(50), nullable=True)
    date = Column(Date, nullable=False, index=True)

    # OHLC
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)

    # 거래량/거래대금
    volume = Column(BigInteger, nullable=True)
    trading_value = Column(BigInteger, nullable=True)

    # 등락 정보
    change = Column(Float, nullable=True)
    change_rate = Column(Float, nullable=True)
    change_sign = Column(String(1), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)

    __table_args__ = (
        Index("idx_index_daily_code_date", "index_code", "date"),
        Index("uk_index_daily_code_date", "index_code", "date", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<IndexDailyPrice(code='{self.index_code}', date={self.date}, "
            f"close={self.close}, change_rate={self.change_rate})>"
        )


class StockOvertimePrice(Base):
    """
    시간외 거래 가격 데이터 모델

    시간외 단일가 거래:
    - 장전 시간외: 08:30~09:00 (동시호가)
    - 장후 시간외 종가: 15:40~16:00 (동시호가)
    - 장후 시간외 단일가: 16:00~18:00 (단일가)
    """
    __tablename__ = "stock_overtime_price"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)

    # 일자 (영업일 기준)
    date = Column(Date, nullable=False, index=True)

    # 시간외 거래 가격
    ovtm_untp_prpr = Column(Float, nullable=True)  # 시간외 단일가 현재가
    ovtm_untp_prdy_vrss = Column(Float, nullable=True)  # 전일 대비
    prdy_vrss_sign = Column(String(1), nullable=True)  # 전일 대비 부호 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락)
    ovtm_untp_prdy_ctrt = Column(Float, nullable=True)  # 전일 대비율

    # 거래량/거래대금
    acml_vol = Column(BigInteger, nullable=True)  # 누적 거래량
    acml_tr_pbmn = Column(BigInteger, nullable=True)  # 누적 거래대금

    # 예상 체결 정보 (장전/장후 시간외 종가 시간대)
    ovtm_untp_antc_cnpr = Column(Float, nullable=True)  # 예상 체결가
    ovtm_untp_antc_cntg_vrss = Column(Float, nullable=True)  # 예상 체결 대비
    ovtm_untp_antc_cntg_vrss_sign = Column(String(1), nullable=True)  # 예상 체결 대비 부호
    ovtm_untp_antc_cntg_ctrt = Column(Float, nullable=True)  # 예상 체결 대비율
    ovtm_untp_antc_vol = Column(BigInteger, nullable=True)  # 예상 거래량

    # 메타데이터
    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)

    __table_args__ = (
        Index("idx_overtime_price_stock_date", "stock_code", "date"),
        # 일자별 중복 방지
        Index("uk_overtime_price_stock_date", "stock_code", "date", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<StockOvertimePrice(stock_code='{self.stock_code}', date={self.date}, "
            f"price={self.ovtm_untp_prpr}, volume={self.acml_vol})>"
        )
