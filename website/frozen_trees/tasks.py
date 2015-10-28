import celery
from celery.utils import log
from celery.utils.log import get_task_logger

from framework.tasks import app as celery_app
from framework.tasks.utils import logged
from website.archiver.tasks import create_app_context
from website.frozen_trees import signals as frozen_tree_signals

class FrozenTreeTask(celery.Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
