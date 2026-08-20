"""Task scheduler for Liara application."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


class TaskScheduler:
    """Manages scheduled tasks for system monitoring."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
    
    def add_interval_task(self, func, seconds: int, task_id: str):
        """Add a task that runs at specified intervals."""
        self.scheduler.add_job(
            func,
            trigger=IntervalTrigger(seconds=seconds),
            id=task_id,
            replace_existing=True
        )


scheduler = TaskScheduler()
