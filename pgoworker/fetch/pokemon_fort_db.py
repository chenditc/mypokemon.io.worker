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
        self.max_account = os.environ.get("MAX_ACCOUNT", "zzzz")


        self.conn = psycopg2.connect(host=rds_host, 
                                     port=5432, 
                                     user=rds_user,
                                     password=rds_password,
                                     database=rds_database)

############################################################################################################
# Crawl API 
############################################################################################################

    def add_fort(self, fortid, cellid, enabled, latitude, longitude, lure_expire=0, forttype=None, gymteam=None):
        try:
            now = time.time()
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO fort_map (fortid, cellid, enabled, latitude, longitude, forttype, gymteam, lure_expire, last_update)" +  
                            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)" +
                            " ON CONFLICT (fortid) DO UPDATE SET gymteam = EXCLUDED.gymteam, lure_expire = EXCLUDED.lure_expire, last_update = EXCLUDED.last_update;", 
                    (fortid, cellid, enabled, latitude, longitude, forttype, gymteam, lure_expire, now))
            self.commit()
        except:
            self.conn.rollback()


    def add_spawn_points(self, cellid, spawn_points):
        now = time.time()
        # Check if this cell already exists
        with self.conn.cursor() as cur:
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
        self.commit()


    def get_first_spawn_point(self, cellid):
        with self.conn.cursor() as cur:
            cur.execute("SELECT latitude, longitude FROM spawn_point_map WHERE cellid=%s limit 1", (str(cellid),))
            records = cur.fetchall()
            if len(records) == 0:
                return None
            else:
                return (records[0][0], records[0][1], 0)


    def add_pokemon(self, encounter_id, expire, pokemon_id, latitude, longitude):
        if expire > 1473173782526:
            return

        try:
            with self.conn.cursor() as cur:
                cur.execute("INSERT INTO pokemon_map (encounter_id, expire, pokemon_id, latitude, longitude)" +  
                            " VALUES (%s, %s, %s, %s, %s)" +
                            " ON CONFLICT (encounter_id, expire, pokemon_id, latitude, longitude) DO NOTHING",
                    (encounter_id, expire, pokemon_id, latitude, longitude))
            self.commit()
        except:
            self.conn.rollback()






############################################################################################################
# Web API 
############################################################################################################



    def cell_exists(self, cellid):
        with self.conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM fort_map WHERE cellid=%s", (str(cellid),))
            number = cur.fetchone()[0]
            return number > 0


    def query_forts(self, west, north, east, south):
        with self.conn.cursor() as cur:
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



############################################################################################################
# utility
############################################################################################################

    def get_searcher_account(self):
        try:
            with self.conn.cursor() as cur:
                # not used for last 5seconds
                cur.execute("SELECT username, password, logininfo " +  
                            " FROM searcher_account" + 
                            #                            " WHERE username='searchfort40537' " +
                            " WHERE username < %s " + 
                            " ORDER BY RANDOM()" +  # Visited last hour
                            " LIMIT 1", (self.max_account,))
                username, password, logininfo = cur.fetchone()
                return (username, password, logininfo) 
            self.commit()
        except:
            self.conn.rollback()


    def update_searcher_account_login_info(self, username, logininfo):
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE searcher_account " + 
                            " SET logininfo = %s, " + 
                            " lastused = %s " + 
                            " WHERE username = %s;", (logininfo, time.time(), username))
            self.commit()
        except:
            self.conn.rollback()



    def clear_searcher_account_login_info(self, username):
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE searcher_account " + 
                            " SET logininfo = NULL " + 
                            " WHERE username = %s;", (username,))
            self.commit()
        except:
            self.conn.rollback()


    def add_searcher(self, username):
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO searcher_account (username, password, lastused, failcount)" +  
                        " VALUES (%s, %s, %s, %s)" +
                        " ON CONFLICT (username) DO NOTHING",
                (username, username, 0, 0))
        self.commit()


    def get_all_searcher_account(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT username " +  
                        " FROM searcher_account")
            rows = cur.fetchall()
            usernames = [ row[0] for row in rows]
            return usernames 
        self.commit()

    def commit(self):
        self.conn.commit()

