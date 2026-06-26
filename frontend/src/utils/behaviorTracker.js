/**
 * AI Privacy & Behavioral Intelligence Engine - Frontend Tracker
 * Tracks mouse velocity, click rates, typing flight times, and session durations
 * to compute a continuous vector payload for the backend IsolationForest / KMeans models.
 */

const API_URL = import.meta.env.VITE_API_URL || 'https://psi-resume-analyser.onrender.com';
const CLEAN_BASE = API_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');
const ENDPOINT = `${CLEAN_BASE}/api/identity/telemetry`;

class BehaviorTracker {
    constructor() {
        this.sessionId = Math.random().toString(36).substring(2, 15);
        this.startTime = Date.now();
        
        // Mouse tracking
        this.lastMouseX = -1;
        this.lastMouseY = -1;
        this.lastMouseTime = Date.now();
        this.totalMouseDistance = 0;
        
        // Click tracking
        this.clickCount = 0;
        
        // Keyboard tracking
        this.keyStrokes = 0;
        this.totalFlightTime = 0;
        this.lastKeyUpTime = 0;
        
        // Error tracking
        this.errorCount = 0;
        
        this.browserHash = this.generateBrowserHash();
        
        this.initListeners();
        
        // Sync every 30 seconds
        this.syncInterval = setInterval(() => this.syncTelemetry(), 30000);
    }
    
    generateBrowserHash() {
        // Simple hash of standard navigator properties to mimic Device Fingerprinting
        const fp = `${navigator.userAgent}-${navigator.language}-${screen.width}x${screen.height}-${new Date().getTimezoneOffset()}`;
        let hash = 0;
        for (let i = 0; i < fp.length; i++) {
            const char = fp.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash.toString();
    }
    
    initListeners() {
        window.addEventListener('mousemove', (e) => {
            const now = Date.now();
            if (this.lastMouseX !== -1) {
                const dx = e.clientX - this.lastMouseX;
                const dy = e.clientY - this.lastMouseY;
                this.totalMouseDistance += Math.sqrt(dx * dx + dy * dy);
            }
            this.lastMouseX = e.clientX;
            this.lastMouseY = e.clientY;
            this.lastMouseTime = now;
        });
        
        window.addEventListener('click', () => {
            this.clickCount++;
        });
        
        window.addEventListener('keydown', (e) => {
            if (this.lastKeyUpTime > 0) {
                const flightTime = Date.now() - this.lastKeyUpTime;
                if (flightTime < 2000) { // Only count continuous typing
                    this.totalFlightTime += flightTime;
                    this.keyStrokes++;
                }
            }
        });
        
        window.addEventListener('keyup', () => {
            this.lastKeyUpTime = Date.now();
        });
        
        window.addEventListener('error', () => {
            this.errorCount++;
        });
    }
    
    getTelemetryPayload() {
        const sessionDuration = (Date.now() - this.startTime) / 1000;
        
        // Metrics
        const mouseSpeed = sessionDuration > 0 ? this.totalMouseDistance / sessionDuration : 0;
        const clickRate = sessionDuration > 0 ? this.clickCount / sessionDuration : 0;
        const typingSpeed = this.keyStrokes > 0 ? this.totalFlightTime / this.keyStrokes : 0; // Avg flight time
        const errorRate = sessionDuration > 0 ? this.errorCount / sessionDuration : 0;
        
        return {
            session_id: this.sessionId,
            mouse_speed: mouseSpeed,
            click_rate: clickRate,
            typing_speed: typingSpeed,
            error_rate: errorRate,
            session_duration: sessionDuration,
            browser_hash: this.browserHash
        };
    }
    
    async syncTelemetry() {
        const payload = this.getTelemetryPayload();
        try {
            const res = await fetch(ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            // Dispatch event with Risk Score so UI can react (e.g. block bot)
            const event = new CustomEvent('telemetrySync', { detail: data });
            window.dispatchEvent(event);
            
            if (data.is_bot) {
                console.warn(`[AI Identity] Bot behavior detected. Risk Score: ${data.risk_score}`);
            } else {
                console.log(`[AI Identity] Human confirmed. Cluster: ${data.user_cluster}. Risk: ${data.risk_score}`);
            }
        } catch (e) {
            console.error('[AI Identity] Telemetry sync failed', e);
        }
    }
}

// Export a singleton instance
export const behaviorTracker = new BehaviorTracker();
