document.addEventListener("DOMContentLoaded", () => {
    const dropzone     = document.getElementById("dropzone");
    const fileInput    = document.getElementById("fileInput");
    const browseBtn    = document.getElementById("browseBtn");
    const queueList    = document.getElementById("queueList");
    const queueStatus  = document.getElementById("queueStatus");
    const queuePill    = document.getElementById("queueCompanyPill");
    const processingSection = document.getElementById("processingSection");
    const dropzoneTitle    = document.getElementById("dropzoneTitle");
    const dropzoneSubtitle = document.getElementById("dropzoneSubtitle");
    
    // Modal Elements
    const successModal     = document.getElementById("successModal");
    const previewModal     = document.getElementById("previewModal");
    const previewTableBody = document.getElementById("previewTableBody");
    const previewTitle     = document.getElementById("previewTitle");
    const modalDownloadBtn = document.getElementById("modalDownloadBtn");
    const countSuccess      = document.getElementById("countSuccess");
    const countError        = document.getElementById("countError");

    let uploadQueue     = [];
    let sessionHistory  = [];     // Track all successful extractions in this session
    let isProcessing    = false;
    let completedCount  = 0;

    const COMPANY_LABELS = {
        bmc:    "Biashara Merchant Co.",
        pernod: "Pernod Ricard"
    };


    // ── Dropzone Events ──────────────────────────────────────────
    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener("change", (e) => {
        handleFiles(e.target.files);
        fileInput.value = ""; // reset for re-selection
    });

    // ── File Handling ─────────────────────────────────────────────
    function handleFiles(files) {

        if (files.length > 50) {
            alert("Maximum 50 files allowed per batch.");
            return;
        }

        const existingNames = uploadQueue.map(i => i.file.name);
        let duplicates = [];
        const newFiles = Array.from(files).filter(file => {
            if (file.type !== "application/pdf") return false;
            if (existingNames.includes(file.name)) {
                duplicates.push(file.name);
                return false;
            }
            return true;
        });

        if (duplicates.length > 0) {
            alert(`Skipping ${duplicates.length} duplicate file(s):\n${duplicates.join("\n")}\n\nThese files are already in your queue.`);
        }

        if (newFiles.length === 0 && files.length > 0) {
            // If all were duplicates or not PDFs
            return;
        }

        processingSection.classList.remove("hidden");
        queuePill.textContent = "Auto-Detecting Formats";

        newFiles.forEach(file => {
            const fileId  = "file-" + Math.random().toString(36).substr(2, 9);
            const fileObj = { 
                id: fileId, 
                file, 
                status: "pending", 
                company: null, // To be detected by backend
                extractedData: [] 
            };
            uploadQueue.push(fileObj);
            renderQueueItem(fileObj);
        });

        updateStatus();
        processQueue();
    }

    function renderQueueItem(item) {
        const el = document.createElement("div");
        el.className = "queue-item pending";
        el.id = item.id;
        el.innerHTML = `
            <div class="item-info">
                <i data-lucide="file-text" class="file-icon"></i>
                <div class="item-details">
                    <span class="file-name">${item.file.name}</span>
                    <span class="file-status" id="status-text-${item.id}">Waiting...</span>
                </div>
            </div>
            <div class="item-actions">
                <div class="progress-ring hidden" id="spinner-${item.id}"></div>
                <button class="view-data-btn hidden" id="view-${item.id}" onclick="showPreview('${item.id}')">
                    <i data-lucide="eye"></i> View Data
                </button>
                <button class="retry-btn hidden" id="retry-${item.id}" onclick="retryFile('${item.id}')">
                    <i data-lucide="rotate-cw"></i> Retry
                </button>
                <button class="remove-btn" id="remove-${item.id}" onclick="removeFile('${item.id}')">
                    <i data-lucide="trash-2"></i>
                </button>
            </div>
        `;
        queueList.appendChild(el);
        lucide.createIcons();
    }

    function updateItemUI(id, status, message) {
        const el        = document.getElementById(id);
        const statusTxt = document.getElementById(`status-text-${id}`);
        const spinner   = document.getElementById(`spinner-${id}`);
        const retryBtn  = document.getElementById(`retry-${id}`);

        el.className = `queue-item ${status}`;
        statusTxt.innerText = message;

        if (status === "uploading") {
            spinner.classList.remove("hidden");
            retryBtn.classList.add("hidden");
            document.getElementById(`view-${id}`).classList.add("hidden");
        } else if (status === "success" || status === "error") {
            spinner.classList.add("hidden");
            if (status === "error") retryBtn.classList.remove("hidden");
            if (status === "success") {
                document.getElementById(`view-${id}`).classList.remove("hidden");
                lucide.createIcons();
            }
        }
    }

    function updateStatus() {
        queueStatus.innerText = `${completedCount} / ${uploadQueue.length}`;
        
        // Show global download if there's at least one success
        const hasSuccess = uploadQueue.some(i => i.status === "success");
        const globalDownloadBtn = document.getElementById("globalDownloadBtn");
        if (globalDownloadBtn) {
            globalDownloadBtn.classList.toggle("hidden", !hasSuccess);
            
            // Disable until all files in queue are processed (success or error)
            const allDone = uploadQueue.every(i => i.status === "success" || i.status === "error");
            globalDownloadBtn.disabled = !allDone;
        }
    }

    window.removeFile = function(id) {
        const idx = uploadQueue.findIndex(i => i.id === id);
        if (idx === -1) return;

        const item = uploadQueue[idx];
        
        // Only allow removing if not currently uploading
        if (item.status === "uploading") return;

        // If it was successful, notify backend to remove its data from the buffer
        if (item.status === "success") {
            const formData = new FormData();
            formData.append("file_id", id);
            formData.append("session_id", SESSION_ID); // Track session
            fetch("/remove-file", { method: "POST", body: formData })
                .catch(err => console.error("Failed to remove file data from backend:", err));
        }

        // Decrement completed count if needed
        if (item.status === "success" || item.status === "error") {
            completedCount--;
        }

        uploadQueue.splice(idx, 1);
        document.getElementById(id).remove();
        
        if (uploadQueue.length === 0) {
            processingSection.classList.add("hidden");
        }
        
        updateStatus();
        processQueue(); // In case we removed something and unblocked the queue
    };

    window.triggerDownload = function() {
        window.location.href = `/download?session_id=${SESSION_ID}`;
        
        // After download, we don't clear session automatically anymore to avoid race conditions.
        // The user can use the "Reset" button in Step 1 to start fresh.
    };

    async function processQueue() {
        if (isProcessing) return;
        isProcessing = true;

        const nextIdx = uploadQueue.findIndex(i => i.status === "pending");
        if (nextIdx === -1) {
            isProcessing = false;
            checkAllDone();
            return;
        }

        const item = uploadQueue[nextIdx];
        item.status = "uploading";
        updateItemUI(item.id, "uploading", "Extracting...");

        const formData = new FormData();
        formData.append("file", item.file);
        formData.append("file_id", item.id); // Send unique ID for tracking
        formData.append("session_id", SESSION_ID); // Track session

        try {
            const res  = await fetch("/process", { method: "POST", body: formData });
            const data = await res.json();

            if (res.ok) {
                item.status = "success";
                item.extractedData = data.extracted_data || [];
                item.company = data.company_key || "unknown"; // Store detected company
                updateItemUI(item.id, "success", data.message);
                
                // Update company name in UI if needed (dynamic label)
                const statusTxt = document.getElementById(`status-text-${item.id}`);
                statusTxt.innerText = `${data.company || 'Extracted'}: ${data.message}`;

                // Add to history immediately for real-time tracking
                if (!sessionHistory.some(i => i.id === item.id)) {
                    sessionHistory.push({...item});
                }
            } else {
                throw new Error(data.detail || "Error");
            }
        } catch (e) {
            item.status = "error";
            updateItemUI(item.id, "error", e.message);
        }

        completedCount++;
        updateStatus();
        isProcessing = false;
        processQueue();
    }

    function checkAllDone() {
        const allDone = uploadQueue.every(i => i.status === "success" || i.status === "error");
        if (allDone && uploadQueue.length > 0) {
            const successes = uploadQueue.filter(i => i.status === "success").length;
            const errors    = uploadQueue.filter(i => i.status === "error").length;

            if (successes > 0) {
                countSuccess.textContent = successes;
                countError.textContent   = errors;
                successModal.classList.remove("hidden");
            }
        }
    }

    window.retryFile = function(id) {
        const item = uploadQueue.find(i => i.id === id);
        if (item && item.status === "error") {
            item.status = "pending";
            completedCount--;
            updateStatus();
            updateItemUI(item.id, "pending", "Waiting...");
            processQueue();
        }
    };

    // ── Modal Actions ─────────────────────────────────────────────
    // showPreview was duplicated below, using the more robust version at the bottom of the file

    window.closePreview = function() {
        previewModal.classList.add("hidden");
    };

    window.closeSuccess = function() {
        successModal.classList.add("hidden");
    };

    modalDownloadBtn.addEventListener("click", () => {
        window.location.href = `/download?session_id=${SESSION_ID}`;
        
        // Show success state on button
        modalDownloadBtn.classList.add("success");
        modalDownloadBtn.innerHTML = '<i data-lucide="check"></i> Downloaded';
        lucide.createIcons();

        // Note: We no longer auto-reset the session here to prevent the "No files processed" error.
        // The user can close the modal and either add more files or reset manually.
    });


    // ── Session & History Management ──────────────────────────────
    async function clearSession() {
        // 1. History is now updated in real-time in processQueue.
        // We ensure sessionHistory only contains unique IDs.

        // 2. Reset Backend State
        try {
            const formData = new FormData();
            formData.append("session_id", SESSION_ID);
            await fetch("/reset", { method: "POST", body: formData });
        } catch (e) {
            console.error("Failed to reset backend:", e);
        }

        // 3. Reset Local State
        uploadQueue    = [];
        completedCount = 0;
        isProcessing   = false;

        // 4. Reset UI
        processingSection.classList.add("hidden");
        successModal.classList.add("hidden");
        queueList.innerHTML = "";
        updateStatus();

        // Restore download button for next time
        modalDownloadBtn.disabled = false;
        modalDownloadBtn.innerHTML = '<i data-lucide="download"></i> Download Excel';
        
        lucide.createIcons();
    }

    window.showHistory = function() {
        if (sessionHistory.length === 0) {
            historyList.innerHTML = "";
            historyEmptyState.classList.remove("hidden");
        } else {
            historyEmptyState.classList.add("hidden");
            historyList.innerHTML = "";
            
            // Show latest first
            [...sessionHistory].reverse().forEach(item => {
                const el = document.createElement("div");
                el.className = "history-item";
                el.innerHTML = `
                    <div class="history-item-info">
                        <i data-lucide="file-check" class="history-icon"></i>
                        <div class="history-details">
                            <span class="history-name">${item.file.name}</span>
                            <span class="history-meta">${item.company || 'Unknown Format'}</span>
                        </div>
                    </div>
                    <button class="view-data-btn" onclick="showHistoryItemPreview('${item.id}')">
                        <i data-lucide="eye"></i> View
                    </button>
                `;
                historyList.appendChild(el);
            });
        }
        
        historyModal.classList.remove("hidden");
        lucide.createIcons();
    };

    window.closeHistory = function() {
        historyModal.classList.add("hidden");
    };

    // Helper to preview from history
    window.showHistoryItemPreview = function(id) {
        const item = sessionHistory.find(i => i.id === id);
        if (item) {
            closeHistory(); // Hide history modal so preview is visible
            showPreview(id, true); // true indicates it's from history search
        }
    };

    // Update showPreview to work with both queue and history
    const originalShowPreview = window.showPreview;
    window.showPreview = function(fileId, fromHistory = false) {
        const item = (fromHistory ? sessionHistory : uploadQueue).find(i => i.id === fileId);
        if (!item || !item.extractedData) return;

        previewTitle.textContent = `Data: ${item.file.name}`;
        previewTableBody.innerHTML = "";

        item.extractedData.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${row.ProductCode || '-'}</td>
                <td>${row.ProductDescription || '-'}</td>
                <td>${row.Units || '-'}</td>
                <td>${row.UOM || '-'}</td>
                <td>${row.QtyOrdered || '-'}</td>
                <td>${row.Weight || '-'}</td>
            `;
            previewTableBody.appendChild(tr);
        });

        previewModal.classList.remove("hidden");
        lucide.createIcons();
    };
});
