"""
FINTEL Market Data Pipeline
============================
Downloads historical stock prices and computes forward returns
for insider transactions.

Uses yfinance for market data.
"""
import logging
from datetime import date, timedelta
from typing import Optional
import pandas as pd
from sqlalchemy import text

from models.database import SessionLocal

logger = logging.getLogger(__name__)


def fetch_price_history(ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Download historical OHLCV data using yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        df = t.history(start=str(start_date), end=str(end_date), auto_adjust=True)
        df.index = pd.to_datetime(df.index).date
        return df
    except Exception as e:
        logger.warning(f"Failed to fetch price history for {ticker}: {e}")
        return pd.DataFrame()


def get_forward_return(
    prices: pd.DataFrame,
    buy_date: date,
    days: int,
) -> Optional[float]:
    """
    Compute forward return from buy_date over `days` calendar days.
    Returns fractional return (e.g., 0.05 = 5%).
    """
    try:
        available_dates = sorted(prices.index)
        if not available_dates:
            return None

        # Find nearest trading day >= buy_date
        buy_dates = [d for d in available_dates if d >= buy_date]
        if not buy_dates:
            return None
        entry_date = buy_dates[0]
        entry_price = float(prices.loc[entry_date, "Close"])

        # Target date
        target_date = buy_date + timedelta(days=days)
        exit_dates = [d for d in available_dates if d >= target_date]
        if not exit_dates:
            return None
        exit_date = exit_dates[0]
        exit_price = float(prices.loc[exit_date, "Close"])

        return (exit_price - entry_price) / entry_price
    except Exception:
        return None


def run_market_data_pipeline():
    """
    Main market data pipeline:
    1. Download price history for all companies
    2. Store in stock_prices table
    3. Compute forward returns for all insider buys lacking outcomes
    """
    db = SessionLocal()
    total_prices = 0
    total_outcomes = 0

    logger.info("Starting market data pipeline...")

    try:
        run_id = db.execute(text("""
            INSERT INTO pipeline_runs (pipeline, status)
            VALUES ('market_data', 'running') RETURNING id
        """)).scalar()
        db.commit()

        # 1. Download recent prices for all companies
        companies = db.execute(text(
            "SELECT id, ticker FROM companies ORDER BY market_cap DESC NULLS LAST"
        )).fetchall()

        end_date = date.today()
        start_date = end_date - timedelta(days=5 * 365)

        for company_id, ticker in companies:
            df = fetch_price_history(ticker, start_date, end_date)
            if df.empty:
                continue

            # Upsert prices
            for price_date, row in df.iterrows():
                try:
                    db.execute(text("""
                        INSERT INTO stock_prices (company_id, date, open, high, low, close, adj_close, volume)
                        VALUES (:company_id, :date, :open, :high, :low, :close, :adj_close, :volume)
                        ON CONFLICT (company_id, date) DO UPDATE
                            SET close = EXCLUDED.close, adj_close = EXCLUDED.adj_close
                    """), {
                        "company_id": company_id,
                        "date": price_date,
                        "open": float(row.get("Open", 0)) or None,
                        "high": float(row.get("High", 0)) or None,
                        "low": float(row.get("Low", 0)) or None,
                        "close": float(row["Close"]),
                        "adj_close": float(row["Close"]),
                        "volume": int(row.get("Volume", 0)) or None,
                    })
                    total_prices += 1
                except Exception as e:
                    logger.debug(f"Price insert error {ticker} {price_date}: {e}")

            db.commit()
            logger.info(f"Loaded {len(df)} price rows for {ticker}")

        # 2. Compute forward returns for insider buys lacking outcomes
        pending_q = text("""
            SELECT
                it.id AS transaction_id,
                c.ticker,
                it.transaction_date,
                it.transaction_value
            FROM insider_transactions it
            JOIN companies c ON c.id = it.company_id
            LEFT JOIN insider_trade_outcomes ito ON ito.transaction_id = it.id
            WHERE it.transaction_type IN ('Buy', 'Purchase')
              AND ito.transaction_id IS NULL
              AND it.transaction_date <= CURRENT_DATE - INTERVAL '7 days'
            LIMIT 5000
        """)
        pending = db.execute(pending_q).fetchall()
        logger.info(f"Computing forward returns for {len(pending)} transactions")

        # Also fetch SPY for benchmark
        spy_df = fetch_price_history("SPY", start_date, end_date)

        for tx_id, ticker, tx_date, tx_value in pending:
            prices = db.execute(text("""
                SELECT date, close FROM stock_prices sp
                JOIN companies c ON c.id = sp.company_id
                WHERE c.ticker = :ticker
                  AND date >= :start
                ORDER BY date
            """), {"ticker": ticker, "start": tx_date}).mappings().all()

            if not prices:
                continue

            price_df = pd.DataFrame(prices).set_index("date")
            price_df.index = pd.to_datetime(price_df.index).date
            price_df.columns = ["Close"]

            r7 = get_forward_return(price_df, tx_date, 7)
            r30 = get_forward_return(price_df, tx_date, 30)
            r90 = get_forward_return(price_df, tx_date, 90)
            r1y = get_forward_return(price_df, tx_date, 365)
            r2y = get_forward_return(price_df, tx_date, 730)

            # Benchmark (SPY)
            b7 = get_forward_return(spy_df.rename(columns={"Close": "Close"}), tx_date, 7) if not spy_df.empty else None
            b30 = get_forward_return(spy_df, tx_date, 30) if not spy_df.empty else None
            b90 = get_forward_return(spy_df, tx_date, 90) if not spy_df.empty else None
            b1y = get_forward_return(spy_df, tx_date, 365) if not spy_df.empty else None

            a30 = (r30 - b30) if r30 and b30 else None
            a90 = (r90 - b90) if r90 and b90 else None
            a1y = (r1y - b1y) if r1y and b1y else None

            try:
                db.execute(text("""
                    INSERT INTO insider_trade_outcomes
                        (transaction_id, return_7d, return_30d, return_90d, return_1y, return_2y,
                         benchmark_return_7d, benchmark_return_30d, benchmark_return_90d, benchmark_return_1y,
                         alpha_30d, alpha_90d, alpha_1y)
                    VALUES
                        (:tx_id, :r7, :r30, :r90, :r1y, :r2y,
                         :b7, :b30, :b90, :b1y, :a30, :a90, :a1y)
                    ON CONFLICT (transaction_id) DO UPDATE
                        SET return_30d = EXCLUDED.return_30d,
                            return_1y = EXCLUDED.return_1y,
                            alpha_30d = EXCLUDED.alpha_30d
                """), {
                    "tx_id": tx_id, "r7": r7, "r30": r30, "r90": r90, "r1y": r1y, "r2y": r2y,
                    "b7": b7, "b30": b30, "b90": b90, "b1y": b1y,
                    "a30": a30, "a90": a90, "a1y": a1y,
                })
                total_outcomes += 1
            except Exception as e:
                logger.warning(f"Outcome insert failed for tx {tx_id}: {e}")

        db.commit()

        db.execute(text("""
            UPDATE pipeline_runs
            SET status='success', ended_at=NOW(), records_processed=:n
            WHERE id=:id
        """), {"n": total_prices + total_outcomes, "id": run_id})
        db.commit()

        logger.info(f"Market data pipeline complete: {total_prices} prices, {total_outcomes} outcomes")

    except Exception as e:
        logger.error(f"Market data pipeline failed: {e}")
        try:
            db.execute(text("""
                UPDATE pipeline_runs SET status='failed', ended_at=NOW(), error_message=:err
                WHERE id=:id
            """), {"err": str(e), "id": run_id})
            db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
