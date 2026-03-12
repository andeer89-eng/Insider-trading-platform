"""
FINTEL Pipeline Scheduler
=========================
APScheduler-based job runner for all ETL pipelines.

Schedule:
  - SEC Form 4 filings: daily at 06:00 UTC
  - Market data / forward returns: daily at 07:00 UTC
  - Signal scoring: daily at 08:00 UTC
  - Institutional 13F: weekly on Mondays at 09:00 UTC
  - KPI extraction: weekly on Sundays at 02:00 UTC
"""
import logging
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BlockingScheduler(timezone="UTC")


@scheduler.scheduled_job(CronTrigger(hour=6, minute=0))
def job_sec_filings():
    logger.info("Running SEC Form 4 pipeline...")
    from pipelines.sec_pipeline import run_sec_pipeline
    run_sec_pipeline(days_back=2)


@scheduler.scheduled_job(CronTrigger(hour=7, minute=0))
def job_market_data():
    logger.info("Running market data pipeline...")
    from pipelines.market_data_pipeline import run_market_data_pipeline
    run_market_data_pipeline()


@scheduler.scheduled_job(CronTrigger(hour=8, minute=0))
def job_signal_scoring():
    logger.info("Running signal scoring pipeline...")
    from signals.scorer import run_signal_scoring
    run_signal_scoring()


@scheduler.scheduled_job(CronTrigger(day_of_week="mon", hour=9, minute=0))
def job_institutional():
    logger.info("Running institutional 13F pipeline...")
    from pipelines.institutional_pipeline import run_institutional_pipeline
    run_institutional_pipeline()


@scheduler.scheduled_job(CronTrigger(day_of_week="sun", hour=2, minute=0))
def job_kpi_extraction():
    logger.info("Running KPI extraction pipeline...")
    from pipelines.kpi_pipeline import run_kpi_pipeline
    run_kpi_pipeline()


if __name__ == "__main__":
    logger.info("Starting FINTEL pipeline scheduler...")
    logger.info("Scheduled jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  {job.id}: {job.trigger}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
