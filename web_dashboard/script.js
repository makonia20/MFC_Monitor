// Data handling
const MAX_POINTS = 100;
let timeData = [];
let rawVData = [];
let calcVData = [];

// Initialize chart
const ctx = document.getElementById('mfcChart').getContext('2d');
Chart.defaults.color = '#a0a0a0';
Chart.defaults.font.family = 'Inter';

const mfcChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: timeData,
        datasets: [
            {
                label: 'Raw V',
                data: rawVData,
                borderColor: '#00c896',
                borderWidth: 1.5,
                tension: 0.4,
                pointRadius: 0
            },
            {
                label: 'Calc true V',
                data: calcVData,
                borderColor: '#ff6b35',
                borderWidth: 1.5,
                borderDash: [4, 4],
                tension: 0.4,
                pointRadius: 0
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    usePointStyle: true,
                    boxWidth: 8,
                    boxHeight: 8
                }
            }
        },
        scales: {
            x: {
                display: false // Hide x-axis labels
            },
            y: {
                suggestedMin: 0,
                suggestedMax: 0.3,
                grid: {
                    color: '#333333'
                },
                ticks: {
                    callback: function(value) {
                        return value.toFixed(2) + 'V';
                    }
                }
            }
        }
    }
});

// UI Elements
const valRaw = document.getElementById('val-raw');
const valAmp = document.getElementById('val-amp');
const valCalc = document.getElementById('val-calc');
const valStatus = document.getElementById('val-status');
const portBadge = document.getElementById('port-badge');
const oledContent = document.getElementById('oled-content');
const serialOutput = document.getElementById('serial-output');

// Gain Input
const hardwareGainInput = document.getElementById('hardware-gain-input');

async function fetchRealData() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        
        // Update Status
        valStatus.textContent = data.status;
        if (data.status === 'Connected') {
            valStatus.style.color = '#00c896';
            portBadge.textContent = data.port || 'COM?';
        } else if (data.status.includes('BLOCKED')) {
            valStatus.style.color = '#ff003c';
            portBadge.textContent = data.port || 'COM?';
        } else {
            valStatus.style.color = '#ff6b35';
            portBadge.textContent = data.port || '---';
        }
        
        // If not connected or data missing, don't update graphs
        if (data.status !== 'Connected' || !data.timestamp) return;

        // Read the user's amplifier gain from the number input
        let userGain = parseFloat(hardwareGainInput.value) || 1.0;

        let rawV = data.raw_v;
        let ampV = data.amp_v;
        
        // Dynamically calculate the true voltage on the PC side using the UI slider
        // (This overrides the ESP32's hardcoded calculation)
        let calcV = ampV / userGain;
        let ts = data.timestamp;

        // Update UI Cards
        valRaw.textContent = rawV.toFixed(3) + ' V';
        valAmp.textContent = ampV.toFixed(3) + ' V';
        valCalc.textContent = calcV.toFixed(3) + ' V';
        
        // Update OLED
        oledContent.textContent = `-- MFC Voltage --\n-----------------\nRaw: ${rawV.toFixed(3)} V\n\nAmp pin: ${ampV.toFixed(3)} V\nCalc: ${calcV.toFixed(3)} V`;
        
        // Only append if it's new data
        if (timeData.length === 0 || timeData[timeData.length - 1] !== ts) {
            timeData.push(ts);
            rawVData.push(rawV);
            calcVData.push(calcV);
            
            if (timeData.length > MAX_POINTS) {
                timeData.shift();
                rawVData.shift();
                calcVData.shift();
            }
            mfcChart.update();

            // Update Serial Monitor
            const logLine = `${ts}, ${rawV.toFixed(4)}, ${ampV.toFixed(4)}, ${calcV.toFixed(4)}`;
            const div = document.createElement('div');
            div.textContent = logLine;
            serialOutput.appendChild(div);
            
            // Auto-scroll logic
            if (serialOutput.children.length > 50) {
                serialOutput.removeChild(serialOutput.firstChild);
            }
            serialOutput.scrollTop = serialOutput.scrollHeight;
        }

    } catch (e) {
        console.error("Failed to fetch data:", e);
        valStatus.textContent = "Server Offline";
        valStatus.style.color = '#ff6b35';
        portBadge.textContent = 'ERROR';
    }
}

// Start polling loop at 5Hz (200ms)
setInterval(fetchRealData, 200);

// Port Selector Logic
const portSelector = document.getElementById('port-selector');
const btnRefreshPorts = document.getElementById('btn-refresh-ports');

async function loadPorts() {
    try {
        const res = await fetch('/api/ports');
        const ports = await res.json();
        
        const currentSelection = portSelector.value;
        portSelector.innerHTML = '<option value="">Auto-Detect</option>';
        
        ports.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p;
            opt.textContent = p;
            portSelector.appendChild(opt);
        });
        
        if (ports.includes(currentSelection)) {
            portSelector.value = currentSelection;
        }
    } catch (e) {
        console.error(e);
    }
}

btnRefreshPorts.addEventListener('click', loadPorts);
portSelector.addEventListener('change', async (e) => {
    const port = encodeURIComponent(e.target.value);
    await fetch(`/api/connect?port=${port}`);
});

loadPorts();
