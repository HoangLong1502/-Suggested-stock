"""
Fundamental & Business Analysis Service for Vietnamese Stocks.
Integrates with vnstock and other free data sources.
"""
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

try:
    import vnstock as vs
except ImportError:
    vs = None

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.postgres import AsyncSessionLocal
from app.models.schema import CompanyFundamental, Stock


class FundamentalAnalyzer:
    """Analyzes company fundamentals and generates business ratings."""

    @staticmethod
    async def fetch_company_fundamentals(symbol: str) -> Dict[str, Any]:
        """
        Fetch company fundamentals from vnstock or cached database.
        """
        # Try to get from database first
        async with AsyncSessionLocal() as session:
            query = select(CompanyFundamental).where(
                CompanyFundamental.stock_symbol == symbol
            )
            result = await session.execute(query)
            cached = result.scalar_one_or_none()

            # If cached data exists and is recent (< 1 day), use it
            if cached:
                age_hours = (datetime.utcnow() - cached.updated_at).total_seconds() / 3600
                if age_hours < 24:
                    return FundamentalAnalyzer._entity_to_dict(cached)

            # Fetch fresh data from vnstock
            if vs is None:
                return {'status': 'vnstock_not_available'}

            try:
                # Fetch from vnstock
                # Note: These are free endpoints from vnstock library
                fundamentals = await asyncio.to_thread(
                    FundamentalAnalyzer._fetch_from_vnstock, symbol
                )

                # Save/update to database
                if fundamentals and fundamentals.get('status') != 'error':
                    await FundamentalAnalyzer._save_to_database(
                        symbol, fundamentals, session
                    )

                return fundamentals

            except Exception as e:
                return {'status': 'error', 'message': str(e)}

    @staticmethod
    def _fetch_from_vnstock(symbol: str) -> Dict[str, Any]:
        """
        Fetch fundamentals from vnstock (blocking call, run in thread).
        """
        try:
            # Get company info
            ticker = vs.Ticker(symbol)
            info = ticker.info.copy() if ticker.info else {}

            # Basic metrics
            fundamentals = {
                'stock_symbol': symbol,
                'company_name': info.get('companyName', symbol),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                
                # Financial metrics
                'pe_ratio': float(info.get('pe', 0.0)) if info.get('pe') else None,
                'pb_ratio': float(info.get('pb', 0.0)) if info.get('pb') else None,
                'roe': float(info.get('roe', 0.0)) if info.get('roe') else None,
                'roa': float(info.get('roa', 0.0)) if info.get('roa') else None,
                'debt_to_equity': float(info.get('debtToEquity', 0.0)) if info.get('debtToEquity') else None,
                'current_ratio': float(info.get('currentRatio', 0.0)) if info.get('currentRatio') else None,
                'quick_ratio': float(info.get('quickRatio', 0.0)) if info.get('quickRatio') else None,
                
                # Growth metrics
                'revenue_growth_yoy': float(info.get('revenueGrowthYoY', 0.0)) if info.get('revenueGrowthYoY') else None,
                'profit_growth_yoy': float(info.get('profitGrowthYoY', 0.0)) if info.get('profitGrowthYoY') else None,
                'revenue_growth_qoq': float(info.get('revenueGrowthQoQ', 0.0)) if info.get('revenueGrowthQoQ') else None,
                'profit_growth_qoq': float(info.get('profitGrowthQoQ', 0.0)) if info.get('profitGrowthQoQ') else None,
                
                # Market metrics
                'market_cap': float(info.get('marketCap', 0.0)) if info.get('marketCap') else None,
                'earnings_per_share': float(info.get('eps', 0.0)) if info.get('eps') else None,
                'dividend_yield': float(info.get('dividendYield', 0.0)) if info.get('dividendYield') else None,
                
                'data_source': 'vnstock',
                'status': 'success',
            }
            return fundamentals

        except Exception as e:
            return {
                'status': 'error',
                'message': f'vnstock fetch failed: {str(e)}',
                'stock_symbol': symbol,
            }

    @staticmethod
    async def _save_to_database(
        symbol: str,
        data: Dict[str, Any],
        session: AsyncSession,
    ) -> None:
        """Save or update fundamentals in database."""
        try:
            query = select(CompanyFundamental).where(
                CompanyFundamental.stock_symbol == symbol
            )
            result = await session.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                for key, value in data.items():
                    if key not in ['status', 'data_source']:
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
            else:
                # Create new
                new_record = CompanyFundamental(**data)
                session.add(new_record)

            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f'Database save failed: {e}')

    @staticmethod
    def _entity_to_dict(entity: CompanyFundamental) -> Dict[str, Any]:
        """Convert SQLAlchemy entity to dict."""
        return {
            'stock_symbol': entity.stock_symbol,
            'company_name': entity.company_name,
            'sector': entity.sector,
            'industry': entity.industry,
            'pe_ratio': entity.pe_ratio,
            'pb_ratio': entity.pb_ratio,
            'roe': entity.roe,
            'roa': entity.roa,
            'debt_to_equity': entity.debt_to_equity,
            'current_ratio': entity.current_ratio,
            'quick_ratio': entity.quick_ratio,
            'revenue_growth_yoy': entity.revenue_growth_yoy,
            'profit_growth_yoy': entity.profit_growth_yoy,
            'revenue_growth_qoq': entity.revenue_growth_qoq,
            'profit_growth_qoq': entity.profit_growth_qoq,
            'market_cap': entity.market_cap,
            'earnings_per_share': entity.earnings_per_share,
            'dividend_yield': entity.dividend_yield,
            'data_source': entity.data_source,
            'status': 'cached',
        }

    @staticmethod
    def score_fundamentals(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score company fundamentals on 0-100 scale.
        Higher is better.
        """
        if fundamentals.get('status') in ['error', 'vnstock_not_available']:
            return {'score': 0.0, 'components': {}}

        scores = {}
        weights = {}

        # 1. Valuation Score (0-30 points)
        # Lower PE is better (but positive)
        pe = fundamentals.get('pe_ratio')
        if pe and pe > 0:
            if pe < 10:
                scores['valuation_pe'] = 25
            elif pe < 15:
                scores['valuation_pe'] = 20
            elif pe < 20:
                scores['valuation_pe'] = 15
            elif pe < 30:
                scores['valuation_pe'] = 10
            else:
                scores['valuation_pe'] = 5
        else:
            scores['valuation_pe'] = 0

        pb = fundamentals.get('pb_ratio')
        if pb and pb > 0:
            if pb < 1:
                scores['valuation_pb'] = 30
            elif pb < 1.5:
                scores['valuation_pb'] = 25
            elif pb < 2:
                scores['valuation_pb'] = 20
            elif pb < 3:
                scores['valuation_pb'] = 10
            else:
                scores['valuation_pb'] = 5
        else:
            scores['valuation_pb'] = 0

        # 2. Profitability Score (0-25 points)
        roe = fundamentals.get('roe')
        if roe and roe > 0:
            if roe > 20:
                scores['profitability_roe'] = 25
            elif roe > 15:
                scores['profitability_roe'] = 20
            elif roe > 10:
                scores['profitability_roe'] = 15
            elif roe > 5:
                scores['profitability_roe'] = 10
            else:
                scores['profitability_roe'] = 5
        else:
            scores['profitability_roe'] = 0

        # 3. Growth Score (0-25 points)
        rev_growth = fundamentals.get('revenue_growth_yoy') or fundamentals.get('revenue_growth_qoq') or 0
        if rev_growth > 0.2:  # > 20%
            scores['growth_revenue'] = 25
        elif rev_growth > 0.1:  # > 10%
            scores['growth_revenue'] = 20
        elif rev_growth > 0.05:  # > 5%
            scores['growth_revenue'] = 15
        elif rev_growth > 0:
            scores['growth_revenue'] = 10
        else:
            scores['growth_revenue'] = 5

        profit_growth = fundamentals.get('profit_growth_yoy') or fundamentals.get('profit_growth_qoq') or 0
        if profit_growth > 0.25:  # > 25%
            scores['growth_profit'] = 25
        elif profit_growth > 0.15:  # > 15%
            scores['growth_profit'] = 20
        elif profit_growth > 0.08:  # > 8%
            scores['growth_profit'] = 15
        elif profit_growth > 0:
            scores['growth_profit'] = 10
        else:
            scores['growth_profit'] = 5

        # 4. Financial Health Score (0-20 points)
        debt_to_equity = fundamentals.get('debt_to_equity')
        if debt_to_equity is not None:
            if debt_to_equity < 0.5:
                scores['health_debt'] = 20
            elif debt_to_equity < 1:
                scores['health_debt'] = 15
            elif debt_to_equity < 1.5:
                scores['health_debt'] = 10
            else:
                scores['health_debt'] = 5
        else:
            scores['health_debt'] = 10

        current_ratio = fundamentals.get('current_ratio')
        if current_ratio:
            if current_ratio > 1.5:
                scores['health_liquidity'] = 20
            elif current_ratio > 1:
                scores['health_liquidity'] = 15
            elif current_ratio > 0.8:
                scores['health_liquidity'] = 10
            else:
                scores['health_liquidity'] = 5
        else:
            scores['health_liquidity'] = 10

        # Calculate total score
        total_score = sum(scores.values())
        max_score = 30 + 25 + 25 + 20  # Maximum possible

        normalized_score = (total_score / max_score) * 100

        # Rating
        if normalized_score >= 80:
            rating = 'Excellent'
        elif normalized_score >= 65:
            rating = 'Good'
        elif normalized_score >= 50:
            rating = 'Fair'
        elif normalized_score >= 35:
            rating = 'Poor'
        else:
            rating = 'Very Poor'

        return {
            'total_score': round(normalized_score, 2),
            'rating': rating,
            'max_score': 100,
            'components': {
                'valuation': round((scores.get('valuation_pe', 0) + scores.get('valuation_pb', 0)) / 60 * 100, 2),
                'profitability': round(scores.get('profitability_roe', 0) / 25 * 100, 2),
                'growth': round((scores.get('growth_revenue', 0) + scores.get('growth_profit', 0)) / 50 * 100, 2),
                'financial_health': round((scores.get('health_debt', 0) + scores.get('health_liquidity', 0)) / 40 * 100, 2),
            },
            'details': {
                'valuation_pe': scores.get('valuation_pe', 0),
                'valuation_pb': scores.get('valuation_pb', 0),
                'profitability_roe': scores.get('profitability_roe', 0),
                'growth_revenue': scores.get('growth_revenue', 0),
                'growth_profit': scores.get('growth_profit', 0),
                'health_debt': scores.get('health_debt', 0),
                'health_liquidity': scores.get('health_liquidity', 0),
            },
        }

    @staticmethod
    async def full_business_analysis(symbol: str) -> Dict[str, Any]:
        """Perform complete business analysis."""
        fundamentals = await FundamentalAnalyzer.fetch_company_fundamentals(symbol)
        scoring = FundamentalAnalyzer.score_fundamentals(fundamentals)

        return {
            'symbol': symbol,
            'fundamentals': fundamentals,
            'scoring': scoring,
            'timestamp': datetime.utcnow().isoformat(),
        }


# Singleton instance
fundamental_analyzer = FundamentalAnalyzer()
