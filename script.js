const API_BASE = '';  // Use relative paths
let statusUpdateInterval;

async function configureDevice() {
    const hostname = document.getElementById('hostname').value;
    if (!hostname) {
        alert('Please enter a device IP/hostname');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/device/configure`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ hostname }),
        });

        if (response.ok) {
            document.getElementById('connectionStatus').className = 'status-indicator connected';
            updateVolume();
            startStatusUpdates();
        } else {
            const error = await response.json();
            document.getElementById('connectionStatus').className = 'status-indicator error';
            console.error('Configuration failed:', error.detail);
        }
    } catch (error) {
        document.getElementById('connectionStatus').className = 'status-indicator error';
        console.error('Connection error:', error.message);
    }
}

async function togglePower() {
    await sendCommand('power');
}

async function playAudio() {
    await sendCommand('play');
}

async function pauseAudio() {
    await sendCommand('pause');
}

async function setVolume(value) {
    document.getElementById('volumeLabel').textContent = value;
    await sendCommand('volume', { value: parseInt(value) });
}

async function setPreset(value) {
    await sendCommand('preset', { value });
}

async function updateVolume() {
    try {
        const response = await fetch(`${API_BASE}/device/volume`);
        if (response.ok) {
            const data = await response.json();
            const volumeSlider = document.getElementById('volume');
            volumeSlider.value = data.actual;
            document.getElementById('volumeLabel').textContent = data.actual;
        }
    } catch (error) {
        console.error('Error updating volume:', error);
    }
}

async function updateStatus() {
    try {
        const response = await fetch(`${API_BASE}/device/status`);
        if (response.ok) {
            const data = await response.json();
            const artElement = document.getElementById('containerArt');
            
            // Update container art if available
            if (data.content_item.container_art) {
                const imageUrl = `${API_BASE}/proxy/image?url=${encodeURIComponent(data.content_item.container_art)}`;
                artElement.src = imageUrl;
                artElement.style.display = '';
            } else {
                artElement.style.display = 'none';
            }
            
            // Update track info
            document.getElementById('trackName').textContent = 
                data.track || data.station_name || data.content_item.name || 'Not Playing';
            document.getElementById('artistName').textContent = 
                data.artist || '';
            document.getElementById('sourceName').textContent = 
                `${data.source}${data.content_item.name ? ` - ${data.content_item.name}` : ''}`;
            
            // Update connection status on successful status fetch
            document.getElementById('connectionStatus').className = 'status-indicator connected';
        }
    } catch (error) {
        console.error('Error updating status:', error);
        document.getElementById('connectionStatus').className = 'status-indicator error';
    }
}

async function sendCommand(endpoint, data = null) {
    try {
        const response = await fetch(`${API_BASE}/device/${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: data ? JSON.stringify(data) : null,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Command failed');
        }

        // Update status after command
        await updateStatus();
    } catch (error) {
        console.error('Command error:', error.message);
        document.getElementById('connectionStatus').className = 'status-indicator error';
    }
}

function startStatusUpdates() {
    // Clear existing interval if any
    if (statusUpdateInterval) {
        clearInterval(statusUpdateInterval);
    }
    // Update immediately
    updateStatus();
    // Then update every 5 seconds
    statusUpdateInterval = setInterval(updateStatus, 5000);
}

// Clean up interval when page is unloaded
window.addEventListener('unload', () => {
    if (statusUpdateInterval) {
        clearInterval(statusUpdateInterval);
    }
});

// Auto-configure device on page load
window.addEventListener('load', () => {
    configureDevice();
});

async function prevTrack() {
    await sendCommand('prev_track');
}

async function nextTrack() {
    await sendCommand('next_track');
}

async function thumbsUp() {
    await sendCommand('thumbs_up');
}

async function thumbsDown() {
    await sendCommand('thumbs_down');
} 