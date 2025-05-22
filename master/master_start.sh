#! /bin/bash

gunicorn -w 1 -b 0.0.0.0:8000 master:app --daemon --pid gunicorn.pid