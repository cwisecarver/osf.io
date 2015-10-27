from framework.guid.model import signals as guid_signals

@guid_signals.guid_stored_object_saved.connect
def log_object_saved(sender, guid_stored_object):
    print '#####################################\n'\
          'Signal "{}" caught for {}: {}\n'\
          '#####################################'\
        .format(sender, guid_stored_object._name, guid_stored_object._id)
