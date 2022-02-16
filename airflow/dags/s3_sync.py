import subprocess
import os
from airflow import DAG
from airflow.decorators import task
from datetime import datetime, timedelta
from time import sleep

import logging
import shutil
import time
from datetime import datetime
from pprint import pprint

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2021, 1, 1),
    "email": ["airflow@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "schedule_interval": "@once",
}


S3_BUCKET = os.environ.get("CELLXGENE_BUCKET")

ANNOTATION_DIR = os.environ.get("ANNOTATION_DIR", os.path.abspath("annotations"))
ANNOTATION_DIR = os.path.join(ANNOTATION_DIR, S3_BUCKET)

S3_BUCKET = f"s3://{S3_BUCKET}"
SYNC_ENABLED = os.environ.get("SYNC_ENABLED", "False").lower() in ["true", "1", "yes"]

# with DAG("sync_down", catchup=False, default_args=default_args) as sync_down_dag:

#     @task(task_id="sync_down")
#     def sync_down():
#         if SYNC_ENABLED:
#             print(f"Sync enabled.. sync down s3 {S3_BUCKET}-> local {ANNOTATION_DIR}")
#             command = f"aws s3 sync {S3_BUCKET}/ {ANNOTATION_DIR}"
#             print(f"Running command: {command}")
#             subprocess.run(command, shell=True, check=True, capture_output=True)
#         else:
#             print("Sync not enabled. Nothing to do here")

#     sync_down()

with DAG("sync_up", catchup=False, default_args=default_args) as sync_up_dag:

    @task(task_id="sync_up")
    def sync_up():
        if SYNC_ENABLED:

            # make the annotation directory
            print(f"Sync enabled.. sync up local: {ANNOTATION_DIR} with s3 {S3_BUCKET}")

            command = f"mkdir -p {ANNOTATION_DIR}"
            print(f"Running command: {command}")
            subprocess.run(command, shell=True, check=True, capture_output=True)

            while True:
                command = f"aws s3 sync {ANNOTATION_DIR} {S3_BUCKET}"
                print(f"Running command: {command}")
                subprocess.run(command, shell=True, check=True, capture_output=True)
                sleep(5)
        else:
            print("Sync not enabled. Nothing to do here")

    sync_up()

with DAG("sync_test", catchup=False, default_args=default_args) as sync_test_dag:

    @task(task_id="sync_test")
    def sync_test():
        if SYNC_ENABLED:
            print(f"Sync enabled.. sync up local: {ANNOTATION_DIR} with s3 {S3_BUCKET}")
        else:
            print("Sync not enabled. Nothing to do here")

    sync_test()
