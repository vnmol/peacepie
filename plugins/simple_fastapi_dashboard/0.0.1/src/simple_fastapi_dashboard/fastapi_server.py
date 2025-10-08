import os
import uvicorn

from fastapi import FastAPI
from fastapi.responses import FileResponse

from . import zmq_client

class FastapiServer:

    def __init__(self, zmq_port, serializer_spec):
        self.zmq_client = zmq_client.ZMQClient(zmq_port, serializer_spec)


def run_server(port, zmq_port, serializer_spec):
    server = FastapiServer(zmq_port, serializer_spec)
    app = FastAPI()

    @app.get("/")
    def read_root():
        return {"message": f'Hello from FastAPI Actor!'}

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(f'{os.path.dirname(__file__)}/resources/static/favicon.ico')

    @app.get("/actors")
    def get_actors():
        return {"actors": []}

    uvicorn.run(app, host="0.0.0.0", port=port)
