from modularodm import Q


PREREG_CAMPAIGNS = {
    'prereg': 'Prereg Challenge',
}


def drafts_for_user(user, campaign):
    from osf.models import DraftRegistration, Node

    PREREG_CHALLENGE_METASCHEMA = get_prereg_schema(campaign)
    return DraftRegistration.objects.filter(
        registration_schema=PREREG_CHALLENGE_METASCHEMA,
        approval=Node.load(None),
        registered_node=Node.load(None),
        branched_from__in=Node.objects.filter(
            is_deleted=False,
            contributor__admin=True,
            contributor__user=user).values_list('id', flat=True))


def get_prereg_schema(campaign='prereg'):
    from osf.models import MetaSchema
    if campaign not in PREREG_CAMPAIGNS:
        raise ValueError('campaign must be one of: {}'.format(', '.join(PREREG_CAMPAIGNS.keys())))
    schema_name = PREREG_CAMPAIGNS[campaign]

    return MetaSchema.find_one(
        Q('name', 'eq', schema_name) &
        Q('schema_version', 'eq', 2)
    )
