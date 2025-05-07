/**
 * Device Control System
 * Handles device status display, manual control, and automatic control based on sensor conditions
 */

class DeviceController {
  constructor(deviceId, deviceType = 'generic') {
    this.deviceId = deviceId;
    this.deviceType = deviceType;
    this.statusElement = document.querySelector(`#device-${deviceId} .device-status`);
    this.controlsContainer = document.querySelector(`#device-${deviceId} .device-controls`);
    this.chartElement = document.getElementById(`device-chart-${deviceId}`);
    this.chart = null;
    
    // Replace the separate buttons with a toggle switch
    this.replaceButtonsWithToggle();
    
    // Initialize the automation controls if needed
    this.initAutomationControls();
    
    // Set up the chart for historical data
    this.initChart();
    
    // Initial data fetch
    this.fetchStatus();
    
    // Set up polling for updates
    setInterval(() => this.fetchStatus(), 60000); // Update every minute
  }
  
  replaceButtonsWithToggle() {
    // Clear the existing buttons
    this.controlsContainer.innerHTML = '';
    
    // Create toggle switch HTML
    const toggleHtml = `
      <div class="switch-container">
        <label class="switch">
          <input type="checkbox" id="device-toggle-${this.deviceId}">
          <span class="slider round"></span>
        </label>
        <span class="switch-label">Power</span>
      </div>
    `;
    
    this.controlsContainer.innerHTML = toggleHtml;
    
    // Add event listener to the toggle
    const toggle = document.getElementById(`device-toggle-${this.deviceId}`);
    toggle.addEventListener('change', (e) => {
      this.controlDevice(e.target.checked ? 'on' : 'off');
    });
  }
  
  initAutomationControls() {
    // Create automation controls container
    const automationContainer = document.createElement('div');
    automationContainer.className = 'automation-controls';
    
    // Create HTML for conditional controls
    automationContainer.innerHTML = `
      <details>
        <summary>Automation Rules</summary>
        <div class="rule-container">
          <select id="action-${this.deviceId}">
            <option value="turn_on">Turn ON</option>
            <option value="turn_off">Turn OFF</option>
          </select>
          <span>when</span>
          <select id="sensor-${this.deviceId}" class="sensor-select">
            <option value="">Select Sensor</option>
            <!-- Will be populated dynamically -->
          </select>
          <select id="condition-${this.deviceId}">
            <option value="gt">is greater than</option>
            <option value="lt">is less than</option>
            <option value="eq">equals</option>
          </select>
          <input type="number" id="threshold-${this.deviceId}" placeholder="Value">
          <button id="save-rule-${this.deviceId}">Save Rule</button>
        </div>
        <div id="rules-list-${this.deviceId}" class="rules-list">
          <!-- Existing rules will appear here -->
        </div>
      </details>
    `;
    
    // Insert after the main controls
    this.controlsContainer.after(automationContainer);
    
    // Set up event listeners
    document.getElementById(`save-rule-${this.deviceId}`).addEventListener('click', () => {
      this.saveAutomationRule();
    });
    
    // Fetch available sensors for the dropdown
    this.fetchAvailableSensors();
    
    // Load existing rules
    this.loadAutomationRules();
  }
  
