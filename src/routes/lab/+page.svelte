<script lang="ts">
    import { onDestroy, onMount } from 'svelte';

    interface PicoData {
        temperature: number,
        timestamp: number,
        device_id: string
    }
    
    // Fetch temperature data from API
    async function fetchTemperatureData() {
        try {
            const response = await fetch('/lab/api?limit=60');
            const result = await response.json();
            if (result.ok && result.data) {
                // Sort by timestamp first (oldest to newest)
                const sortedData = result.data.sort((a, b) => 
                    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
                );
                
                // Transform database data to match our format
                return sortedData.map((reading: PicoData & {id: number}, index: number) => ({
                    time: index, // This will be 0 (oldest) to length-1 (newest)
                    temperature: reading.temperature,
                    timestamp: new Date(reading.timestamp).toLocaleTimeString('en-US', { 
                        hour12: false, 
                        hour: '2-digit', 
                        minute: '2-digit' 
                    }),
                    id: reading.id,
                    device_id: reading.device_id,
                    dbTimestamp: reading.timestamp
                }));
            } else {
                console.warn('Failed to fetch data from API, using generated data');
                return generateTemperatureData();
            }
        } catch (error) {
            console.error('Error fetching temperature data:', error);
            return generateTemperatureData();
        }
    }

    // Generate 60 temperature data points (1 per minute for 1 hour) - fallback
    function generateTemperatureData() {
        const data = [];
        let baseTemp = 35; // Start around 35°C
        
        for (let i = 0; i < 60; i++) {
            // Create realistic temperature variation with some randomness
            const variation = (Math.sin(i / 10) * 8) + (Math.random() - 0.5) * 4;
            const temp = Math.max(20, Math.min(50, baseTemp + variation));
            
            data.push({
                time: i, // minutes
                temperature: Math.round(temp * 10) / 10, // round to 1 decimal
                timestamp: new Date(Date.now() + i * 60000).toLocaleTimeString('en-US', { 
                    hour12: false, 
                    hour: '2-digit', 
                    minute: '2-digit' 
                })
            });
            
            // Gradual drift for more realistic data
            baseTemp += (Math.random() - 0.5) * 0.5;
        }
        
        return data;
    }

    // Add new temperature reading
    async function addTemperatureReading(temperature: string, location = 'lab') {
        try {
            const response = await fetch('/lab/api', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    temperature: parseFloat(temperature),
                    location,
                    metadata: { source: 'manual_entry' }
                })
            });
            
            const result = await response.json();
            
            if (result.ok) {
                // Refresh data after adding
                temperatureData = await fetchTemperatureData();
                lastFetchTime = new Date();
                return { success: true, id: result.id };
            } else {
                return { success: false, error: result.error };
            }
        } catch (error) {
            console.error('Error adding temperature reading:', error);
            return { success: false, error: 'Network error' };
        }
    }
    
    let temperatureData = $state([]);
    let isLoading = $state(true);
    let newTemperature = $state('');
    let isAutoRefresh = $state(true);
    let refreshInterval = $state(30); // seconds
    let lastFetchTime = $state(null);
    let refreshTimer = null;
    
    // Auto-refresh function
    async function refreshData() {
        if (!isAutoRefresh) return;
        
        try {
            temperatureData = await fetchTemperatureData();
            lastFetchTime = new Date();
        } catch (error) {
            console.error('Auto-refresh failed:', error);
        }
    }
    
    // Setup auto-refresh timer
    function setupAutoRefresh() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
        }
        
        if (isAutoRefresh && refreshInterval > 0) {
            refreshTimer = setInterval(refreshData, refreshInterval * 1000);
        }
    }
    
    // Load data on component mount and setup auto-refresh
    onMount(async () => {
        temperatureData = await fetchTemperatureData();
        lastFetchTime = new Date();
        isLoading = false;
        setupAutoRefresh();
    });
    
    // Cleanup on component destroy
    onDestroy(() => {
        if (refreshTimer) {
            clearInterval(refreshTimer);
        }
    });
    
    // Reactive: Update timer when settings change
    $effect(() => {
        setupAutoRefresh();
    });

    let hoveredPoint = $state(null);
    let graphContainer = $state(null);
    
    // Graph dimensions and padding
    const width = 800;
    const height = 400;
    const padding = { top: 20, right: 40, bottom: 60, left: 60 };
    const graphWidth = width - padding.left - padding.right;
    const graphHeight = height - padding.top - padding.bottom;
    
    // Scale functions - inverted x-axis so latest data (newest time) is on the right
    const xScale = (time: number) => {
        if (temperatureData.length === 0) return 0;
        const maxTime = Math.max(temperatureData.length - 1, 59);
        return graphWidth - (time / maxTime) * graphWidth;
    };
    const yScale = (temp: number) => graphHeight - ((temp - 20) / 30) * graphHeight;
    
    // Generate SVG path for the line
    const generatePath = (data: [{time: number, temperature: number}]) => {
        return data.map((point, i) => {
            const x = xScale(point.time);
            const y = yScale(point.temperature);
            return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
        }).join(' ');
    };
    
    // Handle mouse interactions
    function handleMouseMove(event) {
        if (!graphContainer) return;
        
        const rect = graphContainer.getBoundingClientRect();
        const mouseX = event.clientX - rect.left - padding.left;
        const mouseY = event.clientY - rect.top - padding.top;
        
        if (mouseX >= 0 && mouseX <= graphWidth && mouseY >= 0 && mouseY <= graphHeight) {
            // Find closest data point
            let closestPoint = null;
            let closestDistance = Infinity;
            
            temperatureData.forEach((point) => {
                const pointX = xScale(point.time);
                const distance = Math.abs(pointX - mouseX);
                
                if (distance < closestDistance) {
                    closestDistance = distance;
                    closestPoint = {
                        ...point,
                        x: pointX,
                        y: yScale(point.temperature)
                    };
                }
            });
            
            // Only show if we're close enough (within 20px)
            if (closestPoint && closestDistance < 20) {
                hoveredPoint = closestPoint;
            } else {
                hoveredPoint = null;
            }
        } else {
            hoveredPoint = null;
        }
    }
    
    function handleMouseLeave() {
        hoveredPoint = null;
    }
