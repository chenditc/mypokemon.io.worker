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

REDIS_HOST = os.environ.get('REDIS_HOST', 'mypokemon-io.qha7wz.ng.0001.usw2.cache.amazonaws.com')
redis_client = redis.StrictRedis(host=REDIS_HOST, port=6379, db=0)

SQS_QUEUE_NAME = os.environ.get("SQS_QUEUE_NAME", "awseb-e-h66tqvpuym-stack-AWSEBWorkerQueue-1X04PKYR2KY9D")
work_queue = boto3.resource('sqs', region_name='us-west-2').get_queue_by_name(QueueName=SQS_QUEUE_NAME)


def get_cell_ids_from_rect(data):
    west = float(data["west"])
    north = float(data["north"])
    east = float(data["east"])
    south = float(data["south"])
    target = data["target"]

    p1 = s2sphere.LatLng.from_degrees(north, west); 
    p2 = s2sphere.LatLng.from_degrees(south, east);
    rect = s2sphere.LatLngRect.from_point_pair(p1, p2)
    area = rect.area() * 1000 * 1000

    # If area is too large, do nothing
    if area > 0.85:
        return []

    cover = s2sphere.RegionCoverer()
    cover.max_cells = 200
    cover.max_level = 15
    cover.min_level = 15
    if target == "pokemon" and area < 0.015:
        cover.min_level = 16
        cover.max_level = 16
    cells = cover.get_covering(rect)

    cell_ids = [ cell.id() for cell in cells ]
    return cell_ids

def filter_duplciate_cell_ids(cell_ids):
    redis_query = [ "request.{0}".format(cell_id) for cell_id in cell_ids ]
    cell_exist = redis_client.mget(redis_query)
    new_cell_ids = []
    for index in range(len(cell_ids)):
        if cell_exist[index] == None:
            new_cell_ids.append(cell_ids[index])
            redis_client.setex(redis_query[index], 60, '1')
    return new_cell_ids

def query(request):
    try:
        data = json.loads(request.body) 

        if isinstance(data, dict):
            cell_ids = get_cell_ids_from_rect(data)
            if len(cell_ids) == 0:
                return HttpResponse("Too large, not process.")

            # validate it against redis
            cell_ids = filter_duplciate_cell_ids(cell_ids)
            if len(cell_ids) == 0:
                return HttpResponse("Nothing to do")
        else:
            cell_ids = data

    except:
        logging.getLogger('worker').error("Fail to parse cellid from {0}".format(data))
        logging.getLogger('worker').error(str(sys.exc_info()))
        return HttpResponseBadRequest("Fail to parse cellid from {0}".format(data))

    # If cell id size is greater than 20, break it down to smaller pieces and resend to queue
    queue_name = request.META['HTTP_X_AWS_SQSD_QUEUE']
    if len(cell_ids) > 10:
        for i in range(0, len(cell_ids), 5):
            smaller_cells = cell_ids[i:i+5]
            work_queue.send_message(MessageBody=json.dumps(smaller_cells))
        return HttpResponse("Redistributed cells")

    worker = CellWorker()
    fail_count = worker.query_cell_ids(cell_ids)
    # If 80% of cell failed, return bad response
    if fail_count > 0:
        return HttpResponseBadRequest("Some cell failed. Total fail count: {0}".format(fail_count))
    return HttpResponse("OK")

def activate(request):
    poll_email_and_process()
    return HttpResponse("OK")

