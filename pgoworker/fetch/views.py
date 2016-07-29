import logging
import json

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest

from pogo_client import CellWorker

def query(request):
    try:
        data = json.loads(request.body) 
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
            return HttpResponse("Too large, no process.")

        cover = s2sphere.RegionCoverer()
        cover.max_cells = 200
        cover.max_level = 15
        cover.min_level = 15
        if target == "pokemon":
            cover.max_level = 16
        cells = cover.get_covering(rect)

        cell_ids = [ cell.id() for cell in cells ]
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