</script>

<div class="container">
    <h1>Temperature Monitoring</h1>
    <p>Hourly temperature data (60 measurements, 1 per minute)</p>
    
    <div class="graph-wrapper">
        <svg 
            {width} 
            {height} 
            bind:this={graphContainer}
            onmousemove={handleMouseMove}
            onmouseleave={handleMouseLeave}
            role="img"
            aria-label="Interactive temperature graph showing hourly data points"
        >
            <!-- Graph background -->
            <rect 
                x={padding.left} 
                y={padding.top} 
                width={graphWidth} 
                height={graphHeight} 
                fill="#f8f9fa" 
                stroke="#e9ecef"
            />
            
            <!-- Grid lines -->
            {#each Array(7) as _, i}
                {@const y = padding.top + (i / 6) * graphHeight}
                {@const temp = 50 - (i / 6) * 30}
                <line 
                    x1={padding.left} 
                    y1={y} 
                    x2={padding.left + graphWidth} 
                    y2={y} 
                    stroke="#dee2e6" 
                    stroke-width="1"
                />
                <text 
                    x={padding.left - 10} 
                    y={y + 4} 
                    text-anchor="end" 
                    font-size="12" 
                    fill="#6c757d"
                >
                    {Math.round(temp)}°C
                </text>
            {/each}
            
            {#each Array(7) as _, i}
                {@const x = padding.left + (i / 6) * graphWidth}
                {@const maxDataPoints = Math.max(temperatureData.length - 1, 59)}
                {@const timeValue = Math.round(maxDataPoints - (i / 6) * maxDataPoints)}
                <line 
                    x1={x} 
                    y1={padding.top} 
                    x2={x} 
                    y2={padding.top + graphHeight} 
                    stroke="#dee2e6" 
                    stroke-width="1"
                />
                <text 
                    x={x} 
                    y={padding.top + graphHeight + 20} 
                    text-anchor="middle" 
                    font-size="12" 
                    fill="#6c757d"
                >
                    {timeValue}
                </text>
            {/each}
            
            <!-- Temperature line -->
            <path 
                d={generatePath(temperatureData)} 
                fill="none" 
                stroke="#0066cc" 
                stroke-width="2"
                transform={`translate(${padding.left}, ${padding.top})`}
            />
            
            <!-- Data points -->
            {#each temperatureData as point}
                {@const x = padding.left + xScale(point.time)}
                {@const y = padding.top + yScale(point.temperature)}
                <circle 
                    cx={x} 
                    cy={y} 
                    r="3" 
                    fill="#0066cc"
                    stroke="white"
                    stroke-width="1"
                />
            {/each}
            
            <!-- Hover indicator -->
            {#if hoveredPoint}
                {@const x = padding.left + hoveredPoint.x}
                {@const y = padding.top + hoveredPoint.y}
                <circle 
                    cx={x} 
                    cy={y} 
                    r="6" 
                    fill="#ff6b35"
                    stroke="white"
                    stroke-width="2"
                />
                <line 
                    x1={x} 
                    y1={padding.top} 
                    x2={x} 
                    y2={padding.top + graphHeight} 
                    stroke="#ff6b35" 
                    stroke-width="1" 
                    stroke-dasharray="4,4"
                />
            {/if}
            
            <!-- Axes labels -->
            <text 
                x={padding.left + graphWidth / 2} 
                y={height - 10} 
                text-anchor="middle" 
                font-size="14" 
                fill="#495057"
            >
                Time (minutes)
            </text>
            <text 
                x="20" 
                y={padding.top + graphHeight / 2} 
                text-anchor="middle" 
                font-size="14" 
                fill="#495057"
                transform={`rotate(-90, 20, ${padding.top + graphHeight / 2})`}
            >
                Temperature (°C)
            </text>
        </svg>
        
        <!-- Tooltip -->
        {#if hoveredPoint}
            <div class="tooltip" style="left: {padding.left + hoveredPoint.x + 10}px; top: {padding.top + hoveredPoint.y - 10}px;">
                <div><strong>Time:</strong> {hoveredPoint.timestamp}</div>
                <div><strong>Temperature:</strong> {hoveredPoint.temperature}°C</div>
                <div><strong>Device:</strong> {hoveredPoint.device_id}</div>
                {#if hoveredPoint.id}
                    <div><strong>ID:</strong> {hoveredPoint.id}</div>
                {/if}
            </div>
        {/if}
    </div>
    
    <!-- Data summary -->
    <div class="stats">
        <div class="stat-item">
            <span class="label">Min:</span>
            <span class="value">{Math.min(...temperatureData.map(d => d.temperature))}°C</span>
        </div>
        <div class="stat-item">
            <span class="label">Max:</span>
            <span class="value">{Math.max(...temperatureData.map(d => d.temperature))}°C</span>
        </div>
        <div class="stat-item">
            <span class="label">Avg:</span>
            <span class="value">{Math.round((temperatureData.reduce((sum, d) => sum + d.temperature, 0) / temperatureData.length) * 10) / 10}°C</span>
        </div>
        <div class="stat-item">
            <span class="label">Data points:</span>
            <span class="value">{temperatureData.length}</span>
        </div>
    </div>
    
    <!-- Add new temperature reading -->
    <div class="controls">    
        <div class="button-group">
            <button onclick={async () => {
                isLoading = true;
                await refreshData();
                isLoading = false;
            }}>
                Refresh Now
            </button>
            
            <button onclick={() => temperatureData = generateTemperatureData()}>
                Use Demo Data
            </button>
        </div>
        
        <!-- Auto-refresh controls -->
        <div class="auto-refresh-controls">
            <div class="toggle-group">
                <label class="toggle-label">
                    <input 
                        type="checkbox" 
                        bind:checked={isAutoRefresh}
                        onchange={() => setupAutoRefresh()}
                    />
                    <span class="toggle-text">Auto-refresh</span>
                    {#if isAutoRefresh}
                        <span class="status-indicator active">●</span>
                    {:else}
                        <span class="status-indicator inactive">○</span>
                    {/if}
                </label>
            </div>
            
            {#if isAutoRefresh}
                <div class="interval-group">
                    <label>
                        Interval:
                        <select bind:value={refreshInterval} onchange={() => setupAutoRefresh()}>
                            <option value={5}>5 seconds</option>
                            <option value={10}>10 seconds</option>
                            <option value={30}>30 seconds</option>
                            <option value={60}>1 minute</option>
                            <option value={300}>5 minutes</option>
                        </select>
                    </label>
                </div>
                
                {#if lastFetchTime}
                    <div class="last-update">
                        Last update: {lastFetchTime.toLocaleTimeString()}
                    </div>
                {/if}
            {/if}
        </div>
    </div>
    
    {#if isLoading}
        <div class="loading">Loading temperature data...</div>
    {/if}
</div>

<style>
    .container {
        padding: 2rem;
        max-width: 900px;
        margin: 0 auto;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    h1 {
        color: #212529;
        margin-bottom: 0.5rem;
    }
    
    p {
        color: #6c757d;
        margin-bottom: 2rem;
    }
    
    .graph-wrapper {
        position: relative;
        display: inline-block;
        margin-bottom: 2rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        padding: 1rem;
    }
    
    .tooltip {
        position: absolute;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 12px;
        pointer-events: none;
        z-index: 10;
        white-space: nowrap;
    }
    
    .stats {
        display: flex;
        gap: 2rem;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }
    
    .stat-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 8px;
        min-width: 100px;
    }
    
    .stat-item .label {
        font-size: 0.875rem;
        color: #6c757d;
        margin-bottom: 0.25rem;
    }
    
    .stat-item .value {
        font-size: 1.25rem;
        font-weight: 600;
        color: #212529;
    }
    
    button {
        background: #0066cc;
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 6px;
        font-size: 1rem;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    
    button:hover:not(:disabled) {
        background: #0056b3;
    }
    
    button:disabled {
        background: #6c757d;
        cursor: not-allowed;
        opacity: 0.6;
    }
    
    .controls {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .input-group {
        display: flex;
        gap: 0.5rem;
        align-items: center;
    }
    
    .input-group input {
        padding: 0.75rem;
        border: 2px solid #dee2e6;
        border-radius: 6px;
        font-size: 1rem;
        flex: 1;
        max-width: 200px;
    }
    
    .input-group input:focus {
        outline: none;
        border-color: #0066cc;
    }
    
    .button-group {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }
    
    .loading {
        text-align: center;
        padding: 2rem;
        color: #6c757d;
        font-style: italic;
    }
    
    .auto-refresh-controls {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
    
    .toggle-group {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .toggle-label {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        font-weight: 500;
    }
    
    .toggle-label input[type="checkbox"] {
        margin: 0;
    }
    
    .status-indicator {
        font-size: 1.2rem;
        margin-left: 0.25rem;
    }
    
    .status-indicator.active {
        color: #28a745;
        animation: pulse 2s infinite;
    }
    
    .status-indicator.inactive {
        color: #6c757d;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    .interval-group {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .interval-group label {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.9rem;
        color: #495057;
    }
    
    .interval-group select {
        padding: 0.25rem 0.5rem;
        border: 1px solid #ced4da;
        border-radius: 4px;
        font-size: 0.9rem;
        background: white;
    }
    
    .last-update {
        font-size: 0.85rem;
        color: #6c757d;
        font-style: italic;
    }
    
    @media (max-width: 900px) {
        .graph-wrapper {
            overflow-x: auto;
        }
        
        .stats {
            justify-content: center;
        }
        
        .controls {
            align-items: center;
        }
        
        .input-group {
            flex-direction: column;
            width: 100%;
        }
        
        .input-group input {
            max-width: 100%;
        }
        
        .button-group {
            justify-content: center;
        }
    }
</style>