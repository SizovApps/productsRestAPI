#!/bin/sh

echo "Migrate the Database at startup of project"

# Wait for few minute and run db migraiton
python3 manage.py migrate

python3 manage.py runserver 0.0.0.0:8000