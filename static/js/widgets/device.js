document.addEventListener('DOMContentLoaded', () => {
  const POLL_INTERVAL = 60000; // 60s

  document.querySelectorAll('.device-widget').forEach(widget => {
    const widgetId = widget.id;            
    const deviceId = widgetId.split('-')[1];

    const statusSpan = widget.querySelector('.device-status');
    const toggleSwitch = widget.querySelector('.device-toggle');
    const toggleLabel = widget.querySelector('.toggle-label');
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
        statusSpan.textContent = current ? current.charAt(0).toUpperCase() + current.slice(1) : '--';
        
        // Update toggle switch without triggering event
        if (current) {
          const isOn = current === 'on';
          toggleSwitch.checked = isOn;
          toggleLabel.textContent = isOn ? 'On' : 'Off';
        }

        // Prepare history
        if (json.history && json.history.length > 0) {
          const times = json.history.map(item => {
            // Format timestamp for display
            const date = new Date(item.ts);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          });
          const states = json.history.map(item => item.state === 'on' ? 1 : 0);

          deviceChart.data.labels = times;
          deviceChart.data.datasets[0].data = states;
          deviceChart.update();
        }
      } catch (err) {
        console.error('Failed to fetch device status:', err);
      }
    }

    // Toggle switch event
    toggleSwitch.addEventListener('change', async () => {
      const action = toggleSwitch.checked ? 'on' : 'off';
      toggleLabel.textContent = toggleSwitch.checked ? 'On' : 'Off';
      
      try {
        await fetch(`/api/${deviceId}/control`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: action })
        });
        updateDevice();
      } catch (err) {
        console.error('Failed to control device:', err);
        // Revert UI if control failed
        toggleSwitch.checked = !toggleSwitch.checked;
        toggleLabel.textContent = toggleSwitch.checked ? 'On' : 'Off';
      }
    });

    // Initial load and polling
    updateDevice();
    setInterval(updateDevice, POLL_INTERVAL);
  });
});
