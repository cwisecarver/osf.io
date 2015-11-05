

class FreezerSafe(object):
    def __init__(self):
        if not self.freezer_schema:
            raise NotImplementedError('You must specify a freezer_schema.')

    def freeze(self, model=None, depth=1, process_backrefs=True):
        from website.project.model import Freeze

        schema = self.freezer_schema(model=model, depth=depth, process_backrefs=process_backrefs)
        result = schema.dump(self)
        # print result.data
        if not model:
            type = result.data['type']
        else:
            type = model
        freeze_id = '{}:{}'.format(type, result.data['_id'])
        freeze_instance = Freeze.load(key=freeze_id)
        if freeze_instance:
            freeze_instance.update_fields(value=result.data)
            print "!!!!!!!!!!!!!!!!!!!!!!!!!!!\nUpdated freeze {}\n!!!!!!!!!!!!!!!!!!!!!!!!!!!".format(freeze_id)
        else:
            freeze_instance = Freeze(_id=freeze_id, value=result.data)
            print "!!!!!!!!!!!!!!!!!!!!!!!!!!!\nCreated freeze {}\n!!!!!!!!!!!!!!!!!!!!!!!!!!!".format(freeze_id)
        freeze_instance.save()
        return result.data
