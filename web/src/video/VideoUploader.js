/**
 * VideoUploader - Handles video file upload and processing API integration
 */
class VideoUploader {
    constructor(config = {}) {
        this.apiBaseUrl = config.apiBaseUrl || 'http://localhost:5000/api';
        this.uploadElement = null;
        this.progressElement = null;
        this.progressFillElement = null;
        this.resultsElement = null;
        this.videoElement = null;
        this.overlayElement = null;
        
        // Upload state
        this.currentJobId = null;
        this.isUploading = false;
        this.isProcessing = false;
        
        // Callbacks
        this.onUploadProgress = null;
        this.onUploadComplete = null;
        this.onProcessingComplete = null;
        this.onError = null;
        
        // Supported video formats
        this.supportedFormats = ['mp4', 'avi', 'mov', 'webm'];
        
        this.init();
    }
    
    init() {
        // Get DOM elements
        this.uploadElement = document.getElementById('video-upload');
        this.progressElement = document.getElementById('upload-progress');
        this.progressFillElement = document.getElementById('upload-progress-fill');
        this.resultsElement = document.getElementById('analysis-results');
        this.videoElement = document.getElementById('analysis-video');
        this.overlayElement = document.getElementById('collision-overlay');
        
        if (this.uploadElement) {
            this.uploadElement.addEventListener('change', (e) => this.handleFileSelect(e));
        }
        
        // Hide progress bar initially
        if (this.progressElement) {
            this.progressElement.style.display = 'none';
        }
    }
    
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        // Validate file format
        if (!this.isValidVideoFile(file)) {
            this.showError('Invalid file format. Supported formats: MP4, AVI, MOV, WebM');
            return;
        }
        
        // Validate file size (500MB limit)
        const maxSize = 500 * 1024 * 1024; // 500MB
        if (file.size > maxSize) {
            this.showError('File too large. Maximum size is 500MB');
            return;
        }
        
