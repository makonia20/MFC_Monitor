import sys
import os
import time
import json
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import serial
import serial.tools.list_ports

# Global State
latest_data = {
    "status": "Disconnected",
    "port": None,
    "timestamp": 0,
    "raw_v": 0.0,
    "amp_v": 0.0,
    "calc_v": 0.0
}
forced_port = None

# Determine web directory depending on PyInstaller or normal script
if getattr(sys, 'frozen', False):
    web_dir = os.path.join(sys._MEIPASS, 'web_dashboard')
else:
    web_dir = os.path.join(os.path.dirname(__file__), 'web_dashboard')

def get_available_ports():
    return [p.device for p in serial.tools.list_ports.comports()]

def auto_detect_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        if any(k in desc for k in ["cp210", "ch340", "ftdi", "uart", "usb serial"]):
            return p.device
    if ports:
        return ports[0].device
    return None

def serial_reader_thread():
    global latest_data, forced_port
    
    while True:
        port_to_use = forced_port if forced_port else auto_detect_port()
        
        if not port_to_use:
            latest_data["status"] = "No Device Found"
            latest_data["port"] = None
            time.sleep(2)
            continue
            
        try:
            with serial.Serial(port_to_use, 115200, timeout=2) as ser:
                latest_data["status"] = "Connected"
                latest_data["port"] = port_to_use
                
                while True:
                    # Break to reconnect if the user forced a different port
                    if forced_port and forced_port != port_to_use:
                        break
                    # Break to auto-detect if the user cleared the forced port
                    if not forced_port and port_to_use != auto_detect_port() and auto_detect_port() is not None:
                         pass # stay connected until physically broken

                    try:
                        line = ser.readline().decode("utf-8", errors="ignore").strip()
                        if not line or line.startswith("=") or line.startswith("Time"):
                            continue

                        parts = [p.strip() for p in line.split(",")]
                        if len(parts) >= 4:
                            try:
                                latest_data["timestamp"] = int(parts[0])
                                latest_data["raw_v"] = float(parts[1])
                                latest_data["amp_v"] = float(parts[2])
                                latest_data["calc_v"] = float(parts[3])
                            except ValueError:
                                pass # ignore lines that are not valid numbers (like boot logs)
                    except serial.SerialException:
                        break # break inner loop to reconnect only on physical disconnect
                        
        except serial.SerialException as e:
            err_msg = str(e).lower()
            if "access is denied" in err_msg or "permission" in err_msg:
                latest_data["status"] = "PORT BLOCKED! Close Arduino IDE / Other apps"
            else:
                latest_data["status"] = "Disconnected"
            latest_data["port"] = port_to_use
            time.sleep(2)
        except Exception as e:
            latest_data["status"] = "Disconnected"
            latest_data["port"] = port_to_use
            time.sleep(2)

class APIRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=web_dir, **kwargs)
        
    def do_GET(self):
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(latest_data).encode('utf-8'))
            
        elif parsed_url.path == '/api/ports':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(get_available_ports()).encode('utf-8'))
            
        elif parsed_url.path == '/api/connect':
            global forced_port
            query = parse_qs(parsed_url.query)
            if 'port' in query and query['port'][0] != "":
                forced_port = query['port'][0]
            else:
                forced_port = None # reset to auto-detect
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "port": forced_port}).encode('utf-8'))
            
        else:
            super().do_GET()
            
    def log_message(self, format, *args):
        # Mute logging to keep terminal clean
        pass

def start_server():
    # Bind to an ephemeral port or standard port
    port = 8055
    server = HTTPServer(('127.0.0.1', port), APIRequestHandler)
    print(f"Serving MFC App on http://127.0.0.1:{port}")
    server.serve_forever()

def main():
    print("Starting MFC Hardware Service...")
    
    # Start serial reader
    t_serial = threading.Thread(target=serial_reader_thread, daemon=True)
    t_serial.start()
    
    # Start web server
    t_web = threading.Thread(target=start_server, daemon=True)
    t_web.start()
    
    # Open browser automatically
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:8055")
    
    print("Application is running. Keep this window open.")
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()
