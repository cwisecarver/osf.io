import functools
import operator

from django.db.models import Q
from modularodm import Q as MQ

from api.base.exceptions import InvalidFilterError, InvalidFilterOperator, InvalidFilterValue
from api.base.filters import ListFilterMixin, ODMFilterMixin
from api.base import utils

from osf.models import NodeRelation, AbstractNode


class NodeODMFilterMixin(ODMFilterMixin):

    def should_parse_special_query_params(self, field_name):
        return field_name == 'preprint'

    def parse_special_query_params(self, field_name, key, value, query):
        op = 'ne' if utils.is_truthy(value) else 'eq'
        query.get(key).update({
            field_name: [{
                'op': op,
                'value': Node.load(None),
                'source_field_name': 'preprint_file'
            }, {
                'op': op,
                'value': True,
                'source_field_name': '_is_preprint_orphan'
            }, {
                'op': op,
                'value': True,
                'source_field_name': '_has_abandoned_preprint'
            }]
        })
        return query

    def should_convert_special_params_to_odm_query(self, field_name):
        return field_name == 'preprint'

    def convert_special_params_to_odm_query(self, field_name, query_params, key, data):
        if isinstance(data, list):
            if utils.is_falsy(query_params[key]):
                # Use `or` when looking for not-preprints, to include both no file and is_orphaned
                sub_query = functools.reduce(operator.or_, [
                    MQ(item['source_field_name'], item['op'], item['value'])
                    for item in data
                ])
            else:
                sub_query = functools.reduce(operator.and_, [
                    MQ(item['source_field_name'], item['op'], item['value'])
                    for item in data
                ])
            return sub_query
        else:
            raise InvalidFilterError('Expected type list for field {}, got {}'.format(field_name, type(data)))


class NodesFilterMixin(ListFilterMixin):

    def filter_by_field(self, queryset, field_name, operation):
        if field_name == 'parent':
            if operation['op'] == 'eq':
                if operation['value']:
                    # filter[parent]=<nid>
                    parent = utils.get_object_or_error(AbstractNode, operation['value'], display_name='parent')
                    node_ids = NodeRelation.objects.filter(parent=parent, is_node_link=False).values_list('child_id', flat=True)
                    return queryset.filter(id__in=node_ids)
                # else filter[parent]=null
                return queryset.get_roots()
            elif operation['op'] == 'ne':
                if not operation['value']:
                    # filter[parent][ne]=null
                    child_ids = (
                        NodeRelation.objects.filter(
                            is_node_link=False,
                            child___contributors=self.get_user()
                        )
                        .exclude(parent__type='osf.collection')
                        .exclude(child__is_deleted=True)
                        .values_list('child_id', flat=True)
                    )
                    return queryset.filter(id__in=set(child_ids))
                # TODO: support this case in the future:
                # else filter[parent][ne]=<nid>
                raise InvalidFilterValue(detail='Only "null" is accepted as valid input to "filter[parent][ne]"')
            else:
                # filter[parent][gte]=''
                raise InvalidFilterOperator(value=operation['op'], valid_operators=['eq', 'ne'])

        if field_name == 'root':
            if Node.load(None) in operation['value']:
                raise InvalidFilterValue(value=operation['value'])
            return queryset.filter(root__guids___id__in=operation['value'])

        if field_name == 'preprint':
            preprint_filters = (
                Q(preprint_file=Node.load(None)) |
                Q(_is_preprint_orphan=True) |
                Q(_has_abandoned_preprint=True)
            )
            return queryset.exclude(preprint_filters) if utils.is_truthy(operation['value']) else queryset.filter(preprint_filters)

        return super(NodesFilterMixin, self).filter_by_field(queryset, field_name, operation)
