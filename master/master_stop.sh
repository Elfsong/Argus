#!/bin/bash

kill -9 $(cat gunicorn.pid)
rm gunicorn.pid