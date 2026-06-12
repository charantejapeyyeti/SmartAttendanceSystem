/* static/js/main.js */

// Global App State
let activeTab = 'overview';
let activeStream = false;
let webrtcStream = null;
let captureInterval = null;
let currentRegStudentId = null;
let analyticsChart = null;
let logPollingInterval = null;

// Clock initialization
function updateClock() {
  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0];
  document.getElementById('sidebar-time').textContent = timeStr;
}
setInterval(updateClock, 1000);
updateClock();

// Tab Switcher
function switchTab(tabId) {
  // Deactivate current tab
  document.querySelector(`.nav-link[data-tab="${activeTab}"]`)?.classList.remove('active');
  document.getElementById(activeTab)?.classList.remove('active');
  
  // Stop streams if moving away from camera tabs
  if (activeTab === 'tracker' && tabId !== 'tracker') {
    stopAttendanceStream();
  }
  if (activeTab === 'register' && tabId !== 'register') {
    stopWebcamCapture();
  }
  
  // Activate new tab
  activeTab = tabId;
  const newLink = document.querySelector(`.nav-link[data-tab="${tabId}"]`);
  if (newLink) newLink.classList.add('active');
  
  const newSection = document.getElementById(tabId);
  if (newSection) newSection.classList.add('active');
  
  // Trigger tab-specific loaders
  if (tabId === 'overview') {
    loadDashboardData();
  } else if (tabId === 'directory') {
    loadStudentDirectory();
  } else if (tabId === 'risk') {
    loadFlaggedStudents();
  }
}

// Attach Tab Navigation Event Listeners
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', (e) => {
    const tabId = link.getAttribute('data-tab');
    switchTab(tabId);
  });
});

/* ==========================================================================
   1. OVERVIEW DASHBOARD LOGIC
   ========================================================================== */
function loadDashboardData() {
  // Fetch stats
  fetch('/api/stats')
    .then(res => res.json())
    .then(data => {
      document.getElementById('stat-students').textContent = data.total_students;
      document.getElementById('stat-days').textContent = data.total_days;
      document.getElementById('stat-avg-attendance').textContent = data.avg_attendance + '%';
      document.getElementById('stat-risk').textContent = data.at_risk_students;
    })
    .catch(err => console.error("Error loading stats:", err));

  // Fetch recent logs
  fetch('/api/attendance')
    .then(res => res.json())
    .then(logs => {
      const tbody = document.querySelector('#recent-logs-table tbody');
      tbody.innerHTML = '';
      
      if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No attendance logged yet.</td></tr>`;
        return;
      }
      
      logs.forEach(log => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>${log.student_id}</td>
          <td><strong>${log.name}</strong></td>
          <td>${log.date}</td>
          <td>${log.time}</td>
          <td><span class="badge success">Present</span></td>
        `;
        tbody.appendChild(row);
      });
    })
    .catch(err => console.error("Error loading logs:", err));
    
  // Load Chart Analytics
  loadCharts();
}

function loadCharts() {
  fetch('/api/students')
    .then(res => res.json())
    .then(students => {
      const names = students.map(s => s.name);
      const rates = students.map(s => s.attendance_percentage);
      const colors = students.map(s => s.risk_status === 'Fail' ? 'rgba(244, 63, 94, 0.6)' : 'rgba(16, 185, 129, 0.6)');
      const borders = students.map(s => s.risk_status === 'Fail' ? '#f43f5e' : '#10b981');
      
      if (analyticsChart) {
        analyticsChart.destroy();
      }
      
      const ctx = document.getElementById('attendanceChart').getContext('2d');
      analyticsChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: names,
          datasets: [{
            label: 'Attendance Rate (%)',
            data: rates,
            backgroundColor: colors,
            borderColor: borders,
            borderWidth: 1.5,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#94a3b8' }
            },
            x: {
              grid: { display: false },
              ticks: { color: '#94a3b8' }
            }
          }
        }
      });
    })
    .catch(err => console.error("Error drawing charts:", err));
}

/* ==========================================================================
   2. LIVE STREAM TRACKER LOGIC
   ========================================================================== */
const btnStartStream = document.getElementById('btn-start-stream');
const btnStopStream = document.getElementById('btn-stop-stream');
const videoStreamImg = document.getElementById('video-stream');
const videoContainer = document.getElementById('video-feed-container');

btnStartStream.addEventListener('click', startAttendanceStream);
btnStopStream.addEventListener('click', stopAttendanceStream);

function startAttendanceStream() {
  // Set MJPEG source
  videoStreamImg.src = '/api/video_feed';
  videoContainer.classList.add('camera-active');
  
  btnStartStream.disabled = true;
  btnStopStream.disabled = false;
  activeStream = true;
  
  // Start polling session logs
  pollSessionLogs();
  logPollingInterval = setInterval(pollSessionLogs, 2000);
}

