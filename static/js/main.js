// State
let currentPrediction = null;

// Constants - matching backend class colors
const CLASS_COLORS = {
    'Comminuted': '#FF4444',
    'Greenstick': '#44FF44',
    'Linear': '#4444FF',
    'Oblique Displaced': '#FF8C00',
    'Oblique': '#FFD700',
    'Segmental': '#FF69B4',
    'Spiral': '#00CED1',
    'Transverse Displaced': '#9370DB',
    'Transverse': '#20B2AA',
    'Healthy': '#00FF7F'
};

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupUpload();
    loadHistory();
    setupTabs();

    document.getElementById('new-analysis-btn').addEventListener('click', resetToUpload);

    document.getElementById('download-png-btn').addEventListener('click', () => {
        if (currentPrediction) downloadResult(currentPrediction.id, 'png');
    });

    document.getElementById('download-dicom-btn').addEventListener('click', () => {
        if (currentPrediction) downloadResult(currentPrediction.id, 'dicom');
    });
});

// ==================== NAVIGATION ====================
function setupNavigation() {
    const navbar = document.getElementById('navbar');
    const mobileBtn = document.querySelector('.mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    const links = document.querySelectorAll('.nav-link, .mobile-link');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.style.padding = '0.5rem 0';
            navbar.style.background = 'rgba(10, 15, 30, 0.95)';
        } else {
            navbar.style.padding = '1rem 0';
            navbar.style.background = 'rgba(10, 15, 30, 0.8)';
        }
    });

    mobileBtn.addEventListener('click', () => {
        mobileMenu.classList.toggle('active');
        const icon = mobileBtn.querySelector('i');
        if (mobileMenu.classList.contains('active')) {
            icon.classList.remove('fa-bars');
            icon.classList.add('fa-xmark');
        } else {
            icon.classList.remove('fa-xmark');
            icon.classList.add('fa-bars');
        }
    });

    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            mobileMenu.classList.remove('active');
            const mbIcon = mobileBtn.querySelector('i');
            mbIcon.classList.remove('fa-xmark');
            mbIcon.classList.add('fa-bars');

            const targetId = link.getAttribute('href').substring(1);
            const target = document.getElementById(targetId);
            if (target) {
                window.scrollTo({
                    top: target.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// ==================== UPLOAD ====================
function setupUpload() {
    const zone = document.getElementById('upload-zone');
    const input = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');

    browseBtn.addEventListener('click', () => input.click());

    input.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFile(e.target.files[0]);
            e.target.value = ''; // Reset input
        }
    });

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    ['dragenter', 'dragover'].forEach(evt => {
        zone.addEventListener(evt, () => zone.classList.add('dragover'));
    });

    ['dragleave', 'drop'].forEach(evt => {
        zone.addEventListener(evt, () => zone.classList.remove('dragover'));
    });

    zone.addEventListener('drop', (e) => {
        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });
}

function handleFile(file) {
    const validExts = ['.png', '.dcm', '.dicom'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!validExts.includes(ext)) {
        showToast('Định dạng tệp không được hỗ trợ. Vui lòng dùng PNG hoặc DICOM.', 'error');
        return;
    }

    if (file.size > 50 * 1024 * 1024) {
        showToast('Kích thước tệp quá lớn (Tối đa 50MB)', 'error');
        return;
    }

    showLoading();

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/predict', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            currentPrediction = data.prediction;
            showResult(data.prediction);
            showToast('Phân tích thành công!', 'success');
            loadHistory(); // Refresh history
        } else {
            showToast('Lỗi: ' + (data.error || 'Không thể phân tích ảnh'), 'error');
        }
    })
    .catch(err => {
        hideLoading();
        console.error('Predict error:', err);
        showToast('Lỗi kết nối đến server. Vui lòng thử lại.', 'error');
    });
}

