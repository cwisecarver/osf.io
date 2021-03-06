import httplib as http

from framework.exceptions import HTTPError

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from osf.models import Institution

def serialize_institution(inst):
    return {
        'id': inst._id,
        'name': inst.name,
        'logo_path': inst.logo_path,
        'logo_path_rounded_corners': inst.logo_path_rounded_corners,
        'description': inst.description or '',
        'banner_path': inst.banner_path,
    }


def view_institution(inst_id, **kwargs):
    try:
        inst = Institution.find_one(Q('_id', 'eq', inst_id) & Q('is_deleted', 'ne', True))
    except NoResultsFound:
        raise HTTPError(http.NOT_FOUND)
    return serialize_institution(inst)
