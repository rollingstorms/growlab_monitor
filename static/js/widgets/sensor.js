document.addEventListener('DOMContentLoaded', () => {
  const POLL_INTERVAL = 60000; // 60s

  document.querySelectorAll('.sensor-widget').forEach(widget => {
    const metrics = JSON.parse(widget.dataset.metrics);
    const deviceId = widget.id.split('-')[1];
    const tableBody = widget.querySelector(`#table-${deviceId}`);

    console.log(`Initializing sensor widget for device: ${deviceId}`);
    console.log(`Metrics configured:`, metrics);

    // Map placeholders and initialize empty charts
    const spans = {};
    const charts = {};

    metrics.forEach(m => {
      spans[m.name] = widget.querySelector(`.sensor-${m.name}`);
      const ctx = widget.querySelector(`#chart-${m.name}-${deviceId}`).getContext('2d');

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
              type: 'category', // Changed from 'time' to avoid parsing issues
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
        console.log(`Received data for ${deviceId}:`, json);
        
        const { current, history } = json;

        if (!current || Object.keys(current).length === 0) {
          console.warn(`No current data for ${deviceId}`);
          return;
        }

        // Update current readings
        console.log(`Updating current readings for ${deviceId}`);
        metrics.forEach(m => {
          const v = current[m.name];
          console.log(`Metric ${m.name}: ${v}`);
          if (v !== undefined && v !== null) {
            // Handle potential string values
            const numValue = typeof v === 'string' ? parseFloat(v) : v;
            spans[m.name].textContent = isNaN(numValue) ? '--' : numValue.toFixed(2);
          }
        });

        if (!history || history.length === 0) {
          console.warn(`No history data for ${deviceId}`);
          return;
        }

        // Prepare timeline and series per metric
        // Use simpler timestamps for display, we'll use category scale instead of time
        // This avoids date parsing issues
        const times = history.map(r => {
          // Extract just the time portion or format as needed
          const ts = r.ts;
          return ts.split('T').length > 1 ? ts.split('T')[1].substring(0, 5) : ts;
        });
        
        // Convert each metric series separately
        metrics.forEach(m => {
          const data = history.map(r => {
            const val = r[m.name];
            // Handle missing or string values
            if (val === undefined || val === null) return null;
            return typeof val === 'string' ? parseFloat(val) : val;
          });
          
          const chart = charts[m.name];
          chart.data.labels = times;
          chart.data.datasets[0].data = data;
          chart.update();
        });

        // Populate the data table
        tableBody.innerHTML = '';
        history.forEach(r => {
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
      }
    }

    // Initial draw and periodic updates
    updateSensorData();
    setInterval(updateSensorData, POLL_INTERVAL);
  });
});
