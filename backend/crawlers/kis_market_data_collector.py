"""
KIS API 시장 데이터 수집기

호가, 현재가, 투자자매매동향, 종목정보, 업종지수 데이터를 수집하여 DB에 저장합니다.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock
from backend.db.models.market_data import (
    StockOrderbook,
    StockCurrentPrice,
    InvestorTrading,
    StockInfo,
    SectorIndex,
)
from backend.crawlers.kis_client import get_kis_client


logger = logging.getLogger(__name__)


class OrderbookCollector:
    """호가 데이터 수집기"""

    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.collected_count = 0
        self.failed_count = 0

    async def collect_orderbook(self, stock_code: str) -> Dict[str, Any]:
        """
        단일 종목의 호가 데이터 수집

        Args:
            stock_code: 종목 코드

        Returns:
            수집 결과 딕셔너리
        """
        try:
            client = await get_kis_client()
            result = await client.get_orderbook(stock_code=stock_code)

            output1 = result.get("output1", {})
            if not output1:
                logger.warning(f"⚠️  {stock_code}: 호가 데이터 없음")
                return {
                    "stock_code": stock_code,
                    "status": "skipped",
                    "error": "No data"
                }

            # DB 저장
            await self._save_to_db(stock_code, output1)
            self.collected_count += 1
            logger.info(f"✅ {stock_code}: 호가 저장 완료")

            return {
                "stock_code": stock_code,
                "status": "success"
            }

        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ {stock_code}: 호가 수집 실패 - {e}")
            return {
                "stock_code": stock_code,
                "status": "failed",
                "error": str(e)
            }

    async def _save_to_db(self, stock_code: str, data: Dict[str, Any]) -> None:
        """호가 데이터를 DB에 저장"""
        db = SessionLocal()
        try:
            orderbook = StockOrderbook(
                stock_code=stock_code,
                datetime=datetime.now(),
                # 매도 호가
                askp1=float(data.get("askp1", 0) or 0),
                askp2=float(data.get("askp2", 0) or 0),
                askp3=float(data.get("askp3", 0) or 0),
                askp4=float(data.get("askp4", 0) or 0),
                askp5=float(data.get("askp5", 0) or 0),
                askp6=float(data.get("askp6", 0) or 0),
                askp7=float(data.get("askp7", 0) or 0),
                askp8=float(data.get("askp8", 0) or 0),
                askp9=float(data.get("askp9", 0) or 0),
                askp10=float(data.get("askp10", 0) or 0),
                # 매도 호가 잔량
                askp_rsqn1=int(data.get("askp_rsqn1", 0) or 0),
                askp_rsqn2=int(data.get("askp_rsqn2", 0) or 0),
                askp_rsqn3=int(data.get("askp_rsqn3", 0) or 0),
                askp_rsqn4=int(data.get("askp_rsqn4", 0) or 0),
                askp_rsqn5=int(data.get("askp_rsqn5", 0) or 0),
                askp_rsqn6=int(data.get("askp_rsqn6", 0) or 0),
                askp_rsqn7=int(data.get("askp_rsqn7", 0) or 0),
                askp_rsqn8=int(data.get("askp_rsqn8", 0) or 0),
                askp_rsqn9=int(data.get("askp_rsqn9", 0) or 0),
                askp_rsqn10=int(data.get("askp_rsqn10", 0) or 0),
                # 매수 호가
                bidp1=float(data.get("bidp1", 0) or 0),
                bidp2=float(data.get("bidp2", 0) or 0),
                bidp3=float(data.get("bidp3", 0) or 0),
                bidp4=float(data.get("bidp4", 0) or 0),
                bidp5=float(data.get("bidp5", 0) or 0),
                bidp6=float(data.get("bidp6", 0) or 0),
                bidp7=float(data.get("bidp7", 0) or 0),
                bidp8=float(data.get("bidp8", 0) or 0),
                bidp9=float(data.get("bidp9", 0) or 0),
                bidp10=float(data.get("bidp10", 0) or 0),
                # 매수 호가 잔량
                bidp_rsqn1=int(data.get("bidp_rsqn1", 0) or 0),
                bidp_rsqn2=int(data.get("bidp_rsqn2", 0) or 0),
                bidp_rsqn3=int(data.get("bidp_rsqn3", 0) or 0),
                bidp_rsqn4=int(data.get("bidp_rsqn4", 0) or 0),
                bidp_rsqn5=int(data.get("bidp_rsqn5", 0) or 0),
                bidp_rsqn6=int(data.get("bidp_rsqn6", 0) or 0),
                bidp_rsqn7=int(data.get("bidp_rsqn7", 0) or 0),
                bidp_rsqn8=int(data.get("bidp_rsqn8", 0) or 0),
                bidp_rsqn9=int(data.get("bidp_rsqn9", 0) or 0),
                bidp_rsqn10=int(data.get("bidp_rsqn10", 0) or 0),
                # 총 호가 잔량
                total_askp_rsqn=int(data.get("total_askp_rsqn", 0) or 0),
                total_bidp_rsqn=int(data.get("total_bidp_rsqn", 0) or 0),
            )
            db.add(orderbook)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"DB 저장 실패: {stock_code} - {e}")
            raise
        finally:
            db.close()

    async def collect_all(self, stock_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        전체 종목 호가 데이터 수집

        Args:
            stock_codes: 수집할 종목 코드 리스트 (None이면 전체)

        Returns:
            수집 통계
        """
        db = SessionLocal()
        try:
            if stock_codes is None:
                stocks = db.query(Stock).filter(Stock.is_active == True).all()
                stock_codes = [s.code for s in stocks]

            logger.info(f"🎯 호가 수집 시작: {len(stock_codes)}개 종목")

            # 배치 단위로 수집
            for i in range(0, len(stock_codes), self.batch_size):
                batch = stock_codes[i:i + self.batch_size]
                tasks = [self.collect_orderbook(code) for code in batch]
                await asyncio.gather(*tasks, return_exceptions=True)

                # Rate limiting
                await asyncio.sleep(0.5)

            logger.info(
                f"📊 호가 수집 완료: "
                f"성공 {self.collected_count}건, "
                f"실패 {self.failed_count}건"
            )

            return {
                "collected": self.collected_count,
                "failed": self.failed_count
            }

        finally:
            db.close()