  initChart() {
    if (!this.chartElement) return;
    
    const ctx = this.chartElement.getContext('2d');
    this.chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: [],
        datasets: [{
          label: 'Device State',
          data: [],
          backgroundColor: 'rgba(54, 162, 235, 0.5)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            max: 1,
            ticks: {
              callback: function(value) {
                return value === 0 ? 'OFF' : 'ON';
              }
            }
          }
        }
      }
    });
  }
  
  fetchStatus() {
    fetch(`/api/${this.deviceId}/status`)
      .then(response => response.json())
      .then(data => {
        this.updateUI(data);
      })
      .catch(error => {
        console.error('Error fetching device status:', error);
        this.statusElement.textContent = 'Error';
        this.statusElement.classList.add('error');
      });
  }
  
  updateUI(data) {
    // Update status display
    const currentState = data.current?.state || 'unknown';
    this.statusElement.textContent = currentState === 'on' ? 'ON' : 'OFF';
    this.statusElement.className = 'device-status ' + currentState;
    
    // Update toggle switch without triggering events
    const toggle = document.getElementById(`device-toggle-${this.deviceId}`);
    if (toggle) {
      toggle.checked = currentState === 'on';
    }
    
    // Update chart with historical data
    if (this.chart && data.history) {
      this.updateChart(data.history);
    }
    
    // Check automation rules
    this.checkAutomationRules();
  }
  
  updateChart(history) {
    const labels = history.map(item => {
      const date = new Date(item.ts);
      return date.toLocaleTimeString();
    });
    
    const datasets = history.map(item => item.state === 'on' ? 1 : 0);
    
    this.chart.data.labels = labels;
    this.chart.data.datasets[0].data = datasets;
    this.chart.update();
  }
  
  controlDevice(action) {
    // Show loading state
    this.statusElement.textContent = 'Changing...';
    
    fetch(`/api/${this.deviceId}/control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ action: action })
    })
    .then(response => response.json())
    .then(data => {
      if (data.result === 'ok') {
        // Update was successful, refresh status
        this.fetchStatus();
      } else {
        throw new Error('Failed to update device');
      }
    })
    .catch(error => {
      console.error('Error controlling device:', error);
      this.statusElement.textContent = 'Error';
      this.statusElement.classList.add('error');
      
      // Reset toggle to previous state
      const toggle = document.getElementById(`device-toggle-${this.deviceId}`);
      if (toggle) {
        toggle.checked = action !== 'on';
      }
    });
  }
  
  fetchAvailableSensors() {
    // Fetch list of available sensors from the API
    fetch('/api/sensors')
      .then(response => response.json())
      .then(data => {
        const sensorSelect = document.getElementById(`sensor-${this.deviceId}`);
        data.forEach(sensor => {
          const option = document.createElement('option');
          option.value = sensor.id;
          option.textContent = sensor.name;
          sensorSelect.appendChild(option);
        });
      })
      .catch(error => {
        console.error('Error fetching sensors:', error);
      });
  }
  
  saveAutomationRule() {
    const action = document.getElementById(`action-${this.deviceId}`).value;
    const sensor = document.getElementById(`sensor-${this.deviceId}`).value;
    const condition = document.getElementById(`condition-${this.deviceId}`).value;
    const threshold = document.getElementById(`threshold-${this.deviceId}`).value;
    
    if (!sensor || !threshold) {
      alert('Please select a sensor and threshold value');
      return;
    }
    
    const rule = {
      deviceId: this.deviceId,
      action: action,
      sensor: sensor,
      condition: condition,
      threshold: parseFloat(threshold)
    };
    
    // Save rule to server (this would call your backend API)
    fetch('/api/automation/rules', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(rule)
    })
    .then(response => response.json())
    .then(data => {
      if (data.result === 'ok') {
        this.loadAutomationRules(); // Refresh the rules list
      } else {
        throw new Error('Failed to save rule');
      }
    })
    .catch(error => {
      console.error('Error saving automation rule:', error);
      alert('Failed to save automation rule');
    });
  }
  
  loadAutomationRules() {
    // Fetch existing rules from server
    fetch(`/api/automation/rules?device=${this.deviceId}`)
      .then(response => response.json())
      .then(rules => {
        const rulesList = document.getElementById(`rules-list-${this.deviceId}`);
        rulesList.innerHTML = '';
        
        if (rules.length === 0) {
          rulesList.innerHTML = '<p class="no-rules">No automation rules defined</p>';
          return;
        }
        
        rules.forEach(rule => {
          const ruleElement = document.createElement('div');
          ruleElement.className = 'rule-item';
          
          const actionText = rule.action === 'turn_on' ? 'Turn ON' : 'Turn OFF';
          const conditionText = rule.condition === 'gt' ? '>' : rule.condition === 'lt' ? '<' : '=';
          
          ruleElement.innerHTML = `
            <p>${actionText} when ${rule.sensorName} ${conditionText} ${rule.threshold}</p>
            <button class="delete-rule" data-rule-id="${rule.id}">Delete</button>
          `;
          
          rulesList.appendChild(ruleElement);
        });
        
        // Set up delete buttons
        document.querySelectorAll('.delete-rule').forEach(button => {
          button.addEventListener('click', (e) => {
            const ruleId = e.target.dataset.ruleId;
            this.deleteAutomationRule(ruleId);
          });
        });
      })
      .catch(error => {
        console.error('Error loading automation rules:', error);
      });
  }
  
  deleteAutomationRule(ruleId) {
    fetch(`/api/automation/rules/${ruleId}`, {
      method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
      if (data.result === 'ok') {
        this.loadAutomationRules(); // Refresh the rules list
      } else {
        throw new Error('Failed to delete rule');
      }
    })
    .catch(error => {
      console.error('Error deleting automation rule:', error);
    });
  }
  
  checkAutomationRules() {
    // This would typically be done server-side, but we can check rules on the client too
    fetch(`/api/automation/check?device=${this.deviceId}`)
      .then(response => response.json())
      .then(result => {
        if (result.actionRequired) {
          // Server determined an action is needed based on rules
          this.controlDevice(result.action);
        }
      })
      .catch(error => {
        console.error('Error checking automation rules:', error);
      });
  }
}

// Initialize all device widgets when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  // Find all device widgets and initialize controllers
  document.querySelectorAll('.device-widget').forEach(widget => {
    const deviceId = widget.id.replace('device-', '');
    const deviceType = widget.dataset.deviceType || 'generic';
    new DeviceController(deviceId, deviceType);
  });
});