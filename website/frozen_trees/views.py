from framework import auth
from modularodm import Q
import time
import json
from framework.transactions.handlers import no_auto_transaction


@no_auto_transaction
def display_tree(user_id):
    start_time = {}
    finish_time = {}
    user_dumps = {}
    diff = {}

    users = auth.User.find(Q('_id', 'eq', 'cuz73'))

    for user in users:
        user_id = user._id
        try:
            start_time[user_id] = int(time.time())
            print '{} Working on user {}'.format(start_time[user_id], user_id)
            user_dump = json.dumps(user.freeze(model='user'), indent=4)
            user_dumps[user_id] = user_dump
        except Exception as ex:
            finish_time[user_id] = int(time.time())
            diff[user_id] = finish_time[user_id] - start_time[user_id]
            import traceback
            traceback.print_exc()
            print 'In {} seconds ... failed to freeze user {} with message {}.'.format(diff[user_id], user_id, ex.message)
        else:
            finish_time[user_id] = int(time.time())
            diff[user_id] = finish_time[user_id] - start_time[user_id]
            print 'In {} seconds ... Froze user {}.'.format(diff[user_id], user_id)

    return {'start_time': start_time, 'finish_time': finish_time, 'diff': diff, 'user_dumps': user_dumps}
