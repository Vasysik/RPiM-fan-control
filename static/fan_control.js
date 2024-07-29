let fanSpeed = 0;
let isStarting = false;
let isStopping = false;
let currentRotation = 0;
let lastTimestamp = 0;

function updateFanRotation(timestamp) {
    const fanImage = document.getElementById('fan-image');
    
    if (isStarting) {
        fanSpeed += 0.5;
        if (fanSpeed >= 20) {
            isStarting = false;
        }
    } else if (isStopping) {
        fanSpeed -= 0.05;
        if (fanSpeed <= 0) {
            isStopping = false;
            fanSpeed = 0;
        }
    }

    if (lastTimestamp !== 0) {
        const deltaTime = timestamp - lastTimestamp;
        currentRotation += (fanSpeed * deltaTime) / 16;
    }

    fanImage.style.transform = `rotate(${currentRotation}deg)`;
    
    lastTimestamp = timestamp;

    if (fanSpeed > 0 || isStarting || isStopping) {
        requestAnimationFrame(updateFanRotation);
    }
}

function updateCurrentStatus() {
    fetch('/fan_control/api/current')
        .then(response => response.json())
        .then(data => {
            document.getElementById('current-temperature').textContent = data.temperature + '°C';
            document.getElementById('fan-state').textContent = data.fan_state === 0 ? "Off" : "On";
            document.getElementById('rpm').textContent = data.rpm;
            
            if (data.fan_state === 1 && !isStarting && fanSpeed === 0) {
                isStarting = true;
                isStopping = false;
                lastTimestamp = 0;
                requestAnimationFrame(updateFanRotation);
            } else if (data.fan_state === 0 && !isStopping && fanSpeed > 0) {
                isStopping = true;
                isStarting = false;
            }
        })
        .catch(error => console.error('Error:', error));
}

function loadSettings() {
    fetch('/fan_control/api/settings')
        .then(response => response.json())
        .then(settings => {
            document.getElementById('tempOn').value = settings.tempOn;
            document.getElementById('tempOff').value = settings.tempOff;
            document.getElementById('mode').value = settings.mode;
        })
        .catch(error => console.error('Error:', error));
}

function saveSettings() {
    const settings = {
        tempOn: document.getElementById('tempOn').value,
        tempOff: document.getElementById('tempOff').value,
        mode: document.getElementById('mode').value
    };

    fetch('/fan_control/api/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            console.log('Settings updated successfully');
        } else {
            alert('Error updating settings');
        }
    })
    .catch(error => console.error('Error:', error));
}

function updateGraph() {
    const graphType = document.getElementById('graph-type').value;
    const timeRange = document.getElementById('time-range').value;

    fetch(`/fan_control/api/graph_data?type=${graphType}&range=${timeRange}`)
        .then(response => response.json())
        .then(data => {
            const traceOn = {
                x: [],
                y: [],
                type: 'scatter',
                mode: 'lines',
                name: `${graphType} (Fan On)`,
                line: {color: 'lightblue', width: 2},
                connectgaps: false
            };

            const traceOff = {
                x: [],
                y: [],
                type: 'scatter',
                mode: 'lines',
                name: `${graphType} (Fan Off)`,
                line: {color: '#3a8cc5', width: 2},
                connectgaps: false
            };

            for (let i = 0; i < data.timestamps.length; i++) {
                const currentState = data.fan_state[i];
                const currentValue = data[graphType][i];
                const currentTime = data.timestamps[i];

                if (currentState === 1 ) {
                    traceOn.x.push(currentTime);
                    traceOn.y.push(currentValue);
                    if (i > 0 && data.fan_state[i-1] === 0) {
                        traceOn.x.push(data.timestamps[i]);
                        traceOn.y.push(data[graphType][i]);
                        traceOff.x.push(currentTime);
                        traceOff.y.push(currentValue);
                    }
                    traceOff.x.push(currentTime);
                    traceOff.y.push(null);
                } else {
                    traceOff.x.push(currentTime);
                    traceOff.y.push(currentValue);
                    if (i > 0 && data.fan_state[i-1] === 1) {
                        traceOff.x.push(data.timestamps[i]);
                        traceOff.y.push(data[graphType][i]);
                        traceOn.x.push(currentTime);
                        traceOn.y.push(currentValue);
                    }
                    traceOn.x.push(currentTime);
                    traceOn.y.push(null);
                }
            }

            const layout = {
                title: graphType === 'temperature' ? 'Temperature Graph' : 'RPM Graph',
                xaxis: {
                    title: 'Time',
                    color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim()
                },
                yaxis: {
                    title: graphType === 'temperature' ? 'Temperature (°C)' : 'RPM',
                    color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim()
                },
                paper_bgcolor: getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim(),
                plot_bgcolor: getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim(),
                font: {
                    color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim()
                },
                margin: {l: 50, r: 50, b: 50, t: 50, pad: 4},
                showlegend: true,
                legend: {
                    x: 1,
                    xanchor: 'right',
                    y: 1
                },
                dragmode: false,
                displayModeBar: false
            };

            Plotly.newPlot('graph', [traceOn, traceOff], layout, {responsive: true, displayModeBar: false});
        })
        .catch(error => console.error('Error:', error));
}

// Добавим функцию для обновления темы графика
function updateGraphTheme() {
    const graphDiv = document.getElementById('graph');
    if (graphDiv && graphDiv.data && graphDiv.layout) {
        const update = {
            'paper_bgcolor': getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim(),
            'plot_bgcolor': getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim(),
            'font.color': getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim(),
            'xaxis.color': getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim(),
            'yaxis.color': getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim()
        };
        Plotly.relayout(graphDiv, update);
    }
}

// Добавим слушатель изменения темы
if (window.matchMedia) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addListener(updateGraphTheme);
}

setInterval(updateCurrentStatus, 1000);
setInterval(updateGraph, 1000);

window.onload = function() {
    updateCurrentStatus();
    loadSettings();
    updateGraph();
};