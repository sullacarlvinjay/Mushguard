// Base JavaScript for Mushroom Detector Application

// Loading overlay functions
function showLoading() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.style.display = 'flex';
    }
}

function hideLoading() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add loading state to form submission
    const form = document.getElementById('upload-form');
    if (form) {
        form.addEventListener('submit', function() {
            showLoading();
        });
    }

    // Mode toggle handling for home page
    const uploadModeBtn = document.getElementById('upload-mode-btn');
    const cameraModeBtn = document.getElementById('camera-mode-btn');
    const uploadMode = document.getElementById('upload-mode');
    const cameraMode = document.getElementById('camera-mode');
    let stream = null;

    if (uploadModeBtn && cameraModeBtn) {
        function switchToUploadMode() {
            uploadModeBtn.classList.add('active');
            cameraModeBtn.classList.remove('active');
            if (uploadMode) uploadMode.style.display = 'block';
            if (cameraMode) cameraMode.style.display = 'none';
            
            // Stop camera if running
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                stream = null;
            }
            const startCameraBtn = document.getElementById('start-camera');
            const capturePhotoBtn = document.getElementById('capture-photo');
            if (startCameraBtn) {
                startCameraBtn.disabled = false;
                startCameraBtn.innerHTML = '<i class="fas fa-camera"></i> Start Camera';
            }
            if (capturePhotoBtn) capturePhotoBtn.disabled = true;
        }

        function switchToCameraMode() {
            cameraModeBtn.classList.add('active');
            uploadModeBtn.classList.remove('active');
            if (cameraMode) cameraMode.style.display = 'block';
            if (uploadMode) uploadMode.style.display = 'none';
        }

        uploadModeBtn.addEventListener('click', switchToUploadMode);
        cameraModeBtn.addEventListener('click', switchToCameraMode);
    }

    // File upload handling
    const fileInput = document.querySelector('input[type="file"]');
    const previewContainer = document.querySelector('#upload-mode .image-preview-container');
    const previewImage = document.getElementById('image-preview');

    if (fileInput && previewContainer && previewImage) {
        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImage.src = e.target.result;
                    previewContainer.style.display = 'block';
                }
                reader.readAsDataURL(file);
            } else {
                previewContainer.style.display = 'none';
            }
        });
    }

    // Camera handling
    const video = document.getElementById('camera-feed');
    const canvas = document.getElementById('camera-canvas');
    const startButton = document.getElementById('start-camera');
    const captureButton = document.getElementById('capture-photo');
    const cameraPreview = document.getElementById('camera-preview');
    const cameraPreviewContainer = document.querySelector('#camera-mode .image-preview-container');
    const cameraForm = document.getElementById('camera-form');
    const cameraImageInput = document.getElementById('camera-image-input');

    // Start camera
    if (startButton) {
        startButton.addEventListener('click', async function() {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        facingMode: 'environment',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    } 
                });
                if (video) video.srcObject = stream;
                startButton.disabled = true;
                if (captureButton) captureButton.disabled = false;
                startButton.innerHTML = '<i class="fas fa-camera"></i> Camera Running';
            } catch (err) {
                console.error('Error accessing camera:', err);
                alert('Error accessing camera. Please make sure you have granted camera permissions.');
            }
        });
    }

    // Capture photo
    if (captureButton && video && canvas) {
        captureButton.addEventListener('click', function() {
            if (!stream) return;

            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
        
            const context = canvas.getContext('2d');
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            canvas.toBlob(function(blob) {
                const file = new File([blob], 'camera-photo.jpg', { type: 'image/jpeg' });
                const url = URL.createObjectURL(blob);
                if (cameraPreview) cameraPreview.src = url;
                if (cameraPreviewContainer) cameraPreviewContainer.style.display = 'block';
                if (cameraImageInput) cameraImageInput.value = url;
            }, 'image/jpeg', 0.95);
        });
    }

    // Handle camera form submission
    if (cameraForm && cameraImageInput) {
        cameraForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!cameraImageInput.value) {
                alert('Please capture a photo first');
                return;
            }

            // Convert the blob URL back to a blob and create a File
            fetch(cameraImageInput.value)
                .then(res => res.blob())
                .then(blob => {
                    const formData = new FormData();
                    // Create a File object from the blob
                    const file = new File([blob], 'camera-photo.jpg', { type: 'image/jpeg' });
                    // Append the file with the same name as the upload form ('image')
                    formData.append('image', file);
                    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
                    if (csrfToken) {
                        formData.append('csrfmiddlewaretoken', csrfToken.value);
                    }

                    // Submit using the same endpoint as the upload form
                    fetch(window.location.href, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    })
                    .then(response => {
                        if (response.ok) {
                            // Instead of reloading, let's handle the response
                            return response.text().then(html => {
                                // Update the result section
                                const parser = new DOMParser();
                                const doc = parser.parseFromString(html, 'text/html');
                                const newResult = doc.querySelector('.analysis-result');
                                const currentResult = document.querySelector('.analysis-result');
                                
                                if (currentResult && newResult) {
                                    currentResult.replaceWith(newResult);
                                } else if (newResult) {
                                    const inputContainer = document.querySelector('.input-container');
                                    if (inputContainer) {
                                        inputContainer.insertAdjacentElement('afterend', newResult);
                                    }
                                }

                                // Helper: ensure Leaflet CSS is present if referenced
                                function ensureLeafletCSS(docRoot) {
                                    const href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
                                    const already = Array.from(document.querySelectorAll('link[rel="stylesheet"]')).some(l => l.href && l.href.includes('leaflet'));
                                    if (!already) {
                                        const link = document.createElement('link');
                                        link.rel = 'stylesheet';
                                        link.href = href;
                                        document.head.appendChild(link);
                                    }
                                }

                                // Helper: load external script and return a promise
                                function loadScript(src) {
                                    return new Promise((resolve, reject) => {
                                        const s = document.createElement('script');
                                        s.src = src;
                                        s.async = true;
                                        s.onload = resolve;
                                        s.onerror = reject;
                                        document.body.appendChild(s);
                                    });
                                }

                                // Execute scripts contained in the injected HTML
                                async function executeScriptsFrom(container) {
                                    if (!container) return;
                                    // Load any Leaflet CSS if needed
                                    ensureLeafletCSS(document);

                                    const scripts = container.querySelectorAll('script');
                                    for (const sc of scripts) {
                                        if (sc.src) {
                                            // If Leaflet and other libs are already loaded, this will be quick
                                            try {
                                                await loadScript(sc.src);
                                            } catch (e) {
                                                console.error('Failed loading script:', sc.src, e);
                                            }
                                        } else {
                                            const inline = document.createElement('script');
                                            if (sc.textContent) inline.textContent = sc.textContent;
                                            document.body.appendChild(inline);
                                        }
                                    }
                                }

                                // Run any scripts inside the newly injected result (needed for Leaflet map init)
                                const injected = document.querySelector('.analysis-result');
                                executeScriptsFrom(injected);
                                
                                // Reset camera preview
                                if (cameraPreviewContainer) cameraPreviewContainer.style.display = 'none';
                                cameraImageInput.value = '';
                                
                                // Reset camera controls
                                if (stream) {
                                    stream.getTracks().forEach(track => track.stop());
                                    stream = null;
                                }
                                if (startButton) {
                                    startButton.disabled = false;
                                    startButton.innerHTML = '<i class="fas fa-camera"></i> Start Camera';
                                }
                                if (captureButton) captureButton.disabled = true;
                            });
                        } else {
                            throw new Error('Network response was not ok');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Error submitting photo. Please try again.');
                    });
                });
        });
    }

    // Clean up camera stream when leaving the page
    window.addEventListener('beforeunload', function() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
    });

    // Tab functionality for analyze page
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const tabId = tab.dataset.tab;
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            const targetPane = document.getElementById(`${tabId}-tab`);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        });
    });

    // Drag and drop functionality for index page
    const dropZone = document.getElementById('dropZone');
    const fileInputIndex = document.getElementById('fileInput');
    const loadingIndex = document.getElementById('loading');
    const resultCard = document.getElementById('resultCard');
    const resultContent = document.getElementById('resultContent');

    if (dropZone && fileInputIndex) {
        // Handle drag and drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = '#0d6efd';
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = '#dee2e6';
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = '#dee2e6';
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                handleFile(file);
            }
        });

        // Handle click to upload
        dropZone.addEventListener('click', () => {
            fileInputIndex.click();
        });

        fileInputIndex.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                handleFile(file);
            }
        });

        function handleFile(file) {
            const formData = new FormData();
            formData.append('image', file);

            // Show loading
            if (loadingIndex) loadingIndex.style.display = 'block';
            if (resultCard) resultCard.style.display = 'none';

            // Send to server
            fetch('/analyze/', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (loadingIndex) loadingIndex.style.display = 'none';
                if (resultCard) resultCard.style.display = 'block';
                
                let resultHtml = '';
                
                // Edibility result
                const edibilityClass = data.is_edible ? 'text-success' : 'text-danger';
                const edibilityLabel = data.is_edible ? 'EDIBLE' : 'POISONOUS';
                resultHtml += `
                    <div class="mb-3">
                        <h6 class="${edibilityClass}">🧪 Edibility: ${edibilityLabel} (${(data.edibility_confidence * 100).toFixed(2)}%)</h6>
                    </div>
                `;

                // Species result (if edible)
                if (data.is_edible && data.species) {
                    resultHtml += `
                        <div class="mb-3">
                            <h6>🍄 Species: ${data.species} (${(data.species_confidence * 100).toFixed(2)}%)</h6>
                        </div>
                        <div class="mb-3">
                            <h6>🕒 Shelf Life: ${data.lifespan}</h6>
                        </div>
                        <div class="mb-3">
                            <h6>❄️ Preservation Tips: ${data.preservation}</h6>
                        </div>
                    `;
                } else if (!data.is_edible) {
                    resultHtml += `
                        <div class="alert alert-warning">
                            ⚠️ Species identification skipped (not edible)
                        </div>
                    `;
                }

                if (resultContent) resultContent.innerHTML = resultHtml;
            })
            .catch(error => {
                if (loadingIndex) loadingIndex.style.display = 'none';
                if (resultCard) resultCard.style.display = 'block';
                if (resultContent) {
                    resultContent.innerHTML = `
                        <div class="alert alert-danger">
                            Error analyzing image: ${error.message}
                        </div>
                    `;
                }
            });
        }
    }

    // Animated Counter for Statistics
    function animateCounter(element, target, duration = 2000) {
        if (!element || target === 0) {
            element.textContent = '0';
            return;
        }
        
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, 16);
    }

    // Intersection Observer for Scroll Animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                
                // Trigger counter animation for statistics
                if (entry.target.classList.contains('stat-item')) {
                    const statNumber = entry.target.querySelector('.stat-number');
                    if (statNumber) {
                        const target = parseInt(statNumber.getAttribute('data-target')) || 0;
                        animateCounter(statNumber, target);
                    }
                }
                
                // Remove observer after animation
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe elements for scroll animations
    document.querySelectorAll('.stat-item, .card, .feature-card, .hero-content').forEach(el => {
        el.classList.add('animate-on-scroll');
        observer.observe(el);
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Parallax effect for hero section
    window.addEventListener('scroll', () => {
        const heroSection = document.querySelector('.hero-section');
        if (heroSection) {
            const scrolled = window.pageYOffset;
            const rate = scrolled * 0.5;
            heroSection.style.transform = `translateY(${rate}px)`;
        }
    });

    // PWA install button handling
    let deferredPrompt = null;
    const installButton = document.getElementById('install-app-btn');

    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;

        if (installButton) {
            installButton.style.display = 'inline-block';
        }
    });

    if (installButton) {
        installButton.addEventListener('click', async () => {
            if (!deferredPrompt) {
                // No install prompt available yet; just do nothing.
                return;
            }

            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;

            if (outcome === 'accepted') {
                installButton.style.display = 'none';
            }

            deferredPrompt = null;
        });
    }

    window.addEventListener('appinstalled', () => {
        if (installButton) {
            installButton.style.display = 'none';
        }
    });
});