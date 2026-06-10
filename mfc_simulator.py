"""
MFC Real-Time Simulator
─────────────────────────────
Simulates CSV data from an ESP32 and plots
Raw Voltage and Amplified (back-calculated) Voltage in real time.
"""

import time
import threading
import math
import random
from collections import deque

import matplotlib.pyplot as plt
import matplotlib.animation as animation

# ── Config ─────────────────────────────────────────────────
MAX_POINTS   = 200          # rolling window of data points

# ── Data buffers ───────────────────────────────────────────
times     = deque(maxlen=MAX_POINTS)
raw_v     = deque(maxlen=MAX_POINTS)
calc_v    = deque(maxlen=MAX_POINTS)
amp_pin_v = deque(maxlen=MAX_POINTS)

lock = threading.Lock()

def serial_simulator():
    """Background thread: simulates serial lines."""
    start_time = time.time()
    
    while True:
        ts = int((time.time() - start_time) * 1000)
        
        # Simulate MFC voltage: basic sine wave + noise
        t_sec = ts / 1000.0
        # MFC typically generates between 0.3V and 0.8V
        base_v = 0.5 + 0.1 * math.sin(t_sec * 0.2) + random.uniform(-0.01, 0.01)
        
        rv = base_v
        cv = base_v
        
        # Amp pin is the amplified voltage, assuming gain of 5
        av = cv * 5.0
        if av > 3.3: 
            av = 3.3 # simulate rail limit

        with lock:
            times.append(ts / 1000.0)
            raw_v.append(rv)
            amp_pin_v.append(av)
            calc_v.append(cv)

        time.sleep(0.2) # 5Hz update rate

# ── Plot setup ─────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
fig.suptitle("Microbial Fuel Cell — Real-Time Voltage Monitor (SIMULATED)", fontsize=13)

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
    print("Starting MFC Simulation...")
    thread = threading.Thread(target=serial_simulator, daemon=True)
    thread.start()

    ani = animation.FuncAnimation(fig, animate, interval=200, blit=False, cache_frame_data=False)
    plt.show()

if __name__ == "__main__":
    main()
