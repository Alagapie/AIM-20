// AIM20/VISION20 Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Confirm delete actions
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });

    console.log('AIM20/VISION20 loaded successfully');
});

// Utility functions
function showNotification(message, type = 'info') {
    const alertClass = `alert-${type}`;
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const container = document.querySelector('main .container');
    if (container) {
        container.insertAdjacentHTML('afterbegin', alertHtml);
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function formatDate(date) {
    return new Date(date).toLocaleDateString();
}

// Pomodoro timer functionality (basic)
class PomodoroTimer {
    constructor(workDuration = 25, breakDuration = 5) {
        this.workDuration = workDuration * 60;
        this.breakDuration = breakDuration * 60;
        this.currentTime = this.workDuration;
        this.isWork = true;
        this.isRunning = false;
        this.interval = null;
    }

    start() {
        if (this.isRunning) return;
        this.isRunning = true;
        this.interval = setInterval(() => this.tick(), 1000);
    }

    pause() {
        this.isRunning = false;
        clearInterval(this.interval);
    }

    reset() {
        this.pause();
        this.currentTime = this.isWork ? this.workDuration : this.breakDuration;
        this.updateDisplay();
    }

    tick() {
        this.currentTime--;
        this.updateDisplay();
        
        if (this.currentTime <= 0) {
            this.switchMode();
        }
    }

    switchMode() {
        this.isWork = !this.isWork;
        this.currentTime = this.isWork ? this.workDuration : this.breakDuration;
        this.notifyModeSwitch();
        this.updateDisplay();
    }

    updateDisplay() {
        // To be implemented with DOM elements
        console.log(`Time: ${formatTime(this.currentTime)}, Mode: ${this.isWork ? 'Work' : 'Break'}`);
    }

    notifyModeSwitch() {
        const mode = this.isWork ? 'Work' : 'Break';
        showNotification(`Time for ${mode} session!`, 'success');
        
        // Play notification sound if supported
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`AIM20/VISION20: ${mode} Time!`);
        }
    }
}

// Export for use in other modules
window.PomodoroTimer = PomodoroTimer;
window.showNotification = showNotification;