

document.addEventListener('DOMContentLoaded', () => {
  const display = document.querySelector('#clock-widget .clock-display');

  async function updateClock() {
    try {
      const res = await fetch('/api/clock');
      const data = await res.json();
      display.textContent = data.datetime;
    } catch (err) {
      console.error('Clock update failed:', err);
    }
  }

  // Initial update and polling every second
  updateClock();
  setInterval(updateClock, 1000);
});