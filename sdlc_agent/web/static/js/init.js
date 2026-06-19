// SDLC Agent · Button wiring, init, and notifications
// Classic (non-module) script — globals shared across files; load order matters.

// ---- Wire buttons -----------------------------------------------------
const handlers = {
  stage1, stage2, approve, stage3, stage4, stage5, stage6,
  'stage5-manual': stage5Manual,
  'stage5-automation': stage5Automation,
  'stage5-execute': stage5Execute,
  'stage5-heal': stage5Heal,
  autonomous: autonomous
};

function initializeApp() {
  console.log('Initializing SDLC Agent UI...');

  document.querySelectorAll("button[data-action]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const action = btn.dataset.action;
      const originalText = btn.textContent;
      btn.disabled = true;

      // Add loading spinner
      if (!action.includes('approve')) {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + originalText;
      }

      try {
        await handlers[action]();
        // Success animation
        if (action.includes('stage')) {
          const stageNum = action.replace('stage', '');
          const card = document.getElementById(`stage${stageNum}`);
          if (card) {
            card.style.animation = 'none';
            setTimeout(() => {
              card.style.animation = 'fadeIn 0.5s ease-in';
            }, 10);
          }
        }
      }
      catch (e) {
        // Styled error notification with more details
        const errorMsg = e.message || e.toString();
        showNotification(`${action.toUpperCase()}: ${errorMsg}`, 'error');
        console.error('Action failed:', action, e);

        // Reset button state on error
        if (action.includes('stage')) {
          const stageNum = action.replace('stage', '');
          setStatus(stageNum, 'Error', 'fail');
        }
      }
      finally {
        // Only re-enable if button wasn't marked as completed by stage handler
        if (btn.dataset.completed !== "true") {
          btn.disabled = false;
        }
        btn.textContent = originalText;
      }
    });
  });

  console.log('✓ SDLC Agent UI initialized');
}

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeApp);
} else {
  // DOM already loaded
  initializeApp();
}

// Custom notification system
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.innerHTML = `
    <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
    <span>${message}</span>
  `;
  notification.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    background: ${type === 'error' ? 'rgba(255, 107, 107, 0.95)' : 'rgba(91, 157, 255, 0.95)'};
    color: white;
    padding: 16px 20px;
    border-radius: 10px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    z-index: 1000;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
    font-weight: 600;
    animation: slideIn 0.3s ease-out;
    max-width: 400px;
  `;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-in';
    setTimeout(() => notification.remove(), 300);
  }, 5000);
}

// Add animations for notifications (safely)
function addNotificationStyles() {
  if (document.head && !document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    addNotificationStyles();
    updateProgressBar();
  });
} else {
  addNotificationStyles();
  updateProgressBar();
}
