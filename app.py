from typing import List

from fastapi import FastAPI, Request
from azure.cosmosdb.table.tableservice import TableService
from azure.storage.queue import QueueClient
from opencensus.ext.fastapi.fastapi_middleware import FastAPIMiddleware
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
from opencensus.trace.span import SpanKind
from opencensus.trace import config_integration
from opencensus.trace.attributes_helper import COMMON_ATTRIBUTES

import os

app = FastAPI()

os.environ['VERIFY_SSL'] = '0'

HTTP_URL = COMMON_ATTRIBUTES['HTTP_URL']
HTTP_STATUS_CODE = COMMON_ATTRIBUTES['HTTP_STATUS_CODE']

instrumentation_key = os.getenv("INSTRUMENTATION_KEY")
@app.middleware("http")
async def middlewareOpencensus(request: Request, call_next):
    tracer = Tracer(
        exporter=AzureExporter(
            connection_string="InstrumentationKey={}".format(instrumentation_key)
        ),
        sampler=ProbabilitySampler(1.0),
    )
    with tracer.span("main") as span:
        span.span_kind = SpanKind.SERVER

        response = await call_next(request)

        tracer.add_attribute_to_current_span(
            attribute_key=HTTP_STATUS_CODE, attribute_value=response.status_code
        )
        tracer.add_attribute_to_current_span(
            attribute_key=HTTP_URL, attribute_value=str(request.url)
        )

    return response

# Replace these with your actual Azure Storage account connection strings
TABLE_CONNECTION_STRING = os.getenv("TABLE_CONNECTION_STRING")
QUEUE_CONNECTION_STRING = os.getenv("QUEUE_CONNECTION_STRING")

def get_table_entries(table_name: str) -> List[dict]:
    table_service = TableService(connection_string=TABLE_CONNECTION_STRING)
    entries = table_service.query_entities(table_name)
    return list(entries)


def get_queue_messages(queue_name: str, num_messages: int = 10) -> List[str]:
    queue_client = QueueClient.from_connection_string(QUEUE_CONNECTION_STRING, queue_name)
    messages = queue_client.receive_messages(messages_per_page=num_messages)
    return [message.content for message in messages]


@app.get("/table/{table_name}", response_model=List[dict])
async def read_table_entries(table_name: str):
    entries = get_table_entries(table_name)
    return entries


@app.get("/queue/{queue_name}", response_model=List[str])
async def read_queue_messages(queue_name: str):
    messages = get_queue_messages(queue_name)
    return messages
