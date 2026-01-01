// DOM Elements
const predictionForm = document.getElementById('predictionForm');
const dateInput = document.getElementById('date');
const sectorInput = document.getElementById('sector');
const temperatureInput = document.getElementById('temperature');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const loadingSpinner = document.getElementById('loadingSpinner');
const apiStatusElement = document.getElementById('apiStatus');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setTodayAsDefault();
    checkApiHealth();
    predictionForm.addEventListener('submit', handlePredictionSubmit);
});

/**
 * Set today's date as default in the date input
 */
function setTodayAsDefault() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    dateInput.value = `${year}-${month}-${day}`;
}

/**
 * Check API health status
 */
async function checkApiHealth() {
    try {
        const response = await fetch('/api/health');
        if (response.ok) {
            const data = await response.json();
            updateApiStatus('🟢 Online', '#10b981');
        } else {
            updateApiStatus('🔴 Offline', '#ef4444');
        }
    } catch (error) {
        updateApiStatus('🔴 Offline', '#ef4444');
    }
}

/**
 * Update API status indicator
 */
function updateApiStatus(status, color) {
    apiStatusElement.textContent = status;
    apiStatusElement.style.backgroundColor = `rgba(${hexToRgb(color)}, 0.2)`;
}

/**
 * Convert hex color to RGB
 */
function hexToRgb(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `${r}, ${g}, ${b}`;
}

/**
 * Handle prediction form submission
 */
async function handlePredictionSubmit(event) {
    event.preventDefault();

    // Validate inputs
    if (!validateInputs()) {
        return;
    }

    // Show loading spinner
    showLoadingSpinner();
    hideErrorMessage();

    try {
        const date = dateInput.value;
        const sector = sectorInput.value;
        const minTemp = parseFloat(temperatureInput.value);

        // Make API request
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: date,
                sector: sector,
                min_temp_celsius: minTemp
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Prediction failed');
        }

        const result = await response.json();
        displayResults(result);

    } catch (error) {
        showErrorMessage(error.message);
    } finally {
        hideLoadingSpinner();
    }
}

/**
 * Validate form inputs
 */
function validateInputs() {
    if (!dateInput.value) {
        showErrorMessage('Please select a date');
        return false;
    }

    if (!sectorInput.value) {
        showErrorMessage('Please select a sector');
        return false;
    }

    if (temperatureInput.value === '' || isNaN(temperatureInput.value)) {
        showErrorMessage('Please enter a valid temperature');
        return false;
    }

    const temp = parseFloat(temperatureInput.value);
    if (temp < -50 || temp > 50) {
        showErrorMessage('Temperature must be between -50 and 50 degrees Celsius');
        return false;
    }

    return true;
}

/**
 * Display prediction results
 */
function displayResults(result) {
    // Format date for display
    const dateObj = new Date(result.date);
    const formattedDate = dateObj.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    // Update result elements
    document.getElementById('resultDate').textContent = formattedDate;
    document.getElementById('resultSector').textContent = result.sector;
    document.getElementById('resultTemp').textContent = `${result.min_temp_celsius}°C`;
    document.getElementById('resultDemand').textContent = `${result.predicted_shelter_demand.toLocaleString()} beds`;

    // Show results section
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Show error message
 */
function showErrorMessage(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorSection.style.display = 'block';
    errorSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Hide error message
 */
function hideErrorMessage() {
    errorSection.style.display = 'none';
}

/**
 * Show loading spinner
 */
function showLoadingSpinner() {
    loadingSpinner.style.display = 'flex';
    predictionForm.style.opacity = '0.5';
    predictionForm.style.pointerEvents = 'none';
}

/**
 * Hide loading spinner
 */
function hideLoadingSpinner() {
    loadingSpinner.style.display = 'none';
    predictionForm.style.opacity = '1';
    predictionForm.style.pointerEvents = 'auto';
}

/**
 * Format numbers with thousand separators
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * Get temperature description
 */
function getTemperatureDescription(temp) {
    if (temp < -10) return 'Cold';
    if (temp < 5) return 'Cool';
    if (temp < 15) return 'Moderate';
    return 'Warm';
}

/**
 * Handle real-time validation
 */
temperatureInput.addEventListener('input', () => {
    const temp = parseFloat(temperatureInput.value);
    if (!isNaN(temp)) {
        const description = getTemperatureDescription(temp);
        // Could display temperature description in real-time
    }
});

/**
 * Auto-refresh API health status every 30 seconds
 */
setInterval(() => {
    checkApiHealth();
}, 30000);

/**
 * Keyboard shortcut: Enter to submit (when in form)
 */
document.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && event.target.closest('#predictionForm')) {
        predictionForm.dispatchEvent(new Event('submit'));
    }
});
