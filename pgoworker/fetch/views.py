import logging
import json

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest

import pogo_client

def health(request):
    try:
        data = json.loads(request.body) 
        cellid = int(data['cellid'])
    except:
        logging.getLogger('worker').info("Fail to parse cellid from {0}".format(data))
        return HttpResponseBadRequest("Fail to parse cellid from {0}".format(data))


    rcode = pogo_client.query_cellid(cellid)

    if rcode != 0:
        logging.getLogger('worker').info("Failed to query cell id {0}".format(data))
        return HttpResponseBadRequest("Failed to query cell id, rcode {0}".format(rcode))
    return HttpResponse("OK")
