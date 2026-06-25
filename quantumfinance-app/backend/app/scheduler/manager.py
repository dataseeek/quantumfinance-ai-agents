"""APScheduler bootstrap. Sticks jobs in DB and exposes start/stop."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.scheduler.jobs import ingest_news_job, ingest_cvm_job, run_crew_job
from app.db.base import SessionLocal
from app.db.models import Setting


_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=settings.database_url)},
            timezone="America/Sao_Paulo",
        )
    return _scheduler


def _cron_from_setting(key: str, default: str) -> str:
    db = SessionLocal()
    try:
        s = db.get(Setting, key)
        if s and isinstance(s.value, dict):
            return s.value.get("cron", default)
        return default
    finally:
        db.close()


def configure_jobs():
    s = get_scheduler()
    # Remove existing app jobs
    for jid in ("news", "cvm", "crew"):
        try:
            s.remove_job(jid)
        except Exception:
            pass
    news_cron = _cron_from_setting("news_ingest_cron", "0 */4 * * 1-5")
    crew_cron = _cron_from_setting("crew_run_cron",   "30 9 * * 1-5")
    cvm_cron  = _cron_from_setting("cvm_ingest_cron", "0 6 * * 0")
    s.add_job(ingest_news_job, CronTrigger.from_crontab(news_cron), id="news", replace_existing=True)
    s.add_job(run_crew_job,    CronTrigger.from_crontab(crew_cron), id="crew", replace_existing=True)
    s.add_job(ingest_cvm_job,  CronTrigger.from_crontab(cvm_cron),  id="cvm",  replace_existing=True)


def start():
    s = get_scheduler()
    configure_jobs()
    if not s.running:
        s.start()


def stop():
    s = get_scheduler()
    if s.running:
        s.shutdown(wait=False)
