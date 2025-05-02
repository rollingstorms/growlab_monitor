document.addEventListener('DOMContentLoaded', () => {
  const POLL_INTERVAL = 60000; // 60s in milliseconds

  document.querySelectorAll('.sensor-widget').forEach(widget => {
    const widgetId = widget.id; // e.g., "sensor-sensor1"
    const deviceId = widgetId.split('-')[1];

    const tempSpan = widget.querySelector('.sensor-temp');
    const humSpan = widget.querySelector('.sensor-hum');
    const tempCanvas = widget.querySelector(`#temp-chart-${deviceId}`);
    const humCanvas  = widget.querySelector(`#hum-chart-${deviceId}`);

    // Initialize Chart.js charts
    const tempChart = new Chart(tempCanvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Temperature (°C)',
          data: [],
          fill: false,
        }]
      },
      options: {
        scales: {
          x: { display: true, title: { display: true, text: 'Time' } },
          y: { display: true, title: { display: true, text: '°C' } }
        }
      }
    });

    const humChart = new Chart(humCanvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Humidity (%)',
          data: [],
          fill: false,
        }]
      },
      options: {
        scales: {
          x: { display: true, title: { display: true, text: 'Time' } },
          y: { display: true, title: { display: true, text: '%' } }
        }
      }
    });

    // Function to fetch and update data
    async function updateSensorData() {
      try {
        const res = await fetch(`/api/${deviceId}/sensor_data`);
        const json = await res.json();

        // Update current readings
        tempSpan.textContent = json.current.temp.toFixed(1);
        humSpan.textContent  = json.current.hum.toFixed(1);

        // Prepare history arrays
        const times = json.history.map(item => item.ts);
        const temps = json.history.map(item => item.temp);
        const hums  = json.history.map(item => item.hum);

        // Update temperature chart
        tempChart.data.labels = times;
        tempChart.data.datasets[0].data = temps;
        tempChart.update();

        // Update humidity chart
        humChart.data.labels = times;
        humChart.data.datasets[0].data = hums;
        humChart.update();

      } catch (err) {
        console.error('Failed to fetch sensor data:', err);
      }
    }

    // Initial load and interval polling
    updateSensorData();
    setInterval(updateSensorData, POLL_INTERVAL);
  });
});
