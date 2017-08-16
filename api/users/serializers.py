from rest_framework import serializers as ser

from modularodm.exceptions import ValidationValueError, ValidationError

from api.base.exceptions import InvalidModelValueError
from api.base.serializers import JSONAPIRelationshipSerializer, HideIfDisabled, BaseAPISerializer
from osf.models import OSFUser

from api.base.serializers import (
    JSONAPISerializer, LinksField, RelationshipField, DevOnly, IDField, TypeField, ListDictField,
    DateByVersion,
)
from api.base.utils import absolute_reverse, get_user_auth


class UserSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'full_name',
        'given_name',
        'middle_names',
        'family_name',
        'id'
    ])
    non_anonymized_fields = ['type']
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    full_name = ser.CharField(source='fullname', required=True, label='Full name', help_text='Display name used in the general user interface')
    given_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    middle_names = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    family_name = ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations')
    suffix = HideIfDisabled(ser.CharField(required=False, allow_blank=True, help_text='For bibliographic citations'))
    date_registered = HideIfDisabled(DateByVersion(read_only=True))
    active = HideIfDisabled(ser.BooleanField(read_only=True, source='is_active'))
    timezone = HideIfDisabled(ser.CharField(required=False, help_text="User's timezone, e.g. 'Etc/UTC"))
    locale = HideIfDisabled(ser.CharField(required=False, help_text="User's locale, e.g.  'en_US'"))
    social = ListDictField(required=False)

    links = HideIfDisabled(LinksField(
        {
            'html': 'absolute_url',
            'profile_image': 'profile_image_url',
        }
    ))

    nodes = HideIfDisabled(RelationshipField(
        related_view='users:user-nodes',
        related_view_kwargs={'user_id': '<_id>'},
        related_meta={'projects_in_common': 'get_projects_in_common'},
    ))

    registrations = DevOnly(HideIfDisabled(RelationshipField(
        related_view='users:user-registrations',
        related_view_kwargs={'user_id': '<_id>'},
    )))

    institutions = HideIfDisabled(RelationshipField(
        related_view='users:user-institutions',
        related_view_kwargs={'user_id': '<_id>'},
        self_view='users:user-institutions-relationship',
        self_view_kwargs={'user_id': '<_id>'},
    ))

    class Meta:
        type_ = 'users'

    def get_projects_in_common(self, obj):
        user = get_user_auth(self.context['request']).user
        if obj == user:
            return user.contributor_to.count()
        return obj.n_projects_in_common(user)

    def absolute_url(self, obj):
        if obj is not Node.load(None):
            return obj.absolute_url
        return Node.load(None)

    def get_absolute_url(self, obj):
        return absolute_reverse('users:user-detail', kwargs={
            'user_id': obj._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def profile_image_url(self, user):
        size = self.context['request'].query_params.get('profile_image_size')
        return user.profile_image_url(size=size)

    def update(self, instance, validated_data):
        assert isinstance(instance, OSFUser), 'instance must be a User'
        for attr, value in validated_data.items():
            if 'social' == attr:
                for key, val in value.items():
                    # currently only profileWebsites are a list, the rest of the social key only has one value
                    if key == 'profileWebsites':
                        instance.social[key] = val
                    else:
                        if len(val) > 1:
                            raise InvalidModelValueError(
                                detail='{} only accept a list of one single value'. format(key)
                            )
                        instance.social[key] = val[0]
            else:
                setattr(instance, attr, value)
        try:
            instance.save()
        except ValidationValueError as e:
            raise InvalidModelValueError(detail=e.message)
        except ValidationError as e:
            raise InvalidModelValueError(e)

        return instance

class UserAddonSettingsSerializer(JSONAPISerializer):
    """
    Overrides UserSerializer to make id required.
    """
    id = ser.CharField(source='config.short_name', read_only=True)
    user_has_auth = ser.BooleanField(source='has_auth', read_only=True)

    links = LinksField({
        'self': 'get_absolute_url',
        'accounts': 'account_links'
    })

    class Meta:
        type_ = 'user_addons'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'users:user-addon-detail',
            kwargs={
                'provider': obj.config.short_name,
                'user_id': self.context['request'].parser_context['kwargs']['user_id'],
                'version': self.context['request'].parser_context['kwargs']['version']
            }
        )

    def account_links(self, obj):
        # TODO: [OSF-4933] remove this after refactoring Figshare
        if hasattr(obj, 'external_accounts'):
            return {
                account._id: {
                    'account': absolute_reverse('users:user-external_account-detail', kwargs={
                        'user_id': obj.owner._id,
                        'provider': obj.config.short_name,
                        'account_id': account._id,
                        'version': self.context['request'].parser_context['kwargs']['version']
                    }),
                    'nodes_connected': [n.absolute_api_v2_url for n in obj.get_attached_nodes(account)]
                }
                for account in obj.external_accounts.all()
            }
        return {}

class UserDetailSerializer(UserSerializer):
    """
    Overrides UserSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class ReadEmailUserDetailSerializer(UserDetailSerializer):

    email = ser.CharField(source='username', read_only=True)


class RelatedInstitution(JSONAPIRelationshipSerializer):
    id = ser.CharField(required=False, allow_null=True, source='_id')
    class Meta:
        type_ = 'institutions'

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url


class UserInstitutionsRelationshipSerializer(BaseAPISerializer):

    data = ser.ListField(child=RelatedInstitution())
    links = LinksField({'self': 'get_self_url',
                        'html': 'get_related_url'})

    def get_self_url(self, obj):
        return absolute_reverse('users:user-institutions-relationship', kwargs={
            'user_id': obj['self']._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def get_related_url(self, obj):
        return absolute_reverse('users:user-institutions', kwargs={
            'user_id': obj['self']._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    class Meta:
        type_ = 'institutions'
