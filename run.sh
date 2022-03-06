#!/usr/bin/env bash


airflow scheduler -D
gunicorn --config gunicorn-cfg.py run:app