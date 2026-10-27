import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        data = {
            "servis": "Order Servisi",
            "siparisler": ["Siparis #101", "Siparis #102"],
            "calisilan_ic_port": os.getenv("PORT")
        }
        self.wfile.write(json.dumps(data).encode('utf-8'))

port = int(os.getenv("PORT", 5002))

server = HTTPServer(('0.0.0.0', port), Handler)
server.serve_forever()