#!/bin/bash
#sudo service privoxy restart
#sudo service tor restart
echo "Starting ssh tunnel"
ssh -o StrictHostKeyChecking=no -D 8123 -f -C -q -N mypokemonio@$myproxy
echo "Starting django server"
exit
python /src/manage.py runserver 0.0.0.0:8080
