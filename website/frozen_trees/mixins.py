class FreezerSafe(object):
    def __init__(self):
        if not self.freezer_schema:
            raise NotImplementedError('You must specify a freezer_schema.')

    def freeze(self):
        schema = self.freezer_schema()
        result = schema.dump(self)
        return result.data
