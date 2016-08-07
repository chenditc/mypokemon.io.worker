import logging
import json
import sys
import os

import s2sphere
import redis
import boto3

logger = logging.getLogger("BreakDownRequest")
logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

logger.info("Loading redis connection")
REDIS_HOST = os.environ.get('REDIS_HOST', 'mypokemonio-dev.qha7wz.0001.usw2.cache.amazonaws.com')
redis_client = redis.StrictRedis(host=REDIS_HOST, port=6379, db=0)

logger.info("Loading sqs connection")
SQS_QUEUE_NAME = os.environ.get("SQS_QUEUE_NAME", "awseb-e-h66tqvpuym-stack-AWSEBWorkerQueue-1X04PKYR2KY9D")
work_queue = boto3.resource('sqs', region_name='us-west-2').get_queue_by_name(QueueName=SQS_QUEUE_NAME)

logger.info("Finihsed intiialization, start serving requests")

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
    if target == "pokemon":
        cover.min_level = 16
        cover.max_level = 16
    else:
        cover.max_level = 15
        cover.min_level = 15

    cells = cover.get_covering(rect)

    cell_ids = [ cell.id() for cell in cells ]
    return cell_ids

def filter_duplciate_cell_ids(cell_ids):
    # validate it against redis
    redis_query = [ "request.{0}".format(cell_id) for cell_id in cell_ids ]
    cell_exist = redis_client.mget(redis_query)
    new_cell_ids = []
    for index in range(len(cell_ids)):
        if cell_exist[index] == None:
            new_cell_ids.append(cell_ids[index])
            redis_client.setex(redis_query[index], 60, '1')
    return new_cell_ids

def break_down_request(request):
    logger.info("Received:{0}".format(request))
    try:
        # Parse cell ids
        cell_ids = get_cell_ids_from_rect(request)
        if len(cell_ids) == 0:
            return "Too large, not process."
        logging.info("{0} cells before filtering".format(len(cell_ids)))

        # Filter duplicate cells
        cell_ids = filter_duplciate_cell_ids(cell_ids)
        logging.info("{0} cells after filtering".format(len(cell_ids)))
    except:
        logger.error("Fail to parse cellid from {0}".format(request))
        logger.error(str(sys.exc_info()))
        return "Fail to parse cellid from {0}".format(request)

    # Send to worker to query
    cnt = 0
    for i in range(0, len(cell_ids), 5):
        smaller_cells = cell_ids[i:i+5]
        cnt += 1
        logger.debug("Cell batch: {0}".format(smaller_cells))
        work_queue.send_message(MessageBody=json.dumps(smaller_cells))
    logger.info("Generated {0} set of cell ids".format(cnt))
    return "Redistributed cells"

if __name__ == "__main__":
    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT)
    logger.setLevel(logging.DEBUG)
    break_down_request(
            {"east" : -73.9542,
             "south" : 40.7352,
             "north" : 40.7728,
             "west" : -74.0082,
             "target" : "pokemon"}
            )
