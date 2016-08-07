import time
import os
import math

import psycopg2
import s2sphere

class PokemonFortDB(object):
    def __init__(self):
        rds_host = os.environ.get("RDS_HOST","pokemon-fort-dev.cafr6s1nfibs.us-west-2.rds.amazonaws.com" )
        rds_user = os.environ.get("RDS_USER", "pokemon_fort")
        rds_password = os.environ.get("RDS_PASSWORD", "pokemon_fort")
        rds_database = os.environ.get("RDS_DATABASE", "pokemon_fort_dev")

        self.conn = psycopg2.connect(host=rds_host, 
                                     port=5432, 
                                     user=rds_user,
                                     password=rds_password,
                                     database=rds_database)

############################################################################################################
# Crawl API 
############################################################################################################

    def add_fort(self, fortid, cellid, enabled, latitude, longitude, lure_expire=0, forttype=None, gymteam=None):
        now = time.time()
        cur = self.conn.cursor()
        cur.execute("INSERT INTO fort_map (fortid, cellid, enabled, latitude, longitude, forttype, gymteam, lure_expire, last_update)" +  
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)" +
                    " ON CONFLICT (fortid) DO UPDATE SET gymteam = EXCLUDED.gymteam, lure_expire = EXCLUDED.lure_expire, last_update = EXCLUDED.last_update;", 
            (fortid, cellid, enabled, latitude, longitude, forttype, gymteam, lure_expire, now))

    def mark_search(self, cellid):
        now = time.time()
        cur = self.conn.cursor()
        cur.execute("INSERT INTO map_search_record (timestamp, cellid) " + 
                    " VALUES (%s, %s) ON CONFLICT (cellid) DO NOTHING", (now, cellid)) 
        self.conn.commit()


    def add_spawn_points(self, cellid, spawn_points):
        now = time.time()
        # Check if this cell already exists
        cur = self.conn.cursor()
        cur.execute("SELECT count(cellid) FROM spawn_point_map WHERE cellid=%s limit 1", (str(cellid),))
        count = cur.fetchone()[0]
        if count != 0:
            return

        for point in spawn_points:
            # Round to 200 feet
            latitude = math.ceil(point["latitude"] * 2000) / 2000
            longitude = math.ceil(point["longitude"] * 2000) / 2000
            cur = self.conn.cursor()
            cur.execute("INSERT INTO spawn_point_map (cellid, latitude, longitude, last_check)" +  
                        " VALUES (%s, %s, %s, %s) ON CONFLICT (latitude, longitude) DO NOTHING",
                (cellid, latitude, longitude, now))
        self.conn.commit()

    def get_first_spawn_point(self, cellid):
        cur = self.conn.cursor()
        cur.execute("SELECT latitude, longitude FROM spawn_point_map WHERE cellid=%s limit 1", (str(cellid),))
        records = cur.fetchall()
        if len(records) == 0:
            return None
        else:
            return (records[0][0], records[0][1], 0)


    def add_pokemon(self, encounter_id, expire, pokemon_id, latitude, longitude):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO pokemon_map (encounter_id, expire, pokemon_id, latitude, longitude)" +  
                    " VALUES (%s, %s, %s, %s, %s)" +
                    " ON CONFLICT (encounter_id, expire, pokemon_id, latitude, longitude) DO NOTHING",
            (encounter_id, expire, pokemon_id, latitude, longitude))
        self.conn.commit()

    def get_search_cellids(self, limit=200):
        now = time.time()
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT(map_visit_record.cellid) " +  
                    " FROM map_visit_record, map_search_record" + 
                    " WHERE map_visit_record.timestamp > %s" +  # Visited last hour
                        " AND map_search_record.timestamp < %s" +   # Didn't update last minute
                        " AND map_search_record.cellid = map_visit_record.cellid " +
                    " LIMIT %s", (now - 3600, now - 60, limit))
        rows = cur.fetchall()
        result = [ int(row[0]) for row in rows ]
        return result


############################################################################################################
# Web API 
############################################################################################################



    def cell_exists(self, cellid):
        cur = self.conn.cursor()
        cur.execute("SELECT count(*) FROM fort_map WHERE cellid=%s", (str(cellid),))
        number = cur.fetchone()[0]
        return number > 0


    def query_forts(self, west, north, east, south):
        self.add_map_visit_record(west, north, east, south)

        cur = self.conn.cursor()
        cur.execute("SELECT latitude, longitude, forttype, gymteam FROM fort_map " + 
                    "WHERE longitude > %s " + 
                        "and longitude < %s " + 
                        "and latitude > %s " + 
                        "and latitude < %s " +
                     "ORDER BY fortid limit 200",
                (west, east, south, north))
        rows = cur.fetchall()
        forts = []
        for row in rows:
            forts.append({ "latitude": row[0],
                              "longitude" : row[1],
                              "forttype" : row[2],
                              "gymteam" : row[3]
                            })
        return forts

    def add_map_visit_record(self, west, north, east, south):
        # Only add when area is smaller than 0.85 / 1000 / 1000
        p1 = s2sphere.LatLng.from_degrees(north, west); 
        p2 = s2sphere.LatLng.from_degrees(south, east);
        rect = s2sphere.LatLngRect.from_point_pair(p1, p2)
        area = rect.area() * 1000 * 1000
        if area > 0.85:
            return

        cover = s2sphere.RegionCoverer()
        cover.max_cells = 10000
        cover.max_level = 15
        cover.min_level = 15
        cells = cover.get_covering(rect)

        now = time.time()
        cur = self.conn.cursor()

        for cell in cells: 
            cur.execute("INSERT INTO map_visit_record (timestamp, cellid)" +  
                        " VALUES (%s, %s)", (now, cell.id()))
            cur.execute("INSERT INTO map_search_record (timestamp, cellid)" +  
                        " VALUES (%s, %s) " +
                        " ON CONFLICT (cellid) DO NOTHING ", (0, cell.id()))
        self.conn.commit()
        return



############################################################################################################
# utility
############################################################################################################

    def get_searcher_account(self):
        cur = self.conn.cursor()
        cur.execute("SELECT username, password, logininfo " +  
                    " FROM searcher_account" + 
                    " ORDER BY RANDOM()" +  # Visited last hour
                    " LIMIT 1")
        username, password, logininfo = cur.fetchone()
        return (username, password, logininfo) 

    def update_searcher_account_login_info(self, username, logininfo):
        cur = self.conn.cursor()
        cur.execute("UPDATE searcher_account " + 
                    " SET logininfo = %s, " + 
                    " lastused = %s " + 
                    " WHERE username = %s;", (logininfo, time.time(), username))
        self.conn.commit()

    def add_searcher(self, username):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO searcher_account (username, password, lastused, failcount)" +  
                    " VALUES (%s, %s, %s, %s)" +
                    " ON CONFLICT (username) DO NOTHING",
            (username, username, 0, 0))
        self.conn.commit()

    def get_all_searcher_account(self):
        cur = self.conn.cursor()
        cur.execute("SELECT username " +  
                    " FROM searcher_account")
        rows = cur.fetchall()
        usernames = [ row[0] for row in rows]
        return usernames 




    def commit(self):
        self.conn.commit()

