#!/bin/bash
gunicorn -w 2 -b 0.0.0.0:$PORT --timeout 120 api:app
