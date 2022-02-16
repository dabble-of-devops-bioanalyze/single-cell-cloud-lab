import copy
import os
import shutil
import subprocess
from functools import lru_cache

S3_BUCKET = os.environ.get("CELLXGENE_BUCKET")

ANNOTATION_DIR = os.environ.get("ANNOTATION_DIR", os.path.abspath("annotations"))
ANNOTATION_DIR = os.path.join(ANNOTATION_DIR, S3_BUCKET)

@lru_cache(maxsize=10, typed=False)
def sync_dataset_down(dataset):
    t_dataset = copy.deepcopy(dataset)
    if f"s3://{S3_BUCKET}" in t_dataset:
        print("S3 bucket is in dataset")
        t_dataset = t_dataset.replace(f"s3://{S3_BUCKET}", "")
    if t_dataset.startswith("/"):
        t_dataset = t_dataset.replace("/", "", 1)

    os.makedirs(ANNOTATION_DIR, exist_ok=True)
    out = os.path.join(ANNOTATION_DIR, t_dataset)
    up = f"s3://{S3_BUCKET}/{t_dataset}"
    print(f"Dataset: {dataset}")
    print(f"Annotation: {ANNOTATION_DIR}")
    print(f"Up: {up}")
    print(f"Out: {out}")

    command = f"aws s3 cp s3://{S3_BUCKET}/{t_dataset} {out}"
    print(f"Running command: {command}")
    subprocess.run(command, shell=True, capture_output=True, check=True)
    return out, t_dataset
