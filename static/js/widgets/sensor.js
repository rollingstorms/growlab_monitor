document.addEventListener('DOMContentLoaded', () => {
  const POLL_INTERVAL = 60000; // 60s
  
  // Keep track of widget instances to prevent duplicate initialization
  const initializedWidgets = new Set();

  document.querySelectorAll('.sensor-widget').forEach(widget => {
    const deviceId = widget.id.split('-')[1];
    
    // Check if this widget is already initialized
    if (initializedWidgets.has(deviceId)) {
      console.warn(`Widget for ${deviceId} already initialized, skipping`);
      return;
    }
    
    // Mark as initialized
    initializedWidgets.add(deviceId);
    
    const metrics = JSON.parse(widget.dataset.metrics);
    const tableBody = widget.querySelector(`#table-${deviceId}`);

    console.log(`Initializing sensor widget for device: ${deviceId}`);
    console.log(`Metrics configured:`, metrics);

    // Map placeholders and initialize empty charts
    const spans = {};
    const charts = {};

    metrics.forEach(m => {
      spans[m.name] = widget.querySelector(`.sensor-${m.name}`);
      const chartElement = widget.querySelector(`#chart-${m.name}-${deviceId}`);
      
      // Skip if element doesn't exist
      if (!chartElement) {
        console.error(`Chart element for ${m.name} not found`);
        return;
      }
      
      const ctx = chartElement.getContext('2d');

      charts[m.name] = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: m.label,
            data: [],
            fill: false,
            tension: 0.4,
            pointRadius: 2,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            tooltip: { mode: 'index', intersect: false },
            legend: { display: true, position: 'top' }
          },
          scales: {
            x: {
              type: 'category', // Use category scale for simplicity
              title: { display: true, text: 'Time' }
            },
            y: {
              title: { display: true, text: m.label },
              beginAtZero: false
            }
          }
        }
      });
    });

    // Fetch and render the data
    async function updateSensorData() {
      try {
        console.log(`Fetching sensor data for ${deviceId}...`);
        const res = await fetch(`/api/${deviceId}/sensor_data`);
        const json = await res.json();
        console.log(`Received data for ${deviceId}, history length: ${json.history ? json.history.length : 0}`);
        
        const { current, history, has_data } = json;

        // Update current readings
        metrics.forEach(m => {
          const span = spans[m.name];
          if (has_data && current && current[m.name] !== undefined && current[m.name] !== null) {
            // We have data - show the value
            const numValue = typeof current[m.name] === 'string' ? parseFloat(current[m.name]) : current[m.name];
            span.textContent = isNaN(numValue) ? '--' : numValue.toFixed(2);
          } else {
            // No data available - show "No data" message
            span.textContent = 'No data';
            span.classList.add('no-data');
          }
        });

        if (!has_data || !history || history.length === 0) {
          // No data case - show "No data available" in charts
          metrics.forEach(m => {
            const chart = charts[m.name];
            if (!chart) return;
            
            chart.data.labels = ['No data available'];
            chart.data.datasets[0].data = [];
            chart.update();
            
            // Add a "No data" message to the chart container
            const chartElement = widget.querySelector(`#chart-${m.name}-${deviceId}`);
            if (chartElement) {
              const container = chartElement.parentNode;
              // Only add the message if it doesn't exist
              if (!container.querySelector('.no-data-message')) {
                const msg = document.createElement('div');
                msg.className = 'no-data-message';
                msg.textContent = 'No data available for this sensor';
                msg.style.textAlign = 'center';
                msg.style.color = '#666';
                msg.style.padding = '20px';
                container.appendChild(msg);
              }
            }
          });
          
          // Add a message to the table
          if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="' + (metrics.length + 1) + 
                                 '" style="text-align: center;">No data available</td></tr>';
          }
          return;
        }
        
        // Remove any no-data messages if we have data
        const noDataMessages = widget.querySelectorAll('.no-data-message');
        noDataMessages.forEach(msg => msg.remove());

        // Prepare timeline and series per metric
        // Extract just the time portion for display
        const times = history.map(r => {
          const ts = r.ts;
          return ts.split('T').length > 1 ? ts.split('T')[1].substring(0, 5) : ts;
        });
        
        // Update each chart with its metric data
        metrics.forEach(m => {
          const chart = charts[m.name];
          if (!chart) return; // Skip if chart not initialized
          
          const data = history.map(r => {
            const val = r[m.name];
            if (val === undefined || val === null) return null;
            return typeof val === 'string' ? parseFloat(val) : val;
          });
          
          // Update chart data but prevent duplicates
          chart.data.labels = times;
          chart.data.datasets[0].data = data;
          chart.update();
        });

        // Populate the data table (show only a reasonable number of rows)
        // Clear the table first
        tableBody.innerHTML = '';
        
        // Add rows but limit to latest 10 for readability
        const displayHistory = history.slice(0, 10);
        
        displayHistory.forEach(r => {
          const tr = document.createElement('tr');
          // Timestamp cell
          const tdTime = document.createElement('td');
          tdTime.textContent = r.ts;
          tr.appendChild(tdTime);
          // Metric cells
          metrics.forEach(m => {
            const td = document.createElement('td');
            const value = r[m.name];
            if (value !== undefined && value !== null) {
              const numValue = typeof value === 'string' ? parseFloat(value) : value;
              td.textContent = isNaN(numValue) ? '--' : numValue.toFixed(2);
            } else {
              td.textContent = '--';
            }
            tr.appendChild(td);
          });
          tableBody.appendChild(tr);
        });

      } catch (err) {
        console.error(`Failed to fetch sensor data for ${deviceId}:`, err);
        // Show error state in the UI
        metrics.forEach(m => {
          if (spans[m.name]) spans[m.name].textContent = 'Error';
        });
        
        if (tableBody) {
          tableBody.innerHTML = '<tr><td colspan="' + (metrics.length + 1) + 
                               '" style="text-align: center;">Error loading data</td></tr>';
        }
      }
    }

    // Initial draw and periodic updates
    updateSensorData();
    setInterval(updateSensorData, POLL_INTERVAL);
  });
});
