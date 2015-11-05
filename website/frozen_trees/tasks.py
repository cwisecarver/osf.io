import celery
from celery.utils import log
from celery.utils.log import get_task_logger
from framework.auth import User

from framework.tasks import app as celery_app
from framework.tasks.utils import logged
from website.archiver.tasks import create_app_context
from website.frozen_trees import signals as frozen_tree_signals

class FrozenTreeTask(celery.Task):
    abstract = True


@celery_app.task(base=FrozenTreeTask, name='frozen_trees.build_user_tree')
@logged('build_user_tree')
def build_user_tree(user_id):
    user = User.load(user_id)



