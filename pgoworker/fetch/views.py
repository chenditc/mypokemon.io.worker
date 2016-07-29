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
    fail_count = worker.query_cell_ids(cell_ids)
    # If 80% of cell failed, return bad response
    if fail_count > (len(cell_ids) * 0.8):
        return HttpResponseBadRequest("Too many failed cell. Total fail count: {0}".format(fail_count))
    return HttpResponse("OK")
