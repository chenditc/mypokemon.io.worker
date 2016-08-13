import logging
import json
import sys
import os

import s2sphere
import redis
import boto3
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest

from pogo_client import CellWorker
from activate_account import poll_email_and_process
from break_down_request import break_down_request

def query(request):
    try:
        data = json.loads(request.body) 
        # If this is a raw event, 
        # break down to smaller request and send back to queue
        if isinstance(data, dict):
            result = break_down_request(data)
            return HttpResponse(result)
        else:
            cell_ids = data
    except:
        logging.getLogger('worker').error("Fail to parse cellid from {0}".format(request.body))
        logging.getLogger('worker').error(str(sys.exc_info()))
        return HttpResponseBadRequest("Fail to parse cellid from {0}".format(request.body))

    worker = CellWorker()
    fail_count = worker.query_cell_ids(cell_ids)
    if fail_count > 0:
        return HttpResponseBadRequest("Some cell failed. Total fail count: {0}".format(fail_count))
    return HttpResponse("OK")

def activate(request):
    poll_email_and_process()
    return HttpResponse("OK")

def warm_up(request):
    # Warm up mahattan area
    request = {"east" : -73.9542,
                "south" : 40.7352,
                "north" : 40.7728,
                "west" : -74.0082,
                "target" : "pokemon"}
    break_down_request(request, optional=True)

    request = {"east" : -73.927908,
                "south" : 40.766194,
                "north" : 40.8094077,
                "west" : -73.9937221,
                "target" : "pokemon"}
    break_down_request(request, optional=True)

    request = {"east" : -73.9798333,
                "south" : 40.7014576,
                "north" : 40.740863,
                "west" : -74.080372,
                "target" : "pokemon"}
    break_down_request(request, optional=True)


    logging.getLogger('worker').info("Wram up request done")

    return HttpResponse("OK")
