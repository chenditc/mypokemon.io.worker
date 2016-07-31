import psycopg2
import requests
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()


import re
import os
import sys
import poplib

from pokemon_fort_db import PokemonFortDB

def poll_email_and_process():
    if os.environ.get("ENV") == "DEV":
        return

    pop_conn = poplib.POP3_SSL('pop.gmail.com')
    try:
        db = PokemonFortDB()

        pop_conn.user('mypokemon.io419')
        pop_conn.pass_('Mypokemon.io')
        poplist = pop_conn.list()
        if poplist[0].startswith('+OK') :
            for index in range(1, min(len(poplist[1])+1, 40) ):
                message = pop_conn.retr(index)
                message = "\n".join(message[1])

                match = re.search(r'(searchfort\d+)', message)
                if match == None:
                    continue
                username = match.groups()[0]
                link = re.search(r'(https://club.pokemon.com/us/pokemon-trainer-club/activated/.*)"', message).groups()[0] 
                response = requests.get(link)
                if response.status_code == 200:
                    db.add_searcher(username)
                    print "Added user:", username
                    pop_conn.dele(index)

                    print "Deleted message id:", index
                else:
                    print "Failed to activate:", username
        else:
            print "Could not connect to server"
    finally:
        print "exiting"
        pop_conn.quit()

if __name__ == "__main__":
    while True:
        poll_email_and_process()
