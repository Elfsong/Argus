#! /bin/bash

gunicorn -w 1 -b 0.0.0.0:8000 backend:app --daemon --pid gunicorn.pid