class CurrentPriceCollector:
    """현재가 데이터 수집기"""

    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.collected_count = 0
        self.failed_count = 0

    async def collect_current_price(self, stock_code: str) -> Dict[str, Any]:
        """단일 종목의 현재가 데이터 수집"""
        try:
            client = await get_kis_client()
            result = await client.get_current_price(stock_code=stock_code)

            output = result.get("output", {})
            if not output:
                logger.warning(f"⚠️  {stock_code}: 현재가 데이터 없음")
                return {
                    "stock_code": stock_code,
                    "status": "skipped",
                    "error": "No data"
                }

            await self._save_to_db(stock_code, output)
            self.collected_count += 1
            logger.info(f"✅ {stock_code}: 현재가 저장 완료")

            return {
                "stock_code": stock_code,
                "status": "success"
            }

        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ {stock_code}: 현재가 수집 실패 - {e}")
            return {
                "stock_code": stock_code,
                "status": "failed",
                "error": str(e)
            }

    async def _save_to_db(self, stock_code: str, data: Dict[str, Any]) -> None:
        """현재가 데이터를 DB에 저장"""
        db = SessionLocal()
        try:
            current_price = StockCurrentPrice(
                stock_code=stock_code,
                datetime=datetime.now(),
                stck_prpr=float(data.get("stck_prpr", 0) or 0),
                prdy_vrss=float(data.get("prdy_vrss", 0) or 0),
                prdy_vrss_sign=data.get("prdy_vrss_sign"),
                prdy_ctrt=float(data.get("prdy_ctrt", 0) or 0),
                acml_vol=int(data.get("acml_vol", 0) or 0),
                acml_tr_pbmn=int(data.get("acml_tr_pbmn", 0) or 0),
                per=float(data.get("per", 0) or 0) if data.get("per") else None,
                pbr=float(data.get("pbr", 0) or 0) if data.get("pbr") else None,
                eps=float(data.get("eps", 0) or 0) if data.get("eps") else None,
                bps=float(data.get("bps", 0) or 0) if data.get("bps") else None,
                hts_avls=int(data.get("hts_avls", 0) or 0) if data.get("hts_avls") else None,
            )
            db.add(current_price)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"DB 저장 실패: {stock_code} - {e}")
            raise
        finally:
            db.close()

    async def collect_all(self, stock_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """전체 종목 현재가 데이터 수집"""
        db = SessionLocal()
        try:
            if stock_codes is None:
                stocks = db.query(Stock).filter(Stock.is_active == True).all()
                stock_codes = [s.code for s in stocks]

            logger.info(f"🎯 현재가 수집 시작: {len(stock_codes)}개 종목")

            for i in range(0, len(stock_codes), self.batch_size):
                batch = stock_codes[i:i + self.batch_size]
                tasks = [self.collect_current_price(code) for code in batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.5)

            logger.info(
                f"📊 현재가 수집 완료: "
                f"성공 {self.collected_count}건, "
                f"실패 {self.failed_count}건"
            )

            return {
                "collected": self.collected_count,
                "failed": self.failed_count
            }

        finally:
            db.close()


class InvestorTradingCollector:
    """투자자별 매매동향 수집기"""

    def __init__(self, batch_size: int = 5):
        self.batch_size = batch_size
        self.collected_count = 0
        self.failed_count = 0

    async def collect_investor_trading(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """단일 종목의 투자자별 매매동향 수집"""
        try:
            client = await get_kis_client()
            result = await client.get_investor_trading(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date
            )

            output = result.get("output", [])
            if not output:
                logger.warning(f"⚠️  {stock_code}: 투자자 데이터 없음")
                return {
                    "stock_code": stock_code,
                    "status": "skipped",
                    "error": "No data"
                }

            saved = await self._save_to_db(stock_code, output)
            self.collected_count += saved
            logger.info(f"✅ {stock_code}: 투자자 데이터 {saved}건 저장")

            return {
                "stock_code": stock_code,
                "status": "success",
                "saved": saved
            }

        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ {stock_code}: 투자자 데이터 수집 실패 - {e}")
            return {
                "stock_code": stock_code,
                "status": "failed",
                "error": str(e)
            }

    async def _save_to_db(self, stock_code: str, data: List[Dict[str, Any]]) -> int:
        """투자자별 매매동향을 DB에 저장"""
        db = SessionLocal()
        saved_count = 0
        try:
            for item in data:
                date_str = item.get("stck_bsop_date")
                if not date_str:
                    continue

                trade_date = datetime.strptime(date_str, "%Y%m%d")

                # 중복 체크
                existing = db.query(InvestorTrading).filter(
                    InvestorTrading.stock_code == stock_code,
                    InvestorTrading.date == trade_date
                ).first()

                if existing:
                    continue

                investor_trading = InvestorTrading(
                    stock_code=stock_code,
                    date=trade_date,
                    stck_clpr=float(item.get("stck_clpr", 0) or 0),
                    prsn_ntby_qty=int(item.get("prsn_ntby_qty", 0) or 0),
                    frgn_ntby_qty=int(item.get("frgn_ntby_qty", 0) or 0),
                    orgn_ntby_qty=int(item.get("orgn_ntby_qty", 0) or 0),
                    prsn_ntby_tr_pbmn=int(item.get("prsn_ntby_tr_pbmn", 0) or 0),
                    frgn_ntby_tr_pbmn=int(item.get("frgn_ntby_tr_pbmn", 0) or 0),
                    orgn_ntby_tr_pbmn=int(item.get("orgn_ntby_tr_pbmn", 0) or 0),
                )
                db.add(investor_trading)
                saved_count += 1

            db.commit()
            return saved_count

        except Exception as e:
            db.rollback()
            logger.error(f"DB 저장 실패: {stock_code} - {e}")
            raise
        finally:
            db.close()

    async def collect_all(
        self,
        stock_codes: Optional[List[str]] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """전체 종목 투자자별 매매동향 수집"""
        db = SessionLocal()
        try:
            if stock_codes is None:
                stocks = db.query(Stock).filter(Stock.is_active == True).all()
                stock_codes = [s.code for s in stocks]

            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            logger.info(
                f"🎯 투자자 매매동향 수집 시작: {len(stock_codes)}개 종목 "
                f"({start_date} ~ {end_date})"
            )

            for i in range(0, len(stock_codes), self.batch_size):
                batch = stock_codes[i:i + self.batch_size]
                tasks = [
                    self.collect_investor_trading(code, start_date, end_date)
                    for code in batch
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(1.0)  # More conservative rate limiting

            logger.info(
                f"📊 투자자 매매동향 수집 완료: "
                f"성공 {self.collected_count}건, "
                f"실패 {self.failed_count}건"
            )

            return {
                "collected": self.collected_count,
                "failed": self.failed_count
            }

        finally:
            db.close()


class StockInfoCollector:
    """종목 기본정보 수집기"""

    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.collected_count = 0
        self.failed_count = 0

    async def collect_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """단일 종목의 기본정보 수집"""
        try:
            client = await get_kis_client()
            result = await client.get_stock_info(stock_code=stock_code)

            # output이 list일 수도 있고 dict일 수도 있음
            output = result.get("output", {})

            # output이 리스트인 경우 첫 번째 항목 사용
            if isinstance(output, list):
                if not output:
                    logger.warning(f"⚠️  {stock_code}: 종목정보 없음 (빈 리스트)")
                    return {
                        "stock_code": stock_code,
                        "status": "skipped",
                        "error": "Empty list"
                    }
                output = output[0]

            if not output:
                logger.warning(f"⚠️  {stock_code}: 종목정보 없음")
                return {
                    "stock_code": stock_code,
                    "status": "skipped",
                    "error": "No data"
                }

            await self._save_to_db(stock_code, output)
            self.collected_count += 1
            logger.info(f"✅ {stock_code}: 종목정보 저장 완료")

            return {
                "stock_code": stock_code,
                "status": "success"
            }

        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ {stock_code}: 종목정보 수집 실패 - {e}")
            return {
                "stock_code": stock_code,
                "status": "failed",
                "error": str(e)
            }

    async def _save_to_db(self, stock_code: str, data: Dict[str, Any]) -> None:
        """종목 기본정보를 DB에 저장 (upsert)"""
        db = SessionLocal()
        try:
            # 기존 레코드 확인
            stock_info = db.query(StockInfo).filter(
                StockInfo.stock_code == stock_code
            ).first()

            if stock_info:
                # 업데이트
                stock_info.std_idst_clsf_cd = data.get("std_idst_clsf_cd")
                stock_info.std_idst_clsf_cd_name = data.get("std_idst_clsf_cd_name")
                stock_info.hts_avls = int(data.get("hts_avls", 0) or 0) if data.get("hts_avls") else None
                stock_info.lstn_stcn = int(data.get("lstn_stcn", 0) or 0) if data.get("lstn_stcn") else None
                stock_info.cpfn = int(data.get("cpfn", 0) or 0) if data.get("cpfn") else None
                stock_info.updated_at = datetime.now()
            else:
                # 새로 생성
                stock_info = StockInfo(
                    stock_code=stock_code,
                    std_idst_clsf_cd=data.get("std_idst_clsf_cd"),
                    std_idst_clsf_cd_name=data.get("std_idst_clsf_cd_name"),
                    hts_avls=int(data.get("hts_avls", 0) or 0) if data.get("hts_avls") else None,
                    lstn_stcn=int(data.get("lstn_stcn", 0) or 0) if data.get("lstn_stcn") else None,
                    cpfn=int(data.get("cpfn", 0) or 0) if data.get("cpfn") else None,
                )
                db.add(stock_info)

            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"DB 저장 실패: {stock_code} - {e}")
            raise
        finally:
            db.close()

    async def collect_all(self, stock_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """전체 종목 기본정보 수집"""
        db = SessionLocal()
        try:
            if stock_codes is None:
                stocks = db.query(Stock).filter(Stock.is_active == True).all()
                stock_codes = [s.code for s in stocks]

            logger.info(f"🎯 종목정보 수집 시작: {len(stock_codes)}개 종목")

            for i in range(0, len(stock_codes), self.batch_size):
                batch = stock_codes[i:i + self.batch_size]
                tasks = [self.collect_stock_info(code) for code in batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.5)

            logger.info(
                f"📊 종목정보 수집 완료: "
                f"성공 {self.collected_count}건, "
                f"실패 {self.failed_count}건"
            )

            return {
                "collected": self.collected_count,
                "failed": self.failed_count
            }

        finally:
            db.close()


class SectorIndexCollector:
    """업종 지수 수집기"""

    # 주요 업종 코드 매핑
    SECTOR_CODES = {
        "0001": "KOSPI",
        "1001": "KOSDAQ",
        "0050": "KOSPI IT",
        "0051": "KOSPI 금융",
        "0052": "KOSPI 산업재",
        "0053": "KOSPI 경기소비재",
        "0054": "KOSPI 필수소비재",
        "0055": "KOSPI 에너지",
        "0056": "KOSPI 화학",
        "0057": "KOSPI 비철금속",
        "0058": "KOSPI 철강",
        "0059": "KOSPI 건설",
    }

    def __init__(self):
        self.collected_count = 0
        self.failed_count = 0

    async def collect_sector_index(self, sector_code: str) -> Dict[str, Any]:
        """단일 업종 지수 수집"""
        try:
            client = await get_kis_client()
            result = await client.get_sector_index(sector_code=sector_code)

            output = result.get("output", {})
            if not output:
                logger.warning(f"⚠️  {sector_code}: 업종 지수 데이터 없음")
                return {
                    "sector_code": sector_code,
                    "status": "skipped",
                    "error": "No data"
                }

            await self._save_to_db(sector_code, output)
            self.collected_count += 1

            sector_name = self.SECTOR_CODES.get(sector_code, sector_code)
            logger.info(f"✅ {sector_name}: 업종 지수 저장 완료")

            return {
                "sector_code": sector_code,
                "status": "success"
            }

        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ {sector_code}: 업종 지수 수집 실패 - {e}")
            return {
                "sector_code": sector_code,
                "status": "failed",
                "error": str(e)
            }

    async def _save_to_db(self, sector_code: str, data: Dict[str, Any]) -> None:
        """업종 지수 데이터를 DB에 저장"""
        db = SessionLocal()
        try:
            sector_index = SectorIndex(
                sector_code=sector_code,
                datetime=datetime.now(),
                bstp_nmix_prpr=float(data.get("bstp_nmix_prpr", 0) or 0),
                bstp_nmix_prdy_vrss=float(data.get("bstp_nmix_prdy_vrss", 0) or 0),
                bstp_nmix_prdy_ctrt=float(data.get("bstp_nmix_prdy_ctrt", 0) or 0),
                acml_vol=int(data.get("acml_vol", 0) or 0) if data.get("acml_vol") else None,
                acml_tr_pbmn=int(data.get("acml_tr_pbmn", 0) or 0) if data.get("acml_tr_pbmn") else None,
            )
            db.add(sector_index)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"DB 저장 실패: {sector_code} - {e}")
            raise
        finally:
            db.close()

    async def collect_all(self) -> Dict[str, Any]:
        """전체 업종 지수 수집"""
        logger.info(f"🎯 업종 지수 수집 시작: {len(self.SECTOR_CODES)}개 업종")

        # 순차적으로 수집 (rate limiting 고려)
        for sector_code in self.SECTOR_CODES.keys():
            await self.collect_sector_index(sector_code)
            await asyncio.sleep(0.5)  # Rate limiting

        logger.info(
            f"📊 업종 지수 수집 완료: "
            f"성공 {self.collected_count}건, "
            f"실패 {self.failed_count}건"
        )

        return {
            "collected": self.collected_count,
            "failed": self.failed_count
        }


class OvertimePriceCollector:
    """시간외 거래 가격 수집기"""

    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.collected_count = 0
        self.failed_count = 0

    async def collect_overtime_prices(self, stock_code: str) -> Dict[str, Any]:
        """단일 종목의 시간외 거래 가격 수집 (과거 30일)"""
        try:
            client = await get_kis_client()
            result = await client.get_overtime_daily_prices(stock_code=stock_code)

            # output2에 일자별 데이터 있음
            output2 = result.get("output2", [])
            if not output2:
                logger.warning(f"⚠️  {stock_code}: 시간외 거래 데이터 없음")
                return {
                    "stock_code": stock_code,
                    "status": "skipped",
                    "saved": 0,
                    "error": "No data"
                }

            saved_count = await self._save_to_db(stock_code, output2)
            self.collected_count += 1
            logger.info(f"✅ {stock_code}: 시간외 거래 데이터 {saved_count}건 저장")

            return {
                "stock_code": stock_code,
                "status": "success",
                "saved": saved_count
            }

        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ {stock_code}: 시간외 거래 데이터 수집 실패 - {e}")
            return {
                "stock_code": stock_code,
                "status": "failed",
                "saved": 0,
                "error": str(e)
            }

    async def _save_to_db(self, stock_code: str, data: List[Dict[str, Any]]) -> int:
        """시간외 거래 데이터를 DB에 저장 (일자별)"""
        from backend.db.models.market_data import StockOvertimePrice

        db = SessionLocal()
        saved_count = 0

        try:
            for item in data:
                # 날짜 파싱
                date_str = item.get("stck_bsop_date")
                if not date_str:
                    continue

                trade_date = datetime.strptime(date_str, "%Y%m%d").date()

                # 중복 체크
                existing = db.query(StockOvertimePrice).filter(
                    StockOvertimePrice.stock_code == stock_code,
                    StockOvertimePrice.date == trade_date
                ).first()

                if existing:
                    # 기존 데이터 업데이트
                    existing.ovtm_untp_prpr = float(item.get("ovtm_untp_prpr", 0) or 0) if item.get("ovtm_untp_prpr") else None
                    existing.ovtm_untp_prdy_vrss = float(item.get("ovtm_untp_prdy_vrss", 0) or 0) if item.get("ovtm_untp_prdy_vrss") else None
                    existing.prdy_vrss_sign = item.get("prdy_vrss_sign")
                    existing.ovtm_untp_prdy_ctrt = float(item.get("ovtm_untp_prdy_ctrt", 0) or 0) if item.get("ovtm_untp_prdy_ctrt") else None
                    existing.acml_vol = int(item.get("acml_vol", 0) or 0) if item.get("acml_vol") else None
                    existing.acml_tr_pbmn = int(item.get("acml_tr_pbmn", 0) or 0) if item.get("acml_tr_pbmn") else None
                else:
                    # 새 데이터 삽입
                    overtime_price = StockOvertimePrice(
                        stock_code=stock_code,
                        date=trade_date,
                        ovtm_untp_prpr=float(item.get("ovtm_untp_prpr", 0) or 0) if item.get("ovtm_untp_prpr") else None,
                        ovtm_untp_prdy_vrss=float(item.get("ovtm_untp_prdy_vrss", 0) or 0) if item.get("ovtm_untp_prdy_vrss") else None,
                        prdy_vrss_sign=item.get("prdy_vrss_sign"),
                        ovtm_untp_prdy_ctrt=float(item.get("ovtm_untp_prdy_ctrt", 0) or 0) if item.get("ovtm_untp_prdy_ctrt") else None,
                        acml_vol=int(item.get("acml_vol", 0) or 0) if item.get("acml_vol") else None,
                        acml_tr_pbmn=int(item.get("acml_tr_pbmn", 0) or 0) if item.get("acml_tr_pbmn") else None,
                    )
                    db.add(overtime_price)

                saved_count += 1

            db.commit()
            return saved_count

        except Exception as e:
            db.rollback()
            logger.error(f"DB 저장 실패: {stock_code} - {e}")
            raise
        finally:
            db.close()

    async def collect_all(
        self,
        stock_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """전체 종목 시간외 거래 데이터 수집 (최근 30일)"""
        db = SessionLocal()
        try:
            if stock_codes is None:
                stocks = db.query(Stock).filter(Stock.is_active == True).all()
                stock_codes = [s.code for s in stocks]

            logger.info(f"🎯 시간외 거래 데이터 수집 시작: {len(stock_codes)}개 종목")

            # 배치 처리
            for i in range(0, len(stock_codes), self.batch_size):
                batch = stock_codes[i:i + self.batch_size]
                tasks = [self.collect_overtime_prices(code) for code in batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.5)  # Rate limiting

            logger.info(
                f"📊 시간외 거래 데이터 수집 완료: "
                f"성공 {self.collected_count}건, "
                f"실패 {self.failed_count}건"
            )

            return {
                "collected": self.collected_count,
                "failed": self.failed_count
            }

        finally:
            db.close()
