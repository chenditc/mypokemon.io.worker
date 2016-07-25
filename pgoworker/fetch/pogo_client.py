#!/usr/bin/env python
"""
pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.

Author: tjado <https://github.com/tejado>
"""

import os
import re
import sys
import json
import time
import struct
import math
import pprint
import logging
import requests
import argparse
import getpass

import redis

# add directory of this file to PATH, so that the package will be found
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util

# other stuff
from google.protobuf.internal import encoder
from geopy.geocoders import GoogleV3
from s2sphere import Cell, CellId, LatLng
import s2sphere

import pokemon_fort_db 


log = logging.getLogger(__name__)
db = pokemon_fort_db.PokemonFortDB()
redis_client = redis.StrictRedis(host='mypokemon-io.qha7wz.ng.0001.usw2.cache.amazonaws.com', port=6379, db=0)
api_client = pgoapi.PGoApi()
last_login = 0

POGO_FAILED_LOGIN = -1

def get_cell_ids(lat, long, radius = 10):
    origin = CellId.from_lat_lng(LatLng.from_degrees(lat, long)).parent(15)
    walk = [origin.id()]
    right = origin.next()
    left = origin.prev()

    # Search around provided radius
    for i in range(radius):
        walk.append(right.id())
        walk.append(left.id())
        right = right.next()
        left = left.prev()

    # Return everything
    return sorted(walk)

def get_monitor_list():
    return db.get_search_cellids(50)

def get_position_from_cellid(cellid):
    # Check if there is spawn point, if so, use it as location
    point = db.get_first_spawn_point(cellid)
    if point != None:
        return point

    cell = CellId(id_ = cellid).to_lat_lng()
    return (math.degrees(cell._LatLng__coords[0]), math.degrees(cell._LatLng__coords[1]), 0)
    
def encode(cellid):
    output = []
    encoder._VarintEncoder()(output.append, cellid)
    return ''.join(output)
  
def update_forts(cell_id, forts):
    forts_info = []
    for fort in forts:
        enabled = fort.get('enabled', False)
        forttype = fort.get('type', None)
        gymteam = fort.get('owned_by_team', None)
        lure_expire = 0
        if 'lure_info' in fort:
            lure_expire = fort["lure_info"]["lure_expires_timestamp_ms"]
        db.add_fort(fort['id'], cell_id, enabled, fort['latitude'], fort['longitude'], lure_expire, forttype, gymteam)

        forts_info.append({"latitude" : fort['latitude'],
                           "longitude" : fort["longitude"],
                           "lure" : lure_expire,
                           "gymteam" : gymteam })

    logging.getLogger("search").info("Updated cellid: {0} with {1} forts".format(cell_id, len(forts) ))

   
def query_cellid(cellid):
    # Skip fresh cell
    exist = redis_client.get(cellid)
    if exist != None:
        return 0

    api = get_api() 
    if api == POGO_FAILED_LOGIN:
        return POGO_FAILED_LOGIN

    position = get_position_from_cellid(cellid) 
    api.set_position(*position)

    cell_ids = [cellid] 
    timestamps = [0]
    api.get_map_objects(latitude = util.f2i(position[0]), longitude = util.f2i(position[1]), since_timestamp_ms = timestamps, cell_id = cell_ids)
   
    # execute the RPC call
    response_dict = api.call()
    if 'response' not in response_dict:
        print('Response dictionary: \n\r{}'.format(pprint.PrettyPrinter(indent=2).pformat(response_dict)))



    if ('GET_MAP_OBJECTS' not in response_dict['responses'] or
        'map_cells' not in response_dict['responses']['GET_MAP_OBJECTS']):
        logging.getLogger("search").info("Failed to get map object from cell: {0}",format(cellid)) 
        # Valid scenario because no china data
        return 0

    cells = response_dict['responses']['GET_MAP_OBJECTS']['map_cells']
    assert(len(cell_ids) == len(cells))

    for cell in cells:
        # Set to update every 180 seconds
        redis_client.setex("{0}".format(cell['s2_cell_id']), 30, '1')


        logging.getLogger("search").info(cell.keys())
        # Add pokemon info
        if 'catchable_pokemons' in cell:
            for pokemon in cell['catchable_pokemons']:
                db.add_pokemon(pokemon["encounter_id"], 
                               pokemon["expiration_timestamp_ms"], 
                               pokemon["pokemon_id"], 
                               pokemon["latitude"], 
                               pokemon["longitude"])
            logging.getLogger("search").info("Added {0} pokemons".format(len(cell['catchable_pokemons'])))
        if 'wild_pokemons' in cell:
            for pokemon in cell['wild_pokemons']:
                db.add_pokemon(pokemon["encounter_id"], 
                               pokemon["last_modified_timestamp_ms"] + pokemon["time_till_hidden_ms"], 
                               pokemon["pokemon_data"]["pokemon_id"], 
                               pokemon["latitude"], 
                               pokemon["longitude"])
            logging.getLogger("search").info("Added {0} pokemons".format(len(cell['catchable_pokemons'])))

        if 'spawn_points' in cell:
            db.add_spawn_points(cell['s2_cell_id'], cell['spawn_points'])

        if 'forts' in cell:
            update_forts(cell['s2_cell_id'], cell['forts'])

    db.commit()
    return 0

def refresh_api():
    global api_client
    global last_login
    api_client = pgoapi.PGoApi()
    if not api_client.login("ptc", "fortsearcher1", "fortsearcher1"):
        logging.getLogger("pgoapi").error("Failed to login") 
        return POGO_FAILED_LOGIN;
    last_login = time.time()
    return 0;


# Singlton accessor
def get_api():
    if time.time() - last_login > 1700:
        rcode = refresh_api()
        logging.getLogger("worker").info("Api refreshed")
    return api_client


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("pgoapi").setLevel(logging.INFO)
    logging.getLogger("rpc_api").setLevel(logging.INFO)
    logging.getLogger("search").setLevel(logging.INFO)

    if DEBUG:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)
        logging.getLogger("search").setLevel(logging.DEBUG)

    cellid = 9926585761992278016
    query_cellid(cellid)
    query_cellid(cellid)


if __name__ == '__main__':
    DEBUG = True
    main()
