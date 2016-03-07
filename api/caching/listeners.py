from functools import partial

from api.caching.tasks import ban_object_instances_from_varnish
from framework.tasks.postcommit_handlers import enqueue_postcommit_task
from modularodm import signals


@signals.save.connect
def log_object_saved(sender, instance, fields_changed, cached_data):
    abs_url = None
    url_pattern_of_type = []
    if hasattr(instance, 'absolute_api_v2_url'):
        abs_url = instance.absolute_api_v2_url

    if hasattr(instance,'_name'):
        url_pattern_of_type.append('/v2/{}s/$'.format(instance._name))
        url_pattern_of_type.append('/v2/.*{}s/$'.format(instance._name))

    if abs_url is not None:
        enqueue_postcommit_task(partial(ban_object_instances_from_varnish, abs_url, url_pattern_of_type))