// ==================== RESULT DISPLAY ====================
function showResult(prediction) {
    document.getElementById('upload-container').style.display = 'none';
    const resultSection = document.getElementById('result-section');
    resultSection.style.display = 'block';

    // Use original preview from server (works for both PNG and DICOM)
    document.getElementById('original-image').src = prediction.original_image_url || prediction.result_image_url;

    // Show result image with bounding boxes
    document.getElementById('result-image').src = prediction.result_image_url;

    // Detection list
    const list = document.getElementById('detection-list');
    list.innerHTML = '';

    const healthyMsg = document.getElementById('healthy-message');
    const detections = prediction.detections || [];

    // Check if only "Healthy" class detected
    const hasOnlyHealthy = detections.length > 0 && detections.every(d => d.class_name === 'Healthy');
    const fractureDetections = detections.filter(d => d.class_name !== 'Healthy');

    if (detections.length === 0) {
        healthyMsg.style.display = 'flex';
        document.querySelector('.summary-header').style.display = 'none';
        document.getElementById('total-detections').textContent = '0';
    } else if (hasOnlyHealthy) {
        healthyMsg.style.display = 'flex';
        document.querySelector('.summary-header').style.display = 'none';
        document.getElementById('total-detections').textContent = '0';
    } else {
        healthyMsg.style.display = 'none';
        document.querySelector('.summary-header').style.display = 'flex';
        document.getElementById('total-detections').textContent = fractureDetections.length;
    }

    // Render all detections
    detections.forEach((det, index) => {
        const color = CLASS_COLORS[det.class_name] || '#999';
        const nameVi = det.class_name_vi || det.class_name;
        const pct = Math.round(det.confidence * 100);

        let confColor = 'var(--success)';
        if (pct < 50) confColor = 'var(--danger)';
        else if (pct < 80) confColor = 'var(--warning)';

        const card = document.createElement('div');
        card.className = 'detection-card';
        card.style.borderLeftColor = color;
        card.style.animation = `slideUp 0.3s ease ${index * 0.1}s both`;
        card.innerHTML = `
            <div class="detection-info">
                <span class="detection-class">${nameVi} <span class="badge" style="background:${color}">${det.class_name}</span></span>
                <span class="detection-conf">${pct}%</span>
            </div>
            <div class="confidence-bar-wrapper">
                <div class="confidence-bar" style="width: 0%; background: ${confColor}"></div>
            </div>
        `;
        list.appendChild(card);

        // Animate confidence bar
        setTimeout(() => {
            card.querySelector('.confidence-bar').style.width = pct + '%';
        }, 100 + index * 100);
    });

    // Show/hide DICOM download button
    const dicomBtn = document.getElementById('download-dicom-btn');
    dicomBtn.style.display = 'inline-flex';

    // Scroll to results
    window.scrollTo({
        top: resultSection.offsetTop - 80,
        behavior: 'smooth'
    });
}

function resetToUpload() {
    document.getElementById('result-section').style.display = 'none';
    document.getElementById('upload-container').style.display = 'block';
    currentPrediction = null;
    window.scrollTo({
        top: document.getElementById('detection').offsetTop - 80,
        behavior: 'smooth'
    });
}

// ==================== HISTORY ====================
function loadHistory() {
    fetch('/api/history')
    .then(response => response.json())
    .then(data => {
        renderHistory(data);
    })
    .catch(err => {
        console.error('History error:', err);
        renderHistory([]);
    });
}

