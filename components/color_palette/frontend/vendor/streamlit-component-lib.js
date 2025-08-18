// Minimal inline Streamlit Component Library (compatible with 1.44.1)
// Based on streamlit-component-lib patterns but self-contained
(function() {
  'use strict';

  // Event types
  const RENDER_EVENT = 'streamlit:render';

  // Create event target for component events
  const eventTarget = document.createElement('div');

  // Main Streamlit object
  window.Streamlit = {
    RENDER_EVENT: RENDER_EVENT,

    events: {
      addEventListener: function(type, listener) {
        eventTarget.addEventListener(type, listener);
      },
      removeEventListener: function(type, listener) {
        eventTarget.removeEventListener(type, listener);
      }
    },

    setComponentReady: function() {
      const msg = {
        isStreamlitMessage: true,
        type: 'streamlit:componentReady',
        apiVersion: 1
      };
      window.parent.postMessage(msg, '*');
      // Also try with explicit origin for stricter parent policies
      try {
        const origin = new URL(window.location.href).origin;
        window.parent.postMessage(msg, origin);
      } catch(e) {}
    },

    setComponentValue: function(value) {
      const msg = {
        isStreamlitMessage: true,
        type: 'streamlit:setComponentValue',
        value: value
      };
      if (window.__streamlitComponentId) {
        msg.componentId = window.__streamlitComponentId;
      }
      window.parent.postMessage(msg, '*');
    },

    setFrameHeight: function(height) {
      const msg = {
        isStreamlitMessage: true,
        type: 'streamlit:setFrameHeight',
        height: height
      };
      if (window.__streamlitComponentId) {
        msg.componentId = window.__streamlitComponentId;
      }
      window.parent.postMessage(msg, '*');
    }
  };

  // Listen for render messages from parent
  window.addEventListener('message', function(event) {
    const data = event.data;
    if (data && data.isStreamlitMessage) {
      if (data.type === 'streamlit:render') {
        // Store component ID for future messages
        if (data.componentId) {
          window.__streamlitComponentId = data.componentId;
        }
        const renderEvent = new CustomEvent(RENDER_EVENT, {
          detail: data
        });
        eventTarget.dispatchEvent(renderEvent);
      }
    }
  });

})();