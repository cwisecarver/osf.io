from modularodm import Q
import marshmallow


class BaseSchema(marshmallow.Schema):
    _id = marshmallow.fields.Str()

    @marshmallow.post_dump(pass_original=True)
    def add_backrefs(self, obj, original_data):
        from framework import auth
        from website.project import model

        mapping = {
            'node': model.Node,
            'user': auth.User,
            'comment': model.Comment
        }

        by_model = {}
        by_local = {}

        for [local, model, remote], _id in original_data._backrefs_flat:
            #  loop through all the backrefs making a list by model
            if model not in mapping:
                continue
            if model in by_model:
                by_model[model].append(_id)
            else:
                by_model[model] = [_id]
            # and a list by their local property name
            if local in by_local:
                by_local[local].append(_id)
            else:
                by_local[local] = [_id]

        by_id = {}
        for model, id_list in by_model.items():
            #  get all the models by Model from mongo

            #  using list to force the queryset to be evaluated in one mongo query instead of lazy
            #  { <_id>: [<model>, ], ... }
            by_id.update({m._id: m for m in list(mapping[model].find(Q('_id', 'in', map(str, list(set(id_list))))))})

        properties = {}
        for prop, id_list in by_local.items():
            #  reorder the model instances by local property name
            #  { <property_name>: [<frozen_model>, ], ... }
            for _id in id_list:
                if prop in properties:
                    properties[prop].append(by_id[_id].freeze())
                else:
                    properties[prop] = [by_id[_id].freeze(), ]
        obj.update(properties)
        return obj


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
    merged_by = marshmallow.fields.Nested('UserSchema')
    is_registered = marshmallow.fields.Boolean()
    is_claimed = marshmallow.fields.Boolean()
    system_tags = marshmallow.fields.Str(many=True)
    security_messages = marshmallow.fields.Raw()
    is_invited = marshmallow.fields.Boolean()
    unclaimed_records = marshmallow.fields.Raw()



class NodeSchema(BaseSchema):
    retraction = marshmallow.fields.Nested('RetractionSchema')
    embargo = marshmallow.fields.Nested('EmbargoSchema')
    # creator = marshmallow.fields.Nested('UserSchema', only='_id')
    # contributors = marshmallow.fields.Nested('UserSchema', many=True)
    # users_watching_node = marshmallow.fields.Nested('UserSchema', many=True)
    # tags = marshmallow.fields.Raw()
    # logs = marshmallow.fields.Raw()


    title = marshmallow.fields.Str()
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
    file_guid_to_share_uuids = marshmallow.fields.Raw()
    is_retracted = marshmallow.fields.Boolean()
    date_created = marshmallow.fields.DateTime()
    visible_contributor_ids = marshmallow.fields.Str(many=True)
    is_dashboard = marshmallow.fields.Boolean()
    is_folder = marshmallow.fields.Boolean()
    comment_level = marshmallow.fields.Str()


class RetractionSchema(BaseSchema):
    initiated_by = marshmallow.fields.Nested('UserSchema')
    justification = marshmallow.fields.Str()

class EmbargoSchema(BaseSchema):
    initiated_by = marshmallow.fields.Nested('UserSchema')
    for_existing_registration = marshmallow.fields.Boolean()
