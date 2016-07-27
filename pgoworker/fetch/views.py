import logging
import json

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest

from pogo_client import CellWorker

def query(request):
    try:
        cell_ids = json.loads(request.body) 
        cell_ids = [ int(cell_id) for cell_id in cell_ids ]
    except:
        logging.getLogger('worker').info("Fail to parse cellid from {0}".format(data))
        return HttpResponseBadRequest("Fail to parse cellid from {0}".format(data))

    if len(cell_ids) == 0:
        return HttpResponse("Nothing to do")

    # Filter the ones that already refreshed
    worker = CellWorker()
    for cell_id in cell_ids:
        rcode = worker.query_cellid(cell_id)
        if rcode != 0:
            logging.getLogger('worker').info("Failed to query cell id {0}, rcode {1}".format(cell_id, rcode))
            return HttpResponseBadRequest("Failed to query cell id, rcode {0}".format(rcode))
    return HttpResponse("OK")
