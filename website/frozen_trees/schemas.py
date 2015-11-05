from modularodm import Q
import marshmallow


class BaseSchema(marshmallow.Schema):
    _id = marshmallow.fields.Str()
    type = marshmallow.fields.Str()

    def __init__(self, model=None, process_backrefs=True, depth=1, *args, **kwargs):
        self._process_backrefs = process_backrefs
        self.depth = depth
        self.tab_string = '\t' * depth
        self.type = model
        super(BaseSchema, self).__init__(*args, **kwargs)

    def depth_print(self, huh):
        print '{} {}'.format(self.tab_string, huh)

    @marshmallow.post_dump(pass_many=True, pass_original=True)
    def add_backrefs(self, data, many, original):
        if many:
            return data
        data['type'] = self.type

        if 'is_deleted' in data and data['is_deleted'] == True:
            # self.depth_print('It is deleted')
            return data
        if self._process_backrefs is False:
            # self.depth_print('Told not to process backrefs')
            return data
        if not hasattr(original, '_backrefs_flat'):
            # self.depth_print('No backrefs')
            return data

        self.depth_print('Working on {}'.format(data['_id']))

        from framework import auth
        from website.project import model

        mapping = {
            # "addondataverseusersettings",
            # "addonfigshareusersettings",
            # "addongithubusersettings",
            # "addons3usersettings",
            # "apioauth2application",
            # "apioauth2personaltoken",
            # "boxusersettings",
            'comment': model.Comment,
            # "dropboxusersettings",
            # "embargo",
            # "googledriveusersettings",
            # "mailrecord",
            # "mendeleyusersettings",
            'node': model.Node,
            'nodelog': model.NodeLog,
            # "notificationsubscription",
            # "privatelink",
            # "registrationapproval",
            # "retraction",
            # "twofactorusersettings",
            'user': auth.User,
            # "zoterousersettings"
        }

        by_model = {}
        by_local = {}

        for [local, model, remote], _id in original._backrefs_flat:
            #  loop through all the backrefs making a list by model
            if model not in mapping:
                continue
            if _id == data['_id']:
                #  Self-referential, ignore for now.
                continue
            if model in by_model:
                by_model[model].append(_id)
            else:
                by_model[model] = [_id]
            # and a list by their local property name
            if local in by_local:
                by_local[local].append((model, _id))
            else:
                by_local[local] = [(model, _id)]

        from website.project.model import Freeze

        by_id = {}
        locally_cached_ids = []
        locally_cached_freezes = {}
        for model, id_list in by_model.items():
            #  check to see if frozen models exist in cache
            list_of_ids = map(
                str, list(
                    set(
                        sorted(
                            [
                                '{}:{}'.format(model, id) for id in id_list if id not in locally_cached_ids
                            ]
                        )
                    )
                )
            )
            self.depth_print('Count of freeze ids to look up: {}'.format(list_of_ids))
            frozen_models = Freeze.find(
                Q(
                    '_id', 'in', list_of_ids
                )
            )

            #  store them in local cache by model
            locally_cached_freezes[model] = list(frozen_models)
            self.depth_print('Count of found freeze ids: {}'.format(len(frozen_models)))
            by_id.update({m._id: m.value for m in locally_cached_freezes[model]})
            #  store their ids for referencing in the mongo query
            locally_cached_ids = list(set(locally_cached_ids + [frozen_model._id for frozen_model in frozen_models]))
            self.depth_print('Locally cached ids: {}'.format(locally_cached_ids))
            #  get all the models by Model from mongo
            ids_to_check_mongo_for = map(
                str, list(
                    set(
                        sorted(
                            [
                                id for id in id_list if id not in locally_cached_ids
                                ]
                        )
                    )
                )
            )
            # self.depth_print('Ids to check mongo for: {}'.format(ids_to_check_mongo_for))
            self.depth_print('Count of ids to check mongo for: {}'.format(len(ids_to_check_mongo_for)))
            mongo_instances = mapping[model].find(
                Q(
                    '_id', 'in', ids_to_check_mongo_for
                )
            )
            self.depth_print('Number of instances found: {}'.format(len(mongo_instances)))
            #  { <_id>: [<model_freeze>, ], ... }
            by_id.update({
                m._id: m.freeze(model=model)
                #  using list to force the queryset to be evaluated in one mongo query instead of lazily
                for m in list(
                        mongo_instances
                    )
                }
            )

            self.depth_print('Delta of ids: {}'.format(list(set(ids_to_check_mongo_for)-set(locally_cached_ids))))


        # properties = {}
        # for prop, model_id in by_local.items():
        #      # reorder the model instances by local property name
        #      # { <property_name>: [<frozen_model>, ], ... }
        #     for model, _id in model_id:
        #         if prop in properties:
        #             print prop, model, _id
        #             # properties[prop].append(by_id[_id].freeze(process_backrefs=False))
        #         else:
        #             print prop, model, _id
        #             # properties[prop] = [by_id[_id].freeze(process_backrefs=False), ]
        #
        # obj.update(properties)
        self.depth_print(locally_cached_freezes)
        return data


