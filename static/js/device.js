document.addEventListener('DOMContentLoaded', () => {
  const POLL_INTERVAL = 60000; // 60s

  document.querySelectorAll('.device-widget').forEach(widget => {
    const widgetId = widget.id;            // e.g., "device-fan1"
    const deviceId = widgetId.split('-')[1];

    const statusSpan = widget.querySelector('.device-status');
    const onBtn = widget.querySelector('.device-on');
    const offBtn = widget.querySelector('.device-off');
    const chartCanvas = widget.querySelector(`#device-chart-${deviceId}`);

    // Initialize Chart.js stepped line chart
    const deviceChart = new Chart(chartCanvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'State',
          data: [],
          stepped: true,
          fill: false,
        }]
      },
      options: {
        scales: {
          x: { display: true, title: { display: true, text: 'Time' } },
          y: {
            display: true,
            title: { display: true, text: 'State' },
            ticks: {
              callback: val => val === 1 ? 'On' : 'Off',
              stepSize: 1,
              min: 0,
              max: 1
            }
          }
        }
      }
    });

    // Fetch status and history, then update UI/chart
    async function updateDevice() {
      try {
        const res = await fetch(`/api/${deviceId}/status`);
        const json = await res.json();

        // Update current status
        const current = json.current.state;
        statusSpan.textContent = current.charAt(0).toUpperCase() + current.slice(1);

        // Prepare history
        const times = json.history.map(item => item.ts);
        const states = json.history.map(item => item.state === 'on' ? 1 : 0);

        deviceChart.data.labels = times;
        deviceChart.data.datasets[0].data = states;
        deviceChart.update();
      } catch (err) {
        console.error('Failed to fetch device status:', err);
      }
    }

    // Control buttons
    onBtn.addEventListener('click', async () => {
      await fetch(`/api/${deviceId}/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'on' })
      });
      updateDevice();
    });

    offBtn.addEventListener('click', async () => {
      await fetch(`/api/${deviceId}/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'off' })
      });
      updateDevice();
    });

    // Initial load and polling
    updateDevice();
    setInterval(updateDevice, POLL_INTERVAL);
  });
});
