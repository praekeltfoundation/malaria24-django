from malaria24 import celery_app


@celery_app.task
def test_task():
    return 'hi'
