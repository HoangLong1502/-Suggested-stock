from celery import Celery

app = Celery(
    'worker',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/1',
)

app.conf.task_routes = {
    'backend.app.services.agent_orchestrator.*': {'queue': 'agents'},
}
