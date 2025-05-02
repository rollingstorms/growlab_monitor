

document.addEventListener('DOMContentLoaded', () => {
  const listWidget = document.querySelector('#device-list-widget ul');

  async function updateDeviceList() {
    try {
      const res = await fetch('/api/devices');
      const json = await res.json();
      const devices = json.devices || [];

      // Clear existing list
      listWidget.innerHTML = '';

      if (!devices.length) {
        const li = document.createElement('li');
        li.textContent = 'No devices configured.';
        listWidget.appendChild(li);
        return;
      }

      // Populate with latest devices
      devices.forEach(dev => {
        const li = document.createElement('li');
        li.id = `device-item-${dev.id}`;
        li.innerHTML = `<strong>${dev.name}</strong> — ${dev.type}`;
        listWidget.appendChild(li);
      });
    } catch (err) {
      console.error('Failed to fetch device list:', err);
    }
  }

  // Initial load and polling
  updateDeviceList();
  setInterval(updateDeviceList, 60000);
});