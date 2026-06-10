"""
MFC Real-Time Serial Plotter
─────────────────────────────
Reads CSV data from ESP32 over USB serial and plots
Raw Voltage and Amplified (back-calculated) Voltage in real time.

Install dependencies:
    pip install pyserial matplotlib

Usage:
    python mfc_plotter.py           # auto-detects port
    python mfc_plotter.py COM3      # specify port (Windows)
    python mfc_plotter.py /dev/ttyUSB0   # Linux/Mac
"""

import sys
import csv
import time
import threading
from collections import deque
from datetime import datetime

import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# ── Config ─────────────────────────────────────────────────
BAUD_RATE    = 115200
MAX_POINTS   = 200          # rolling window of data points
LOG_FILE     = f"mfc_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# ── Data buffers ───────────────────────────────────────────
times     = deque(maxlen=MAX_POINTS)
raw_v     = deque(maxlen=MAX_POINTS)
calc_v    = deque(maxlen=MAX_POINTS)
amp_pin_v = deque(maxlen=MAX_POINTS)

lock = threading.Lock()

def find_port():
    """Auto-detect the ESP32 serial port."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        if any(k in desc for k in ["cp210", "ch340", "ftdi", "uart", "usb serial"]):
            print(f"Auto-detected port: {p.device} ({p.description})")
            return p.device
    if ports:
        print(f"Using first available port: {ports[0].device}")
        return ports[0].device
    raise RuntimeError("No serial port found. Connect your ESP32.")

def serial_reader(port):
    """Background thread: reads serial lines and parses CSV."""
    with open(LOG_FILE, "w", newline="") as logfile:
        writer = csv.writer(logfile)
        writer.writerow(["timestamp_ms", "raw_V", "amp_pin_V", "calc_V"])

        with serial.Serial(port, BAUD_RATE, timeout=2) as ser:
            print(f"Connected to {port} at {BAUD_RATE} baud")
            print(f"Logging to: {LOG_FILE}\n")

            while True:
                try:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if not line or line.startswith("=") or line.startswith("Time"):
                        continue  # skip headers/blank lines

                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) < 4:
                        continue

                    ts   = int(parts[0])
                    rv   = float(parts[1])
                    av   = float(parts[2])
                    cv   = float(parts[3])

                    with lock:
                        times.append(ts / 1000.0)   # convert ms → s
                        raw_v.append(rv)
                        amp_pin_v.append(av)
                        calc_v.append(cv)

                    writer.writerow([ts, rv, av, cv])
                    logfile.flush()

                except (ValueError, IndexError):
                    pass   # skip malformed lines
                except serial.SerialException as e:
                    print(f"Serial error: {e}")
                    break

# ── Plot setup ─────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
fig.suptitle("Microbial Fuel Cell — Real-Time Voltage Monitor", fontsize=13)

line_raw,  = ax1.plot([], [], color="#00c896", linewidth=1.5, label="Raw Voltage (V)")
line_calc, = ax1.plot([], [], color="#ff6b35", linewidth=1.5, linestyle="--", label="Calc. True V (via amp)")
line_amp,  = ax2.plot([], [], color="#4a9eff", linewidth=1.5, label="Amp Pin Voltage (V)")

ax1.set_ylabel("Voltage (V)")
ax1.legend(loc="upper right", fontsize=8)
ax1.grid(True, alpha=0.3)
ax1.set_title("True MFC Voltage")

ax2.set_ylabel("Voltage (V)")
ax2.set_xlabel("Time (s)")
ax2.legend(loc="upper right", fontsize=8)
ax2.grid(True, alpha=0.3)
ax2.set_title("Amplified Channel (at ADC pin)")

plt.tight_layout()

def animate(_frame):
    with lock:
        if len(times) < 2:
            return line_raw, line_calc, line_amp

        t  = list(times)
        rv = list(raw_v)
        av = list(amp_pin_v)
        cv = list(calc_v)

    line_raw.set_data(t, rv)
    line_calc.set_data(t, cv)
    line_amp.set_data(t, av)

    for ax in (ax1, ax2):
        ax.relim()
        ax.autoscale_view()

    return line_raw, line_calc, line_amp

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_port()

    thread = threading.Thread(target=serial_reader, args=(port,), daemon=True)
    thread.start()

    ani = animation.FuncAnimation(fig, animate, interval=200, blit=False, cache_frame_data=False)
    plt.show()

if __name__ == "__main__":
    main()
