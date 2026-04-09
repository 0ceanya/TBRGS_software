"""TBRGS -- Traffic-Based Route Guidance System.

Web application for traffic flow prediction and optimal route finding
using the PEMS-BAY sensor network (325 sensors, Bay Area highways).

Launch:
    python main.py                 # http://localhost:8000
    python main.py --port 8080     # custom port

Dependencies:
    pip install -r requirements.txt
"""

import argparse

import uvicorn

from src.api.app import create_app

app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TBRGS Web Application")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    args = parser.parse_args()

    print(f"Starting TBRGS at http://{args.host}:{args.port}")
    uvicorn.run("main:app", host=args.host, port=args.port, reload=True)
