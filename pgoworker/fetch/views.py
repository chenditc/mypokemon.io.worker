from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest

import pogo_client


def health(request):
    data = request.GET
    if 'cellid' not in data:
        return HttpResponseBadRequest("No cellid specified")

    try:
        cellid = int(data['cellid'])
    except:
        return HttpResponseBadRequest("Fail to parse cellid from {0}".format(data))


    rcode = pogo_client.query_cellid(cellid)

    if rcode != 0:
        return HttpResponseBadRequest("Failed to query cell id, rcode {0}".format(rcode))
    return HttpResponse("OK")
