// DOM Elements
const videoPlayer = document.getElementById('videoPlayer');
const detectionOverlay = document.getElementById('detectionOverlay');
const playPauseBtn = document.getElementById('playPauseBtn');
const currentTimeDisplay = document.getElementById('currentTime');
const playbackSpeedSelect = document.getElementById('playbackSpeed');
const ctx = detectionOverlay.getContext('2d');

// Initialize video player controls
function initializeVideoControls() {
    playPauseBtn.addEventListener('click', togglePlayPause);
    videoPlayer.addEventListener('timeupdate', updateTime);
    playbackSpeedSelect.addEventListener('change', updatePlaybackSpeed);
    
    // Set initial canvas size
    resizeOverlay();
    window.addEventListener('resize', resizeOverlay);
}

function resizeOverlay() {
    detectionOverlay.width = videoPlayer.clientWidth;
    detectionOverlay.height = videoPlayer.clientHeight;
}

function togglePlayPause() {
    if (videoPlayer.paused) {
        videoPlayer.play();
        playPauseBtn.textContent = 'Pause';
    } else {
        videoPlayer.pause();
        playPauseBtn.textContent = 'Play';
    }
}

function updatePlaybackSpeed() {
    videoPlayer.playbackRate = parseFloat(playbackSpeedSelect.value);
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    seconds = Math.floor(seconds % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function updateTime() {
    currentTimeDisplay.textContent = `${formatTime(videoPlayer.currentTime)} / ${formatTime(videoPlayer.duration)}`;
    drawDetections();
    updateCurrentFrameStats();
}

// Vehicle detection styles with clean outline effects
const vehicleStyles = {
    bicycle: {
        color: '#10B981',  // Emerald color for bicycles
        icon: '🚲'
    },
    car: {
        color: '#3B82F6',
        icon: '🚗'
    },
    truck: {
        color: '#EF4444',
        icon: '🚛'
    },
    bus: {
        color: '#F59E0B',
        icon: '🚌'
    },
    motorcycle: {
        color: '#8B5CF6',
        icon: '🏍️'
    }
};

function drawDetections() {
    ctx.clearRect(0, 0, detectionOverlay.width, detectionOverlay.height);
    
    const currentDetections = detectionData.filter(d => {
        return Math.abs(d.timestamp - videoPlayer.currentTime) < 0.1;
    });
    
    const scaleX = detectionOverlay.width / videoPlayer.videoWidth;
    const scaleY = detectionOverlay.height / videoPlayer.videoHeight;
    
    currentDetections.sort((a, b) => b.confidence - a.confidence);
    
    currentDetections.forEach(detection => {
        const x = detection.bbox_x1 * scaleX;
        const y = detection.bbox_y1 * scaleY;
        const width = (detection.bbox_x2 - detection.bbox_x1) * scaleX;
        const height = (detection.bbox_y2 - detection.bbox_y1) * scaleY;
        const style = vehicleStyles[detection.vehicle_type];
        
        // Draw clean outline with double border effect
        ctx.strokeStyle = style.color;
        ctx.lineWidth = 3;
        ctx.setLineDash([]);
        ctx.strokeRect(x, y, width, height);
        
        // Add animated corner accents
        const time = Date.now() / 1000;
        const cornerLength = 20;
        const pulseEffect = Math.sin(time * 3) * 0.5 + 1.5; // Creates a pulsing effect
        
        ctx.lineWidth = 2 * pulseEffect;
        
        // Draw corners with animation
        const corners = [
            // Top-left
            [[x, y + cornerLength], [x, y], [x + cornerLength, y]],
            // Top-right
            [[x + width - cornerLength, y], [x + width, y], [x + width, y + cornerLength]],
            // Bottom-right
            [[x + width, y + height - cornerLength], [x + width, y + height], [x + width - cornerLength, y + height]],
            // Bottom-left
            [[x + cornerLength, y + height], [x, y + height], [x, y + height - cornerLength]]
        ];
        
        corners.forEach(corner => {
            ctx.beginPath();
            ctx.moveTo(corner[0][0], corner[0][1]);
            ctx.lineTo(corner[1][0], corner[1][1]);
            ctx.lineTo(corner[2][0], corner[2][1]);
            ctx.stroke();
        });
        
        // Draw label with clean outline
        const labelText = `${style.icon} ${detection.vehicle_type} ${(detection.confidence * 100).toFixed(0)}%`;
        ctx.font = '14px Arial';
        const labelWidth = ctx.measureText(labelText).width + 20;
        const labelHeight = 28;
        const labelX = x;
        const labelY = y - labelHeight - 5;
        
        // Draw label outline
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(labelX + 5, labelY);
        ctx.lineTo(labelX + labelWidth - 5, labelY);
        ctx.quadraticCurveTo(labelX + labelWidth, labelY, labelX + labelWidth, labelY + 5);
        ctx.lineTo(labelX + labelWidth, labelY + labelHeight - 5);
        ctx.quadraticCurveTo(labelX + labelWidth, labelY + labelHeight, labelX + labelWidth - 5, labelY + labelHeight);
        ctx.lineTo(labelX + 5, labelY + labelHeight);
        ctx.quadraticCurveTo(labelX, labelY + labelHeight, labelX, labelY + labelHeight - 5);
        ctx.lineTo(labelX, labelY + 5);
        ctx.quadraticCurveTo(labelX, labelY, labelX + 5, labelY);
        ctx.stroke();
        
        // Draw label text
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '14px Arial';
        ctx.textBaseline = 'middle';
        ctx.fillText(labelText, labelX + 10, labelY + labelHeight/2);
        
        // Draw confidence indicator as a simple ring
        const indicatorX = labelX + labelWidth - 15;
        const indicatorY = labelY + labelHeight/2;
        const indicatorRadius = 4;
        
        // Draw progress ring
        ctx.beginPath();
        ctx.arc(indicatorX, indicatorY, indicatorRadius, -Math.PI/2, -Math.PI/2 + (2 * Math.PI * detection.confidence));
        ctx.strokeStyle = detection.confidence > 0.8 ? '#22C55E' : 
                         detection.confidence > 0.6 ? '#F59E0B' : 
                         '#EF4444';
        ctx.lineWidth = 2;
        ctx.stroke();
    });
    
    requestAnimationFrame(drawDetections);
}

// Start animation loop when video loads
videoPlayer.addEventListener('loadedmetadata', () => {
    resizeOverlay();
    requestAnimationFrame(drawDetections);
});

// Statistics and Analysis
function updateCurrentFrameStats() {
    const currentDetections = detectionData.filter(d => {
        return Math.abs(d.timestamp - videoPlayer.currentTime) < 0.1;
    });
    
    const counts = {};
    vehicleTypes.forEach(type => counts[type] = 0);
    currentDetections.forEach(d => counts[d.vehicle_type]++);
    
    const colors = {
        bicycle: 'from-emerald-500 to-emerald-600',
        car: 'from-blue-500 to-blue-600',
        truck: 'from-red-500 to-red-600',
        bus: 'from-yellow-500 to-yellow-600',
        motorcycle: 'from-purple-500 to-purple-600'
    };
    
    document.getElementById('currentStats').innerHTML = Object.entries(counts)
        .map(([type, count]) => `
            <div class="py-3">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-gray-600 font-medium capitalize">${type}</span>
                    <span class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r ${colors[type]}">${count}</span>
                </div>
                <div class="w-full bg-gray-100 rounded-full h-2">
                    <div class="h-2 rounded-full bg-gradient-to-r ${colors[type]}" 
                         style="width: ${(count / Math.max(...Object.values(counts)) * 100) || 0}%">
                    </div>
                </div>
            </div>
        `).join('');
}

function createVehicleDistributionChart() {
    const colors = ['#10B981', '#3B82F6', '#EF4444', '#F59E0B', '#8B5CF6'];
    
    const data = [{
        values: vehicleCounts,
        labels: vehicleTypes.map(t => t.charAt(0).toUpperCase() + t.slice(1)),
        type: 'pie',
        hole: 0.6,
        textinfo: 'label+percent',
        textposition: 'outside',
        automargin: true,
        marker: {
            colors: colors,
            line: {
                color: '#ffffff',
                width: 2
            }
        }
    }];
    
    const layout = {
        showlegend: false,
        margin: { t: 0, l: 0, r: 0, b: 0 },
        height: 300,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)'
    };
    
    const config = {
        displayModeBar: false,
        responsive: true
    };
    
    Plotly.newPlot('vehicleDistribution', data, layout, config);
}

function createTrafficFlowChart() {
    const data = [{
        x: timestamps.map(t => new Date(t * 1000)),
        y: vehicleCountsTime,
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        line: {
            color: '#F59E0B',
            width: 3,
            shape: 'spline'
        },
        fillcolor: 'rgba(245, 158, 11, 0.1)'
    }];
    
    const layout = {
        margin: { t: 10, r: 10, l: 50, b: 40 },
        height: 300,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        xaxis: {
            showgrid: true,
            gridcolor: 'rgba(156, 163, 175, 0.1)',
            zeroline: false,
            tickformat: '%H:%M'
        },
        yaxis: {
            showgrid: true,
            gridcolor: 'rgba(156, 163, 175, 0.1)',
            zeroline: false,
            title: 'Vehicle Count'
        }
    };
    
    const config = {
        displayModeBar: false,
        responsive: true
    };
    
    Plotly.newPlot('trafficFlow', data, layout, config);
}

function updateAnalysisResults() {
    // Update Peak Hours
    document.getElementById('peakHours').innerHTML = `
        <div class="flex flex-col items-center">
            <div class="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-cyan-600">
                ${analysisData.peak_hours.start}
            </div>
            <div class="text-gray-400 font-medium">to</div>
            <div class="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-600 to-blue-600">
                ${analysisData.peak_hours.end}
            </div>
        </div>
    `;
    
    // Update Vehicle Composition
    document.getElementById('vehicleComposition').innerHTML =
        Object.entries(analysisData.vehicle_composition)
            .map(([type, percentage]) => `
                <div class="bg-gray-50 rounded-lg p-3">
                    <div class="flex justify-between items-center mb-2">
                        <span class="text-gray-600 font-medium capitalize">${type}</span>
                        <span class="text-lg font-bold text-gray-800">${percentage.toFixed(1)}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="h-2 rounded-full bg-gradient-to-r from-green-500 to-emerald-500"
                             style="width: ${percentage}%">
                        </div>
                    </div>
                </div>
            `).join('');
    
    // Update Traffic Density
    document.getElementById('trafficDensity').innerHTML = `
        <div class="space-y-4">
            <div class="bg-gray-50 rounded-lg p-4">
                <div class="text-gray-500 text-sm mb-1">Average Density</div>
                <div class="text-2xl font-bold text-gray-800">
                    ${analysisData.traffic_density.average.toFixed(1)}
                    <span class="text-sm font-normal text-gray-500">vehicles/5min</span>
                </div>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
                <div class="text-gray-500 text-sm mb-1">Maximum Density</div>
                <div class="text-2xl font-bold text-gray-800">
                    ${analysisData.traffic_density.maximum}
                    <span class="text-sm font-normal text-gray-500">vehicles/5min</span>
                </div>
            </div>
        </div>
    `;
    
    // Update Concerns
    document.getElementById('concerns').innerHTML =
        analysisData.concerns.map(concern => `
            <div class="bg-red-50 rounded-xl p-4 border border-red-100">
                <h4 class="font-semibold text-red-800 mb-2 flex items-center">
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    ${concern.title}
                </h4>
                <p class="text-gray-700">${concern.description}</p>
            </div>
        `).join('');
    
    // Update Recommendations
    document.getElementById('recommendations').innerHTML =
        analysisData.recommendations.map(rec => `
            <div class="bg-green-50 rounded-xl p-4 border border-green-100">
                <h4 class="font-semibold text-green-800 mb-2 flex items-center">
                    <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    ${rec.title}
                </h4>
                <p class="text-gray-700">${rec.description}</p>
            </div>
        `).join('');
}

// Initialize everything when the page loads
document.addEventListener('DOMContentLoaded', () => {
    initializeVideoControls();
    createVehicleDistributionChart();
    createTrafficFlowChart();
    updateAnalysisResults();
});
