import json
import logging
import urlparse

from django.http import HttpResponse

from openquake.engine.db import models as oqe_models

METHOD_NOT_ALLOWED = 405
JSON = 'application/json'

IGNORE_FIELDS = ('base_path', 'export_dir', 'owner')
GEOM_FIELDS = ('region', 'sites', 'region_constraint', 'sites_disagg')
RISK_INPUTS = ('hazard_calculation', 'hazard_output')

LOGGER = logging.getLogger('openquakeserver')


def calc_hazard(request):
    """
    The following request types are supported:

        * GET: List hazard calculations.

    Responses are in JSON.
    """
    if not request.method == 'GET':
        return HttpResponse(status=METHOD_NOT_ALLOWED)

    if request.is_secure():
        base_url = 'https://%s'
    else:
        base_url = 'http://%s'
    base_url %= request.META['HTTP_HOST']

    base_url = 'http://%s' % request.META['HTTP_HOST']

    haz_calc_data = _get_haz_calcs()

    response_data = []
    for hc_id, status, desc in haz_calc_data:
        url = urlparse.urljoin(base_url, 'calc/hazard/%d' % hc_id)
        response_data.append(
            dict(id=hc_id, status=status, description=desc, url=url)
        )

    return HttpResponse(content=json.dumps(response_data),
                        content_type=JSON)


def _get_haz_calcs():
    return oqe_models.OqJob.objects\
        .select_related()\
        .filter(hazard_calculation__isnull=False)\
        .values_list('hazard_calculation',
                     'status',
                     'hazard_calculation__description')


def calc_hazard_info(request, calc_id):
    if not request.method == 'GET':
        return HttpResponse(status=METHOD_NOT_ALLOWED)

    response_data = _get_haz_calc_info(calc_id)

    return HttpResponse(content=json.dumps(response_data), content_type=JSON)


def _get_haz_calc_info(calc_id):
    job = oqe_models.OqJob.objects\
        .select_related()\
        .get(hazard_calculation=calc_id)

    hc = job.hazard_calculation
    response_data = _calc_to_response_data(hc)

    response_data['status'] = job.status
    return response_data


def _calc_to_response_data(calc):
    """
    Extract the calculation parameters into a dictionary.
    """
    fields = [x.name for x in calc._meta.fields if x.name not in IGNORE_FIELDS]
    response_data = {}
    for field_name in fields:
        try:
            value = getattr(calc, field_name)
            if value is not None:
                if field_name in GEOM_FIELDS:
                    response_data[field_name] = json.loads(value.geojson)
                elif field_name in RISK_INPUTS:
                    response_data[field_name] = value.id
                else:
                    response_data[field_name] = value
        except AttributeError:
            # Better that we miss an attribute than crash.
            pass
    return response_data


def calc_risk(request):
    """
    The following request types are supported:

        * GET: List risk calculations.

    Responses are in JSON.
    """
    if not request.method == 'GET':
        return HttpResponse(status=METHOD_NOT_ALLOWED)

    if request.is_secure():
        base_url = 'https://%s'
    else:
        base_url = 'http://%s'
    base_url %= request.META['HTTP_HOST']

    risk_calc_data = _get_risk_calcs()

    response_data = []
    for hc_id, status, desc in risk_calc_data:
        url = urlparse.urljoin(base_url, 'calc/risk/%d' % hc_id)
        response_data.append(
            dict(id=hc_id, status=status, description=desc, url=url)
        )

    return HttpResponse(content=json.dumps(response_data),
                        content_type=JSON)


def _get_risk_calcs():
    return oqe_models.OqJob.objects\
        .select_related()\
        .filter(risk_calculation__isnull=False)\
        .values_list('risk_calculation',
                     'status',
                     'risk_calculation__description')


def calc_risk_info(request, calc_id):
    if not request.method == 'GET':
        return HttpResponse(status=METHOD_NOT_ALLOWED)

    response_data = _get_risk_calc_info(calc_id)

    return HttpResponse(content=json.dumps(response_data), content_type=JSON)


def _get_risk_calc_info(calc_id):
    job = oqe_models.OqJob.objects\
        .select_related()\
        .get(risk_calculation=calc_id)

    rc = job.risk_calculation
    response_data = _calc_to_response_data(rc)

    response_data['status'] = job.status
    return response_data
