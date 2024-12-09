const videoPlayer = document.getElementById('videoPlayer');
const detectionOverlay = document.getElementById('detectionOverlay');
const ctx = detectionOverlay.getContext('2d');
const progressBar = document.getElementById('progressBar');
const progressPercentage = document.getElementById('progressPercentage');
const processingLog = document.getElementById('processingLog');
const loadingOverlay = document.getElementById('loadingOverlay');

const totalVehiclesElement = document.getElementById('totalVehicles');
const processingFPSElement = document.getElementById('processingFPS');
const currentTimeElement = document.getElementById('currentTime');
const detectionRateElement = document.getElementById('detectionRate');
const vehicleTypeStats = document.getElementById('vehicleTypeStats');

let isProcessing = false;
let socket = null;
let frameCount = 0;
let lastFrameTime = 0;
let totalDetections = 0;
let processedFrames = 0;

const vehicleStyles = {
    car: {
        color: '#3B82F6',
        label: 'Cars',
        icon: ''
    },
    truck: {
        color: '#EF4444',
        label: 'Trucks',
        icon: ''
    },
    bus: {
        color: '#F59E0B',
        label: 'Buses',
        icon: ''
    },
    motorcycle: {
        color: '#8B5CF6',
        label: 'Motorcycles',
        icon: ''
    }
};

document.addEventListener('DOMContentLoaded', () => {
    initializeVideo();
    setupWebSocket();
    initializeVehicleStats();
    resizeCanvas();
});

window.addEventListener('resize', resizeCanvas);

function resizeCanvas() {
    if (videoPlayer && detectionOverlay) {
        detectionOverlay.width = videoPlayer.clientWidth;
        detectionOverlay.height = videoPlayer.clientHeight;
    }
}

function initializeVideo() {
    videoPlayer.addEventListener('play', () => {
        frameCount = 0;
        lastFrameTime = performance.now();
    });

    videoPlayer.addEventListener('timeupdate', updateTime);
}

function initializeVehicleStats() {
    Object.entries(vehicleStyles).forEach(([type, style]) => {
        const statBox = document.createElement('div');
        statBox.className = 'bg-white rounded-lg p-4 shadow border-l-4';
        statBox.style.borderLeftColor = style.color;
        
        statBox.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <span class="text-2xl">${style.icon}</span>
                    <span class="ml-2 text-gray-600">${style.label}</span>
                </div>
                <span id="${type}Count" class="text-2xl font-bold" style="color: ${style.color}">0</span>
            </div>
        `;
        vehicleTypeStats.appendChild(statBox);
    });
}

function setupWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const analysisId = document.getElementById('analysisId').value;
    const wsUrl = `${protocol}//${window.location.host}/ws/processing/${analysisId}/`;
    
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const reconnectDelay = 1000;

    function connect() {
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            console.log('WebSocket connected');
            reconnectAttempts = 0;
            addLogMessage('Connected to processing server');
            loadingOverlay.classList.remove('hidden');
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };

        socket.onclose = (event) => {
            console.log('WebSocket disconnected');
            loadingOverlay.classList.add('hidden');
            addLogMessage('Disconnected from processing server');
            
            if (reconnectAttempts < maxReconnectAttempts) {
                const delay = reconnectDelay * Math.pow(2, reconnectAttempts);
                addLogMessage(`Attempting to reconnect in ${delay/1000} seconds...`);
                setTimeout(() => {
                    reconnectAttempts++;
                    connect();
                }, delay);
            } else {
                handleProcessingError('Connection lost. Please refresh the page to try again.');
            }
        };

        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            handleProcessingError('Connection error occurred');
        };
    }

    connect();
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'processing_update':
            updateProgress(data.progress);
            updateStats(data.counts);
            if (data.detections) {
                drawDetections(data.detections);
                updateDetectionRate(data.detections.length);
            }
            break;
            
        case 'processing_complete':
            isProcessing = false;
            loadingOverlay.classList.add('hidden');
            addLogMessage('Processing completed successfully');
            window.location.href = data.results_url;
            break;
            
        case 'processing_error':
            handleProcessingError(data.message);
            break;
            
        default:
            console.log('Unknown message type:', data.type);
    }
}

function updateProgress(progress) {
    const percentage = Math.round(progress * 100);
    progressBar.style.width = `${percentage}%`;
    progressPercentage.textContent = `${percentage}%`;
    processedFrames++;
    updateFPS();
    addToLog(`Processing: ${percentage}% complete`);
}

function updateStats(counts) {
    let total = 0;
    Object.entries(counts).forEach(([type, count]) => {
        const element = document.getElementById(`${type}Count`);
        if (element) {
            element.textContent = count;
            total += count;
        }
    });
    totalVehiclesElement.textContent = total;
    totalDetections = total;
}

function updateFPS() {
    const now = performance.now();
    const elapsed = (now - lastFrameTime) / 1000;
    if (elapsed >= 1) {
        const fps = Math.round(frameCount / elapsed);
        processingFPSElement.textContent = fps;
        frameCount = 0;
        lastFrameTime = now;
    }
    frameCount++;
}

function updateTime() {
    const time = Math.floor(videoPlayer.currentTime);
    const minutes = Math.floor(time / 60);
    const seconds = time % 60;
    currentTimeElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function updateDetectionRate() {
    if (processedFrames > 0) {
        const rate = Math.round((totalDetections / processedFrames) * 100);
        detectionRateElement.textContent = `${rate}%`;
    }
}

function drawDetections(detections) {
    ctx.clearRect(0, 0, detectionOverlay.width, detectionOverlay.height);
    
    const scaleX = detectionOverlay.width / videoPlayer.videoWidth;
    const scaleY = detectionOverlay.height / videoPlayer.videoHeight;
    
    detections.forEach(detection => {
        const style = vehicleStyles[detection.vehicle_type];
        if (!style) return;
        
        const x = detection.bbox_x1 * scaleX;
        const y = detection.bbox_y1 * scaleY;
        const width = (detection.bbox_x2 - detection.bbox_x1) * scaleX;
        const height = (detection.bbox_y2 - detection.bbox_y1) * scaleY;
        
        ctx.strokeStyle = style.color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);
        
        ctx.fillStyle = style.color + '80';  
        const label = `${style.icon} ${Math.round(detection.confidence * 100)}%`;
        const labelWidth = ctx.measureText(label).width + 10;
        ctx.fillRect(x, y - 25, labelWidth, 20);
        
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '14px Arial';
        ctx.fillText(label, x + 5, y - 10);
    });
}

function addLogMessage(message) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = 'text-gray-600';
    logEntry.textContent = `[${timestamp}] ${message}`;
    processingLog.appendChild(logEntry);
    processingLog.scrollTop = processingLog.scrollHeight;
}

function handleProcessingError(message) {
    isProcessing = false;
    loadingOverlay.classList.add('hidden');
    addLogMessage(`Error: ${message}`);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4';
    errorDiv.textContent = message;
    document.querySelector('.container').insertBefore(errorDiv, document.querySelector('.card'));
}