        this.uploadVideo(file);
    }
    
    isValidVideoFile(file) {
        const extension = file.name.split('.').pop().toLowerCase();
        return this.supportedFormats.includes(extension);
    }
    
    async uploadVideo(file) {
        if (this.isUploading) {
            this.showError('Upload already in progress');
            return;
        }
        
        this.isUploading = true;
        this.showProgress(0);
        this.clearResults();
        
        try {
            const formData = new FormData();
            formData.append('video', file);
            
            const xhr = new XMLHttpRequest();
            
            // Track upload progress
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    this.updateProgress(percentComplete, 'Uploading...');
                    
                    if (this.onUploadProgress) {
                        this.onUploadProgress(percentComplete);
                    }
                }
            });
            
            // Handle upload completion
            xhr.addEventListener('load', () => {
                if (xhr.status === 201) {
                    const response = JSON.parse(xhr.responseText);
                    this.currentJobId = response.job_id;
                    this.updateProgress(100, 'Upload complete');
                    
                    if (this.onUploadComplete) {
                        this.onUploadComplete(response);
                    }
                    
                    // Start processing automatically
                    setTimeout(() => this.startProcessing(), 1000);
                } else {
                    const error = JSON.parse(xhr.responseText);
                    this.showError(`Upload failed: ${error.error}`);
                }
                this.isUploading = false;
            });
            
            // Handle upload errors
            xhr.addEventListener('error', () => {
                this.showError('Upload failed: Network error');
                this.isUploading = false;
            });
            
            // Send the request
            xhr.open('POST', `${this.apiBaseUrl}/upload`);
            xhr.send(formData);
            
        } catch (error) {
            this.showError(`Upload failed: ${error.message}`);
            this.isUploading = false;
        }
    }
    
    async startProcessing() {
        if (!this.currentJobId) {
            this.showError('No job ID available for processing');
            return;
        }
        
        if (this.isProcessing) {
            this.showError('Processing already in progress');
            return;
        }
        
        this.isProcessing = true;
        this.updateProgress(0, 'Starting video processing...');
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/process/${this.currentJobId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.updateProgress(10, 'Processing started...');
                
                // Poll for processing status
                this.pollProcessingStatus();
            } else {
                const error = await response.json();
                this.showError(`Processing failed: ${error.error}`);
                this.isProcessing = false;
            }
        } catch (error) {
            this.showError(`Processing failed: ${error.message}`);
            this.isProcessing = false;
        }
    }
    
    async pollProcessingStatus() {
        if (!this.currentJobId || !this.isProcessing) return;
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/status/${this.currentJobId}`);
            
            if (response.ok) {
                const status = await response.json();
                
                // Update progress based on status
                let progress = 10;
                let message = 'Processing...';
                
                switch (status.status) {
                    case 'processing':
                        progress = Math.min(90, 10 + (status.progress || 0) * 0.8);
                        message = `Processing video... ${Math.round(progress)}%`;
                        break;
                    case 'completed':
                        progress = 100;
                        message = 'Processing complete';
                        this.isProcessing = false;
                        this.handleProcessingComplete(status);
                        return;
                    case 'failed':
                        this.showError(`Processing failed: ${status.error || 'Unknown error'}`);
                        this.isProcessing = false;
                        return;
                }
                
                this.updateProgress(progress, message);
                
                // Continue polling if still processing
                if (this.isProcessing) {
                    setTimeout(() => this.pollProcessingStatus(), 2000);
                }
            } else {
                this.showError('Failed to get processing status');
                this.isProcessing = false;
            }
        } catch (error) {
            this.showError(`Status check failed: ${error.message}`);
            this.isProcessing = false;
        }
    }
    
    async handleProcessingComplete(status) {
        this.updateProgress(100, 'Loading results...');
        
        try {
            // Get detailed results
            const resultsResponse = await fetch(`${this.apiBaseUrl}/results/${this.currentJobId}`);
            const collisionResponse = await fetch(`${this.apiBaseUrl}/collisions/${this.currentJobId}`);
            
            if (resultsResponse.ok && collisionResponse.ok) {
                const results = await resultsResponse.json();
                const collisions = await collisionResponse.json();
                
                this.displayResults(results, collisions);
                
                if (this.onProcessingComplete) {
                    this.onProcessingComplete(results, collisions);
                }
            } else {
                this.showError('Failed to load processing results');
            }
        } catch (error) {
            this.showError(`Results loading failed: ${error.message}`);
        }
        
        this.hideProgress();
    }
    
    displayResults(results, collisions) {
        if (!this.resultsElement) return;
        
        const videoMetadata = results.video_metadata || {};
        const collisionResults = collisions.collision_results || {};
        const collisionEvents = collisionResults.collision_events || [];
        
        let html = `
            <div class="results-container">
                <h3>Analysis Results</h3>
                
                <div class="video-info">
                    <h4>Video Information</h4>
                    <p><strong>Duration:</strong> ${videoMetadata.duration || 'N/A'} seconds</p>
                    <p><strong>Frame Rate:</strong> ${videoMetadata.fps || 'N/A'} fps</p>
                    <p><strong>Resolution:</strong> ${videoMetadata.width || 'N/A'} x ${videoMetadata.height || 'N/A'}</p>
                    <p><strong>Total Frames:</strong> ${videoMetadata.total_frames || 'N/A'}</p>
                </div>
                
                <div class="collision-summary">
                    <h4>Collision Detection Summary</h4>
                    <p><strong>Total Collisions Detected:</strong> ${collisionEvents.length}</p>
                    <p><strong>Processing Time:</strong> ${results.results?.processing_time || 'N/A'} seconds</p>
                </div>
        `;
        
        if (collisionEvents.length > 0) {
            html += `
                <div class="collision-events">
                    <h4>Collision Events</h4>
                    <div class="events-list">
            `;
            
            collisionEvents.forEach((event, index) => {
                html += `
                    <div class="collision-event" data-timestamp="${event.timestamp}">
                        <h5>Collision ${index + 1}</h5>
                        <p><strong>Time:</strong> ${event.timestamp?.toFixed(2) || 'N/A'}s</p>
                        <p><strong>Severity:</strong> ${event.severity?.toFixed(2) || 'N/A'}</p>
                        <p><strong>Objects:</strong> ${event.object1?.class_name || 'Unknown'} vs ${event.object2?.class_name || 'Unknown'}</p>
                        <button class="jump-to-time" onclick="videoUploader.jumpToTime(${event.timestamp})">
                            Jump to Time
                        </button>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        } else {
            html += `
                <div class="no-collisions">
                    <p>No collisions detected in this video.</p>
                </div>
            `;
        }
        
        html += `</div>`;
        
        this.resultsElement.innerHTML = html;
        
        // Display collision overlay on video if available
        this.displayCollisionOverlay(collisionEvents);
    }
    
    displayCollisionOverlay(collisionEvents) {
        if (!this.overlayElement || !this.videoElement) return;
        
        // Clear existing overlay
        this.overlayElement.innerHTML = '';
        
        if (collisionEvents.length === 0) return;
        
        // Create overlay markers for each collision
        collisionEvents.forEach((event, index) => {
            const marker = document.createElement('div');
            marker.className = 'collision-marker';
            marker.innerHTML = `
                <div class="marker-dot"></div>
                <div class="marker-label">Collision ${index + 1}</div>
            `;
            marker.style.left = `${(event.collision_point?.x || 0.5) * 100}%`;
            marker.style.top = `${(event.collision_point?.y || 0.5) * 100}%`;
            marker.addEventListener('click', () => this.jumpToTime(event.timestamp));
            
            this.overlayElement.appendChild(marker);
        });
    }
    
    jumpToTime(timestamp) {
        if (this.videoElement && timestamp !== undefined) {
            this.videoElement.currentTime = timestamp;
            this.videoElement.play();
        }
    }
    
    showProgress(percent) {
        if (this.progressElement) {
            this.progressElement.style.display = 'block';
        }
        this.updateProgress(percent, 'Uploading...');
    }
    
    updateProgress(percent, message = '') {
        if (this.progressFillElement) {
            this.progressFillElement.style.width = `${percent}%`;
            this.progressFillElement.textContent = message;
        }
    }
    
    hideProgress() {
        if (this.progressElement) {
            this.progressElement.style.display = 'none';
        }
    }
    
    clearResults() {
        if (this.resultsElement) {
            this.resultsElement.innerHTML = '';
        }
        if (this.overlayElement) {
            this.overlayElement.innerHTML = '';
        }
    }
    
    showError(message) {
        if (this.onError) {
            this.onError(message);
        }
        
        if (this.resultsElement) {
            this.resultsElement.innerHTML = `
                <div class="error-message">
                    <h4>Error</h4>
                    <p>${message}</p>
                </div>
            `;
        }
        
        this.hideProgress();
        console.error('VideoUploader Error:', message);
    }
    
    // Public API methods
    setCallbacks(callbacks) {
        this.onUploadProgress = callbacks.onUploadProgress;
        this.onUploadComplete = callbacks.onUploadComplete;
        this.onProcessingComplete = callbacks.onProcessingComplete;
        this.onError = callbacks.onError;
    }
    
    getCurrentJobId() {
        return this.currentJobId;
    }
    
    isCurrentlyUploading() {
        return this.isUploading;
    }
    
    isCurrentlyProcessing() {
        return this.isProcessing;
    }
    
    reset() {
        this.currentJobId = null;
        this.isUploading = false;
        this.isProcessing = false;
        this.clearResults();
        this.hideProgress();
        
        if (this.uploadElement) {
            this.uploadElement.value = '';
        }
    }
}

// Global instance for easy access
let videoUploader = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    videoUploader = new VideoUploader();
});