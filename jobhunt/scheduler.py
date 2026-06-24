import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_scheduler = None

def start_global_sync_scheduler(engine):
    global _scheduler
    
    # Simple check to avoid duplicate schedulers if running multiple workers in some WSGI servers
    if os.environ.get("RUN_MAIN") == "true":
        return

    _scheduler = BackgroundScheduler()
    
    def run_scheduled_sync():
        from jobhunt.scanning import scan_target_companies
        
        # Open a dedicated, isolated background database session
        with Session(engine) as session:
            try:
                logger.info("Starting background sync for target companies.")
                scan_target_companies(session)
                session.commit()
                logger.info("Background sync completed successfully.")
            except Exception as e:
                session.rollback()
                logger.error(f"Background sync failed: {e}")

    _scheduler.add_job(run_scheduled_sync, 'interval', hours=6, id='global_ats_sync')
    _scheduler.start()
    print("⏰ Unified Background ATS Sync initialized successfully.")

def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