function stopAttendanceStream() {
  // Call server to release camera
  fetch('/api/stop_camera', { method: 'POST' })
    .then(res => res.json())
    .then(() => {
      videoStreamImg.removeAttribute('src');
      videoContainer.classList.remove('camera-active');
      btnStartStream.disabled = false;
      btnStopStream.disabled = true;
      activeStream = false;
      
      clearInterval(logPollingInterval);
    })
    .catch(err => console.error("Error stopping camera feed:", err));
}

function pollSessionLogs() {
  fetch('/api/attendance')
    .then(res => res.json())
    .then(logs => {
      const todayStr = new Date().toISOString().split('T')[0];
      const tbody = document.querySelector('#session-logs-table tbody');
      tbody.innerHTML = '';
      
      // Filter for logs captured today
      const todayLogs = logs.filter(log => log.date === todayStr);
      
      if (todayLogs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No student detected in today's active session.</td></tr>`;
        return;
      }
      
      todayLogs.forEach(log => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>${log.time}</td>
          <td><strong>${log.name}</strong></td>
          <td><span class="badge success">Present</span></td>
        `;
        tbody.appendChild(row);
      });
    })
    .catch(err => console.error("Error polling session logs:", err));
}

/* ==========================================================================
   3. STUDENT DIRECTORY LOGIC
   ========================================================================== */
function loadStudentDirectory() {
  fetch('/api/students')
    .then(res => res.json())
    .then(students => {
      renderDirectoryTable(students);
      
      // Search functionality
      const searchInput = document.getElementById('search-students');
      searchInput.oninput = function() {
        const val = searchInput.value.toLowerCase();
        const filtered = students.filter(s => 
          s.name.toLowerCase().includes(val) || 
          String(s.id).includes(val)
        );
        renderDirectoryTable(filtered);
      };
    })
    .catch(err => console.error("Error loading student directory:", err));
}

function renderDirectoryTable(students) {
  const tbody = document.querySelector('#students-directory-table tbody');
  tbody.innerHTML = '';
  
  if (students.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No students registered.</td></tr>`;
    return;
  }
  
  students.forEach(s => {
    const isAtRisk = s.risk_status === 'Fail' || s.attendance_percentage < 75;
    const badgeClass = isAtRisk ? 'danger' : 'success';
    const badgeText = isAtRisk ? 'At Risk' : 'Healthy';
    
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${s.id}</td>
      <td><strong>${s.name}</strong></td>
      <td>${s.attended_classes} classes</td>
      <td>${s.attendance_percentage}%</td>
      <td><span class="badge ${badgeClass}">${badgeText}</span></td>
    `;
    tbody.appendChild(row);
  });
}

/* ==========================================================================
   4. REGISTER STUDENT & WEBRTC FACE CAPTURE LOGIC
   ========================================================================== */
const webrtcVideo = document.getElementById('webrtc-video-element');
const hiddenCanvas = document.getElementById('hidden-canvas');
const btnStartCapture = document.getElementById('btn-start-capture');
const progressBlock = document.getElementById('capture-progress-block');
const progressBar = document.getElementById('capture-progress-bar');
const progressCount = document.getElementById('capture-count');
const previewContainer = document.getElementById('thumbnails-preview-container');

btnStartCapture.addEventListener('click', startFaceCaptureSequence);

function registerStudent(e) {
  e.preventDefault();
  const idInput = document.getElementById('reg-student-id').value;
  const nameInput = document.getElementById('reg-student-name').value;
  
  fetch('/api/students', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: idInput, name: nameInput })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      currentRegStudentId = idInput;
      document.getElementById('registration-success-msg').style.display = 'inline-flex';
      
      // Start WebRTC Camera
      startWebcamCapture();
    } else {
      alert("Error: " + data.message);
    }
  })
  .catch(err => {
    console.error("Error adding student profile:", err);
    alert("An error occurred during database registration.");
  });
}

function startWebcamCapture() {
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
      .then(stream => {
        webrtcStream = stream;
        webrtcVideo.srcObject = stream;
        btnStartCapture.disabled = false;
      })
      .catch(err => {
        console.error("Error accessing user camera:", err);
        alert("Webcam permission denied or camera unavailable. Please enable browser webcam.");
      });
  } else {
    alert("Your browser does not support webcam capture.");
  }
}

function stopWebcamCapture() {
  if (webrtcStream) {
    webrtcStream.getTracks().forEach(track => track.stop());
    webrtcStream = null;
  }
  webrtcVideo.srcObject = null;
  btnStartCapture.disabled = true;
  clearInterval(captureInterval);
}

function startFaceCaptureSequence() {
  btnStartCapture.disabled = true;
  progressBlock.style.display = 'block';
  previewContainer.innerHTML = '';
  
  let frameCount = 0;
  const targetSamples = 100;
  progressBar.style.width = '0%';
  progressCount.textContent = `0/${targetSamples}`;
  
  const ctx = hiddenCanvas.getContext('2d');
  
  captureInterval = setInterval(() => {
    if (frameCount >= targetSamples) {
      clearInterval(captureInterval);
      stopWebcamCapture();
      
      alert(`Successfully captured 100 face images for ID ${currentRegStudentId}! Please switch to the "Model Trainer" tab to compile.`);
      
      // Reset registration states
      document.getElementById('student-register-form').reset();
      document.getElementById('registration-success-msg').style.display = 'none';
      progressBlock.style.display = 'none';
      currentRegStudentId = null;
      return;
    }
    
    // Draw current frame to hidden canvas
    ctx.save();
    // Mirror reflection drawing
    ctx.translate(hiddenCanvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(webrtcVideo, 0, 0, hiddenCanvas.width, hiddenCanvas.height);
    ctx.restore();
    
    // Convert to Base64 jpeg string
    const dataUrl = hiddenCanvas.toDataURL('image/jpeg', 0.85);
    
    frameCount++;
    const currentFrame = frameCount; // closure capture
    
    // Upload image
    fetch('/api/upload_face', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_id: currentRegStudentId,
        count: currentFrame,
        image: dataUrl
      })
    })
    .then(res => res.json())
    .then(data => {
      // Update UI bar
      const pct = (currentFrame / targetSamples) * 100;
      progressBar.style.width = `${pct}%`;
      progressCount.textContent = `${currentFrame}/${targetSamples}`;
      
      if (data.success) {
        // Append a thumbnail of captured image
        const img = document.createElement('img');
        img.src = dataUrl;
        img.className = 'dataset-img-thumbnail';
        previewContainer.appendChild(img);
        previewContainer.scrollTop = previewContainer.scrollHeight;
      }
    })
    .catch(err => console.error("Error uploading frame:", err));
    
  }, 150); // Capture photo every 150ms
}

/* ==========================================================================
   5. MODEL COMPILATION LOGIC
   ========================================================================== */
const btnRunTraining = document.getElementById('btn-run-training');
const trainingConsole = document.getElementById('training-console');

btnRunTraining.addEventListener('click', () => {
  btnRunTraining.disabled = true;
  
  // Write initial log
  logConsole("Initializing training pipeline...", 'info');
  logConsole("Scanning dataset directory...", 'info');
  
  fetch('/api/train', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        logConsole(data.message, 'success');
        logConsole("Training successfully completed!", 'success');
        logConsole("LBPH Face Recognition model saved to 'trainer/trainer.yml'. Ready for use.", 'success');
      } else {
        logConsole("Error: " + data.message, 'error');
      }
      btnRunTraining.disabled = false;
    })
    .catch(err => {
      console.error("Training error:", err);
      logConsole("System pipeline exception: check local server console.", 'error');
      btnRunTraining.disabled = false;
    });
});

function logConsole(message, type) {
  const line = document.createElement('div');
  line.className = `console-line ${type}`;
  line.textContent = `> [${new Date().toLocaleTimeString()}] ${message}`;
  trainingConsole.appendChild(line);
  trainingConsole.scrollTop = trainingConsole.scrollHeight;
}

/* ==========================================================================
   6. RISK PREDICTOR LOGIC
   ========================================================================== */
function calculateRisk(e) {
  e.preventDefault();
  const attVal = document.getElementById('risk-attendance').value;
  const intVal = document.getElementById('risk-internal').value;
  const assignVal = document.getElementById('risk-assignment').value;
  
  fetch('/api/predict_risk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      attendance: attVal,
      internal: intVal,
      assignment: assignVal
    })
  })
  .then(res => res.json())
  .then(data => {
    const resultBox = document.getElementById('risk-result-box');
    const title = document.getElementById('risk-result-title');
    const text = document.getElementById('risk-result-text');
    
    // Clear styles
    resultBox.className = 'predict-result-card';
    resultBox.classList.add(data.color);
    
    title.innerHTML = data.risk_level === 'High' ? 
      `⚠️ WARNING: High Failure Risk Detected` : 
      `✅ Low Failure Risk Assessed`;
      
    text.textContent = data.message;
    resultBox.style.display = 'block';
  })
  .catch(err => {
    console.error("Risk prediction failed:", err);
    alert("Risk calculation pipeline failed. Make sure ML libraries are initialized.");
  });
}

function loadFlaggedStudents() {
  fetch('/api/students')
    .then(res => res.json())
    .then(students => {
      const tbody = document.querySelector('#flagged-students-table tbody');
      tbody.innerHTML = '';
      
      const flagged = students.filter(s => s.risk_status === 'Fail' || s.attendance_percentage < 75);
      
      if (flagged.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--success); font-weight: 500;">No students flagged! Academic health is stable.</td></tr>`;
        return;
      }
      
      flagged.forEach(s => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td>${s.id}</td>
          <td><strong>${s.name}</strong></td>
          <td style="color: var(--danger); font-weight: 600;">${s.attendance_percentage}%</td>
          <td><span class="badge danger">High Risk</span></td>
        `;
        tbody.appendChild(row);
      });
    })
    .catch(err => console.error("Error loading flagged students:", err));
}

// Initial Load
loadDashboardData();