function renderHistory(items) {
    const grid = document.getElementById('history-grid');
    const empty = document.getElementById('history-empty');

    if (!items || items.length === 0) {
        grid.style.display = 'none';
        empty.style.display = 'block';
        return;
    }

    grid.style.display = 'grid';
    empty.style.display = 'none';
    grid.innerHTML = '';

    items.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'history-card';
        card.style.animation = `slideUp 0.3s ease ${index * 0.05}s both`;

        const date = formatDate(item.created_at);
        const fractureCount = item.detections
            ? item.detections.filter(d => d.class_name !== 'Healthy').length
            : item.num_detections;

        card.innerHTML = `
            <img src="${item.result_image_url}" class="history-img" alt="Kết quả nhận diện" loading="lazy">
            <div class="history-details">
                <h4 class="history-title" title="${item.filename}">${truncateFilename(item.filename, 30)}</h4>
                <div class="history-meta">
                    <span><i class="fa-solid fa-bone-break fa-solid fa-crosshairs"></i> ${fractureCount} phát hiện</span>
                    <span><i class="fa-regular fa-clock"></i> ${date}</span>
                </div>
                <div class="history-actions">
                    <div class="download-dropdown">
                        <button class="btn btn-outline btn-sm download-toggle-btn" onclick="toggleDownloadMenu(this)">
                            <i class="fa-solid fa-download"></i> Tải về ▾
                        </button>
                        <div class="download-menu" style="display:none;">
                            <button onclick="downloadResult(${item.id}, 'png'); closeDownloadMenus();">
                                <i class="fa-solid fa-image"></i> Tải PNG
                            </button>
                            <button onclick="downloadResult(${item.id}, 'dicom'); closeDownloadMenus();">
                                <i class="fa-solid fa-file-medical"></i> Tải DICOM
                            </button>
                        </div>
                    </div>
                    <button class="btn btn-outline btn-sm btn-delete" onclick="deleteHistoryItem(${item.id})">
                        <i class="fa-regular fa-trash-can"></i> Xóa
                    </button>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

// ==================== DOWNLOAD ====================
function downloadResult(id, format) {
    showToast(`Đang chuẩn bị tải file ${format.toUpperCase()}...`, 'success');
    window.open(`/api/download/${id}?format=${format}`, '_blank');
}

window.downloadResult = downloadResult;

// Download menu toggle
function toggleDownloadMenu(btn) {
    closeDownloadMenus();
    const menu = btn.nextElementSibling;
    menu.style.display = menu.style.display === 'none' ? 'flex' : 'none';
}

function closeDownloadMenus() {
    document.querySelectorAll('.download-menu').forEach(m => m.style.display = 'none');
}

window.toggleDownloadMenu = toggleDownloadMenu;
window.closeDownloadMenus = closeDownloadMenus;

// Close menus when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.download-dropdown')) {
        closeDownloadMenus();
    }
});

// ==================== DELETE ====================
function deleteHistoryItem(id) {
    if (!confirm('Bạn có chắc chắn muốn xóa kết quả này khỏi lịch sử?')) return;

    fetch(`/api/delete/${id}`, { method: 'DELETE' })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Đã xóa thành công!', 'success');
            loadHistory();
        } else {
            showToast('Lỗi khi xóa: ' + (data.error || 'Không xác định'), 'error');
        }
    })
    .catch(err => {
        console.error('Delete error:', err);
        showToast('Lỗi kết nối server', 'error');
    });
}

window.deleteHistoryItem = deleteHistoryItem;

// ==================== TABS ====================
function setupTabs() {
    const btns = document.querySelectorAll('.tab-btn');
    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            btns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.contact-content').forEach(c => c.style.display = 'none');
            document.getElementById(btn.dataset.target + '-content').style.display = 'block';
        });
    });
}

// ==================== LOADING ====================
function showLoading() {
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}

// ==================== TOAST ====================
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'fa-circle-check';
    if (type === 'error') icon = 'fa-circle-xmark';
    if (type === 'warning') icon = 'fa-triangle-exclamation';

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==================== UTILITY FUNCTIONS ====================
function formatDate(dateString) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('vi-VN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch {
        return dateString;
    }
}

function truncateFilename(name, maxLen) {
    if (!name || name.length <= maxLen) return name;
    const ext = name.substring(name.lastIndexOf('.'));
    const base = name.substring(0, name.lastIndexOf('.'));
    const truncated = base.substring(0, maxLen - ext.length - 3);
    return truncated + '...' + ext;
}
