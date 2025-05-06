document.addEventListener('DOMContentLoaded', () => {
  const POLL_INTERVAL = 60000; // 60s

  document.querySelectorAll('.sensor-widget').forEach(widget => {
    const metrics = JSON.parse(widget.dataset.metrics);
    const deviceId = widget.id.split('-')[1];
    const tableBody = widget.querySelector(`#table-${deviceId}`);

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
              type: 'time',
              time: {
                parser: 'YYYY-MM-DD HH:mm:ss',
                tooltipFormat: 'lll',
                unit: 'minute',
                displayFormats: { minute: 'HH:mm' }
              },
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
        const res = await fetch(`/api/${deviceId}/sensor_data`);
        const json = await res.json();
        const { current, history } = json;

        // Update current readings
        metrics.forEach(m => {
          const v = current[m.name];
          if (v !== undefined) {
            spans[m.name].textContent = v.toFixed(2);
          }
        });

        // Prepare timeline and series per metric
        const times = history.map(r => r.ts);
        metrics.forEach(m => {
          const data = history.map(r => r[m.name] ?? null);
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
            td.textContent = (value !== undefined && value !== null)
              ? value.toFixed(2)
              : '';
            tr.appendChild(td);
          });
          tableBody.appendChild(tr);
        });

      } catch (err) {
        console.error('Failed to fetch sensor data:', err);
      }
    }

    // Initial draw and periodic updates
    updateSensorData();
    setInterval(updateSensorData, POLL_INTERVAL);
  });
});
