#!/bin/bash
sudo service privoxy restart
sudo service tor restart
python /src/manage.py runserver 00.0.0.0:8080