class CommentSchema(BaseSchema):
    content = marshmallow.fields.Str()
    is_deleted = marshmallow.fields.Boolean()
    modified = marshmallow.fields.Boolean()
    date_created = marshmallow.fields.DateTime()
    date_modified = marshmallow.fields.DateTime()
    reports = marshmallow.fields.Raw()


class UserSchema(BaseSchema):
    fullname = marshmallow.fields.Str()
    given_name = marshmallow.fields.Str()
    middle_names = marshmallow.fields.Str()
    family_name = marshmallow.fields.Str()
    suffix = marshmallow.fields.Str()
    merged_by = marshmallow.fields.Nested('self')
    is_registered = marshmallow.fields.Boolean()
    is_claimed = marshmallow.fields.Boolean()
    system_tags = marshmallow.fields.Str(many=True)
    security_messages = marshmallow.fields.Raw()
    is_invited = marshmallow.fields.Boolean()
    unclaimed_records = marshmallow.fields.Raw()


class RetractionSchema(BaseSchema):
    initiated_by = marshmallow.fields.Nested(UserSchema(process_backrefs=False))
    justification = marshmallow.fields.Str()


class EmbargoSchema(BaseSchema):
    initiated_by = marshmallow.fields.Nested(UserSchema)
    for_existing_registration = marshmallow.fields.Boolean()

class NodeSchema(BaseSchema):

    # @marshmallow.pre_dump
    # def print_id(self, data):
    #
    #     if data.is_deleted:
    #         return None
    #     else:
    #         return data


    retraction = marshmallow.fields.Nested(RetractionSchema)
    embargo = marshmallow.fields.Nested(EmbargoSchema)
    creator = marshmallow.fields.Nested(UserSchema(process_backrefs=False))
    contributors = marshmallow.fields.Nested(UserSchema, many=True)
    users_watching_node = marshmallow.fields.Nested(UserSchema, many=True)
    tags = marshmallow.fields.Raw()
    logs = marshmallow.fields.Nested('NodeLogSchema', many=True, exclude=('user'))

    title = marshmallow.fields.Str()
    primary = marshmallow.fields.Boolean()
    description = marshmallow.fields.Str()
    category = marshmallow.fields.Str()
    is_fork = marshmallow.fields.Boolean()
    forked_date = marshmallow.fields.DateTime()
    is_registration = marshmallow.fields.Boolean()
    is_public = marshmallow.fields.Boolean()
    is_deleted = marshmallow.fields.Boolean()
    wiki_pages_current = marshmallow.fields.Raw()
    wiki_pages_versions = marshmallow.fields.Raw()
    wiki_pages_uuids = marshmallow.fields.Raw()
    # file_guid_to_share_uuids = marshmallow.fields.Raw()
    is_retracted = marshmallow.fields.Boolean()
    date_created = marshmallow.fields.DateTime()
    visible_contributor_ids = marshmallow.fields.Str(many=True)
    is_dashboard = marshmallow.fields.Boolean()
    is_folder = marshmallow.fields.Boolean()
    comment_level = marshmallow.fields.Str()



class NodeLogSchema(BaseSchema):
    date = marshmallow.fields.DateTime()
    action = marshmallow.fields.Str()
    params = marshmallow.fields.Raw()
    should_hide = marshmallow.fields.Boolean()
    was_connected_to = marshmallow.fields.Nested(NodeSchema(process_backrefs=False), many=True)
    user = marshmallow.fields.Nested(UserSchema(process_backrefs=False))
    foreign_user = marshmallow.fields.Str()
