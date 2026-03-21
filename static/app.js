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
    
    // Select Elements
    const selectTrigger  = document.getElementById("selectTrigger");
    const selectOptions  = document.getElementById("selectOptions");
    const selectedDisplay = document.getElementById("selectedDisplay");
    const selectedIcon    = document.getElementById("selectedIcon");
    const selectedBar     = document.getElementById("selectedBar");
    const selectedLabel   = document.getElementById("selectedLabel");

    // Modal Elements
    const successModal     = document.getElementById("successModal");
    const previewModal     = document.getElementById("previewModal");
    const previewTableBody = document.getElementById("previewTableBody");
    const previewTitle     = document.getElementById("previewTitle");
    const modalDownloadBtn = document.getElementById("modalDownloadBtn");
    const countSuccess      = document.getElementById("countSuccess");
    const countError        = document.getElementById("countError");

    let selectedCompany = null;   // "bmc" | "pernod"
    let uploadQueue     = [];
    let sessionHistory  = [];     // Track all successful extractions in this session
    let isProcessing    = false;
    let completedCount  = 0;

    // History Elements
    const historyModal      = document.getElementById("historyModal");
    const historyList       = document.getElementById("historyList");
    const historyEmptyState = document.getElementById("historyEmptyState");

    const COMPANY_LABELS = {
        bmc:    "Biashara Merchant Co.",
        pernod: "Pernod Ricard"
    };

    // ── Dropdown Logic ───────────────────────────────────────────
    window.toggleDropdown = function() {
        selectOptions.classList.toggle("hidden");
        selectTrigger.classList.toggle("active");
    };

    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
        if (!selectTrigger.contains(e.target) && !selectOptions.contains(e.target)) {
            selectOptions.classList.add("hidden");
            selectTrigger.classList.remove("active");
        }
    });

    window.selectCompany = function(id, name, icon) {
        selectedCompany = id;
        
        // Update Trigger UI
        selectedDisplay.textContent = name;
        selectedIcon.setAttribute("data-lucide", icon);
        
        // Update Options UI (Radios)
        document.querySelectorAll(".option").forEach(opt => {
            const isSelected = opt.getAttribute("onclick").includes(`'${id}'`);
            opt.classList.toggle("selected", isSelected);
        });

        // Show confirmation bar
        selectedBar.classList.remove("hidden");
        selectedLabel.textContent = `Processing for: ${name}`;

        // Unlock upload zone
        unlockDropzone();
        
        // Close dropdown
        selectOptions.classList.add("hidden");
        selectTrigger.classList.remove("active");
        
        lucide.createIcons();
    };

    window.clearCompany = function() {
        selectedCompany = null;
        selectedDisplay.textContent = "Select a company...";
        selectedIcon.setAttribute("data-lucide", "building-2");
        
        document.querySelectorAll(".option").forEach(opt => opt.classList.remove("selected"));
        selectedBar.classList.add("hidden");
        
        lockDropzone();
        lucide.createIcons();
    };

    function unlockDropzone() {
        dropzone.classList.remove("locked");
        fileInput.disabled = false;
        browseBtn.disabled = false;
        dropzoneTitle.textContent = "Drag & Drop Invoices Here";
        dropzoneSubtitle.textContent = `Target: ${COMPANY_LABELS[selectedCompany]}`;
    }

    function lockDropzone() {
        dropzone.classList.add("locked");
        fileInput.disabled = true;
        browseBtn.disabled = true;
        dropzoneTitle.textContent = "Select a company first";
        dropzoneSubtitle.textContent = "Complete Step 1 above before uploading files.";
    }

    // ── Dropzone Events ──────────────────────────────────────────
    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        if (!selectedCompany) return;
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (!selectedCompany) return;
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener("change", (e) => {
        handleFiles(e.target.files);
        fileInput.value = ""; // reset for re-selection
    });

    // ── File Handling ─────────────────────────────────────────────
    function handleFiles(files) {
        if (!selectedCompany) return;

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
        queuePill.textContent = COMPANY_LABELS[selectedCompany];

        newFiles.forEach(file => {
            const fileId  = "file-" + Math.random().toString(36).substr(2, 9);
            const fileObj = { 
                id: fileId, 
                file, 
                status: "pending", 
                company: selectedCompany,
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
        // Trigger modal download logic (using the first successful company label or "Batch")
        const successfulItem = uploadQueue.find(i => i.status === "success");
        const companyLabel = successfulItem ? COMPANY_LABELS[successfulItem.company] : "Batch";
        window.location.href = `/download?company=${encodeURIComponent(companyLabel)}`;
        
        // After download, show success summary again? No, just clear session as per user preference
        setTimeout(() => clearSession(), 1500);
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
        formData.append("company", item.company);

        try {
            const res  = await fetch("/process", { method: "POST", body: formData });
            const data = await res.json();

            if (res.ok) {
                item.status = "success";
                item.extractedData = data.extracted_data || [];
                updateItemUI(item.id, "success", data.message);
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
    window.showPreview = function(fileId) {
        const item = uploadQueue.find(i => i.id === fileId);
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

    window.closePreview = function() {
        previewModal.classList.add("hidden");
    };

    window.closeSuccess = function() {
        successModal.classList.add("hidden");
    };

    modalDownloadBtn.addEventListener("click", () => {
        // Trigger download with company query param
        const companyParam = encodeURIComponent(COMPANY_LABELS[selectedCompany] || "Invoices");
        window.location.href = `/download?company=${companyParam}`;
        
        // Show loading state on button
        modalDownloadBtn.disabled = true;
        modalDownloadBtn.innerHTML = '<div class="progress-ring" style="border-top-color:white; margin:0 auto;"></div>';
        
        // Instead of refresh, clear the session and UI
        setTimeout(() => {
            clearSession();
        }, 1500);
    });

    // ── Session & History Management ──────────────────────────────
    async function clearSession() {
        // 1. Save successful items to history
        const successfulItems = uploadQueue.filter(i => i.status === "success");
        sessionHistory = [...sessionHistory, ...successfulItems];

        // 2. Reset Backend State
        try {
            await fetch("/reset", { method: "POST" });
        } catch (e) {
            console.error("Failed to reset backend:", e);
        }

        // 3. Reset Local State
        uploadQueue    = [];
        completedCount = 0;
        isProcessing   = false;

        // 4. Reset UI
        clearCompany(); // Resets Step 1 and Step 2
        
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
                            <span class="history-meta">${COMPANY_LABELS[item.company]}</span>
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
