#!/bin/bash
set -e
service ssh start
exec uvicorn app:app --host 0.0.0.0 --reload
