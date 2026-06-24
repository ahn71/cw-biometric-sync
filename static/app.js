const state = {
    devices: [],
    punches: [],
    users: [],
    serviceIsRunning: false,
};

document.addEventListener("DOMContentLoaded", () => {
    setupNavigation();
    setupControls();
    setupFilters();
    updateDashboardData();

    setInterval(updateStats, 3000);
    setInterval(updateServiceStatus, 3000);
    setInterval(updateDevices, 7000);
    setInterval(updatePunches, 7000);
    setInterval(updateUsers, 15000);
});

function setupNavigation() {
    document.querySelectorAll(".nav-item").forEach((button) => {
        button.addEventListener("click", () => showSection(button.dataset.section));
    });

    const menuToggle = document.getElementById("menu_toggle");
    const sidebar = document.getElementById("sidebar");
    if (menuToggle && sidebar) {
        menuToggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    }

}

function setupControls() {
    const toggleButton = document.getElementById("service_toggle_btn");
    if (toggleButton) {
        toggleButton.addEventListener("click", () => {
            const endpoint = state.serviceIsRunning ? "/service/stop" : "/service/start";
            runServiceAction(toggleButton, endpoint);
        });
    }
}

function setupFilters() {
    ["global_search", "device_search"].forEach((id) => bindInput(id, renderDevicesTable));
    ["user_search", "department_filter"].forEach((id) => bindInput(id, renderUsers));
    ["punch_search", "punch_device_filter", "punch_employee_filter", "punch_type_filter", "date_from", "date_to"].forEach((id) => bindInput(id, renderPunchTable));
    renderDepartmentFilter();
}

function bindInput(id, handler) {
    const element = document.getElementById(id);
    if (element) element.addEventListener("input", handler);
}

function showSection(sectionId) {
    document.querySelectorAll(".section").forEach((section) => {
        section.classList.toggle("active", section.id === sectionId);
        if (section.id === sectionId) setText("page_title", section.dataset.title || "Dashboard");
    });

    document.querySelectorAll(".nav-item").forEach((button) => {
        button.classList.toggle("active", button.dataset.section === sectionId);
    });

    const sidebar = document.getElementById("sidebar");
    if (sidebar) sidebar.classList.remove("open");
}

function updateDashboardData() {
    updateStats();
    updateServiceStatus();
    updateDevices();
    updateUsers();
    updatePunches();
}

function updateUsers() {
    fetchJson("/users")
        .then((data) => {
            state.users = (data.users || []).map(normalizeUser);
            renderDepartmentFilter();
            renderUsers();
            renderPunchFilters();
            renderDeviceMetrics();
        })
        .catch((err) => {
            console.error("Users endpoint error:", err);
            state.users = [];
            renderDepartmentFilter();
            renderUsers();
            renderPunchFilters();
            renderDeviceMetrics();
        });
}

function normalizeUser(user) {
    return {
        employeeId: user.employee_id || user.enroll_id || user.user_id || "",
        enrollId: user.enroll_id || user.employee_id || "",
        name: user.name || "",
        department: user.department || "",
        designation: user.designation || "",
        mobile: user.mobile || "",
        status: user.status || "seen",
        uid: user.uid || "",
        devices: user.devices || [],
        punchCount: user.punch_count || 0,
        lastPunch: user.last_punch || "",
        lastDevice: user.last_device || "",
    };
}

function renderDepartmentFilter() {
    const departments = [...new Set(state.users.map((user) => user.department).filter(Boolean))].sort();
    const departmentFilter = document.getElementById("department_filter");
    if (!departmentFilter) return;

    const current = departmentFilter.value;
    departmentFilter.innerHTML = '<option value="">All departments</option>' + departments.map((department) => `<option>${escapeHTML(department)}</option>`).join("");
    if (departments.includes(current)) departmentFilter.value = current;
}

function updateStats() {
    fetchJson("/stats")
        .then((data) => {
            const cpu = Number(data.cpu_percent || 0);
            const ram = Number(data.memory?.percent || 0);
            const disk = Number(data.disk?.percent || 0);
            setMetric("stats_cpu_percent", cpu);
            setMetric("stats_ram_percent", ram);
            setMetric("stats_disk_percent", disk);
            setMeter("cpu_meter", cpu);
            setMeter("ram_meter", ram);
            setMeter("disk_meter", disk);
            setText("sidebar_refresh", `Updated ${new Date().toLocaleTimeString()}`);
        })
        .catch((err) => console.error("Stats endpoint error:", err));
}

function updateServiceStatus() {
    fetchJson("/service/status")
        .then((data) => {
            const running = Boolean(data.running);
            state.serviceIsRunning = running;
            setHTML("stats_sync_status", running ? '<span class="pill ok">Running</span>' : '<span class="pill bad">Stopped</span>');
            setText("sidebar_status", running ? "Running" : "Stopped");
            updateServiceToggle(running);
        })
        .catch((err) => console.error("Service status endpoint error:", err));
}

function updateServiceToggle(isRunning) {
    const button = document.getElementById("service_toggle_btn");
    const label = document.getElementById("service_toggle_label");
    if (!button || !label) return;

    button.classList.toggle("running", isRunning);
    button.classList.toggle("stopped", !isRunning);
    button.setAttribute("aria-pressed", String(isRunning));
    label.textContent = isRunning ? "Sync running" : "Sync stopped";
}

function updateDevices() {
    fetchJson("/devices")
        .then((data) => {
            state.devices = (data.devices || []).map(normalizeDevice);
            renderDeviceMetrics();
            renderDevicesTable();
            renderOverviewDevicesTable();
            renderPunchFilters();
            if (state.devices.length) selectDevice(state.devices[0].id);
        })
        .catch((err) => console.error("Devices endpoint error:", err));
}

function normalizeDevice(device, index) {
    const id = device.device_id || `ZK Device ${index + 1}`;
    const status = device.status === "offline" ? "offline" : device.status === "online" ? "online" : "configured";
    return {
        id,
        ip: device.ip || "Not configured",
        status,
        userCount: device.user_count,
        punchCount: device.last_attendance_count,
        successLogCount: device.success_log_count || 0,
        failedLogCount: device.failed_log_count || 0,
        lastActivity: device.last_pull || device.last_push || "Waiting for sync",
        firmware: device.firmware || "Not available",
        lastSync: device.last_pull || "Not synchronized",
        lastPunch: device.last_push || "No punch received",
        retention: device.clear_from_device_on_fetch ? "Clear after fetch" : "Keep on device",
        direction: device.punch_direction || "AUTO",
    };
}

function calcUserCounts() {
    const counts = {};
    state.users.forEach((user) => {
        (user.devices || []).forEach((dev) => {
            counts[dev] = (counts[dev] || 0) + 1;
        });
    });
    return counts;
}

function syncDevice(deviceId, button) {
    if (button) {
        button.disabled = true;
        button.classList.add("syncing");
        button.textContent = "⟳ Syncing";
    }
    fetch("/devices/sync/" + encodeURIComponent(deviceId), { method: "POST" })
        .then((r) => r.json())
        .then((data) => {
            if (button) {
                button.textContent = "✓ Synced";
                button.classList.remove("syncing");
                button.classList.add("synced");
                setTimeout(() => {
                    button.disabled = false;
                    button.classList.remove("synced");
                    button.textContent = "⟳ Sync";
                }, 3000);
            }
        })
        .catch((err) => {
            console.error("Sync error:", err);
            if (button) {
                button.textContent = "✗ Failed";
                button.classList.remove("syncing");
                button.classList.add("sync-fail");
                setTimeout(() => {
                    button.disabled = false;
                    button.classList.remove("sync-fail");
                    button.textContent = "⟳ Sync";
                }, 3000);
            }
        });
}

function renderDeviceMetrics() {
    const total = state.devices.length;
    const online = state.devices.filter((device) => device.status === "online").length;
    const offline = state.devices.filter((device) => device.status === "offline").length;
    const knownUsers = state.devices.reduce((sum, device) => sum + Number(device.userCount || 0), 0);

    setText("total_users", knownUsers || state.users.length || "N/A");

    const summary = document.getElementById("device_summary");
    if (summary) {
        summary.innerHTML = `
            <span class="sum-total">Devices: <strong>${total}</strong></span>
            <span class="sum-online">Online: <strong>${online}</strong></span>
            <span class="sum-offline">Offline: <strong>${offline}</strong></span>
        `;
    }
}

function renderOverviewDevicesTable() {
    const tbody = document.querySelector("#overview_devices_table tbody");
    if (!tbody) return;
    const userCounts = calcUserCounts();

    tbody.innerHTML = state.devices.length ? state.devices.map((device) => `
        <tr>
            <td><strong>${escapeHTML(device.id)}</strong></td>
            <td><code class="ip-addr">${escapeHTML(device.ip)}</code></td>
            <td>${statusPill(device.status)}</td>
            <td><strong>${formatCount(device.punchCount)}</strong></td>
            <td>${formatCount(userCounts[device.id] || 0)}</td>
            <td><span class="sync-time">${escapeHTML(device.lastSync)}</span></td>
            <td><button class="btn-sync" type="button" onclick="syncDevice('${escapeAttr(device.id)}',this)" title="Sync this device">⟳ Sync</button></td>
        </tr>
    `).join("") : '<tr><td colspan="7">No configured devices found.</td></tr>';
}

function renderDevicesTable() {
    const query = combinedQuery("device_search").toLowerCase();
    const rows = state.devices.filter((device) => searchable(device, query));
    const tbody = document.querySelector("#devices_table tbody");
    if (!tbody) return;
    const userCounts = calcUserCounts();

    tbody.innerHTML = rows.length ? rows.map((device) => `
        <tr>
            <td><strong>${escapeHTML(device.id)}</strong></td>
            <td><code class="ip-addr">${escapeHTML(device.ip)}</code></td>
            <td>${statusPill(device.status)}</td>
            <td><strong>${formatCount(device.punchCount)}</strong></td>
            <td>${formatCount(userCounts[device.id] || 0)}</td>
            <td><span class="sync-time">${escapeHTML(device.lastSync)}</span></td>
            <td><div class="cell-actions">
                <button class="btn-sync" type="button" onclick="syncDevice('${escapeAttr(device.id)}',this)" title="Sync this device">⟳ Sync</button>
                <button class="btn-view" type="button" onclick="selectDevice('${escapeAttr(device.id)}')">View</button>
            </div></td>
        </tr>
    `).join("") : '<tr><td colspan="7">No devices match the current filters.</td></tr>';
    setText("devices_count_label", `${rows.length} device${rows.length === 1 ? "" : "s"}`);
}

window.selectDevice = function selectDevice(id) {
    const device = state.devices.find((item) => item.id === id) || state.devices[0];
    if (!device) return;

    setText("selected_device_name", device.id);
    setHTML("selected_device_status", statusPill(device.status));
    setHTML("device_detail_grid", [
        ["Device Information", `${device.id} / ${device.ip}`],
        ["Connection Status", titleCase(device.status)],
        ["User Count", formatCount(device.userCount)],
        ["Device Punch Count", formatCount(device.punchCount)],
        ["Successful Sync Logs", formatCount(device.successLogCount)],
        ["Failed Sync Logs", formatCount(device.failedLogCount)],
        ["Last Pull", device.lastSync],
        ["Last Push", device.lastPunch],
        ["Firmware Version", device.firmware],
        ["Retention Policy", device.retention],
    ].map(([label, value]) => `<div class="detail-cell"><span>${label}</span><strong>${escapeHTML(value)}</strong></div>`).join(""));

    setHTML("device_timeline", [
        ["Connection check", `${titleCase(device.status)} at ${new Date().toLocaleTimeString()}`],
        ["Last synchronization", device.lastSync],
        ["Last punch received", device.lastPunch],
        ["Punch direction", device.direction],
    ].map(([label, value]) => `<div class="timeline-item"><strong>${escapeHTML(label)}</strong><span>${escapeHTML(value)}</span></div>`).join(""));
};

function updatePunches() {
    fetchJson("/logs/punches")
        .then((data) => {
            const endpointPunches = (data.punches || []).map(normalizePunch);
            state.punches = endpointPunches;
            renderPunchMetrics();
            renderPunchTable();
            renderLiveFeed();
            renderPunchFilters();
        })
        .catch((err) => {
            console.error("Punch endpoint error:", err);
            state.punches = [];
            renderPunchMetrics();
            renderPunchTable();
            renderLiveFeed();
            renderPunchFilters();
        });
}

function normalizePunch(punch) {
    const employeeId = punch.employee_id || punch.employee || punch.uid || "";
    const matchedUser = state.users.find((user) => user.employeeId === employeeId || user.enrollId === employeeId);
    const direction = String(punch.direction || "").toUpperCase().includes("OUT") ? "OUT" : "IN";
    return {
        time: punch.time || "",
        employeeId,
        employeeName: matchedUser?.name || "",
        device: punch.device || "",
        checkType: direction,
        method: punch.punch_code === null || punch.punch_code === undefined ? "Device" : `Punch ${punch.punch_code}`,
        status: punch.status || "success",
    };
}

function renderPunchMetrics() {
    const today = formatLocalDate(new Date());
    const todayPunches = state.punches.filter((punch) => String(punch.time).slice(0, 10) === today);
    setText("today_check_total", todayPunches.length);
    setText("notification_count", state.devices.filter((device) => device.status === "offline").length);
    setText("punch_source", `${state.punches.length} recent entries`);
}

function renderPunchTable() {
    const punches = filteredPunches();
    const tbody = document.querySelector("#punch_table tbody");
    if (!tbody) return;

    tbody.innerHTML = punches.length ? punches.map((punch) => `
        <tr>
            <td>${escapeHTML(punch.time)}</td>
            <td>${escapeHTML(punch.employeeId || "N/A")}</td>
            <td><strong>${escapeHTML(punch.employeeName || "N/A")}</strong></td>
            <td>${escapeHTML(punch.device)}</td>
            <td>${checkPill(punch.checkType)}</td>
            <td>${escapeHTML(punch.method)}</td>
        </tr>
    `).join("") : '<tr><td colspan="6">No punch records match the selected filters.</td></tr>';
    setText("punches_count_label", `${punches.length} record${punches.length === 1 ? "" : "s"}`);
}

function filteredPunches() {
    const query = combinedQuery("punch_search").toLowerCase();
    const device = valueOf("punch_device_filter");
    const employee = valueOf("punch_employee_filter");
    const type = valueOf("punch_type_filter");
    const from = valueOf("date_from");
    const to = valueOf("date_to");

    return state.punches.filter((punch) => {
        const text = `${punch.employeeId} ${punch.employeeName} ${punch.device}`.toLowerCase();
        return (!query || text.includes(query))
            && (!device || punch.device === device)
            && (!employee || punch.employeeId === employee)
            && (!type || punch.checkType === type)
            && (!from || punch.time.slice(0, 10) >= from)
            && (!to || punch.time.slice(0, 10) <= to);
    }).slice().reverse();
}

function renderPunchFilters() {
    fillSelect("punch_device_filter", "All devices", state.devices.map((device) => device.id));
    fillSelect("punch_employee_filter", "All employees", [
        ...state.users.map((user) => user.employeeId),
        ...state.punches.map((punch) => punch.employeeId),
    ]);
}

function fillSelect(id, firstLabel, values) {
    const select = document.getElementById(id);
    if (!select) return;
    const current = select.value;
    const unique = [...new Set(values.filter(Boolean))];
    select.innerHTML = `<option value="">${firstLabel}</option>` + unique.map((value) => `<option>${escapeHTML(value)}</option>`).join("");
    if (unique.includes(current)) select.value = current;
}

function renderLiveFeed() {
    const latest = state.punches.slice(-10).reverse();
    const html = latest.map((punch) => `
        <article class="feed-item ${punch.checkType === "OUT" ? "check-out" : "check-in"}">
            <div><strong>${escapeHTML(punch.employeeName || `User ${punch.employeeId || "N/A"}`)}</strong><small>${escapeHTML(punch.employeeId || "N/A")} / ${escapeHTML(punch.method)}</small></div>
            <div><span>${escapeHTML(punch.device || "N/A")}</span><small>${escapeHTML(punch.time || "N/A")}</small></div>
            ${checkPill(punch.checkType)}
        </article>
    `).join("") || '<div class="feed-item"><strong>Waiting for live punches</strong><small>Auto refresh is active</small></div>';

    setHTML("live_feed", html);
}

function renderUsers() {
    const query = combinedQuery("user_search").toLowerCase();
    const department = valueOf("department_filter");
    const rows = state.users.filter((user) => {
        const text = Object.values(user).join(" ").toLowerCase();
        return (!query || text.includes(query)) && (!department || user.department === department);
    });
    const tbody = document.querySelector("#users_table tbody");
    if (!tbody) return;

    tbody.innerHTML = rows.length ? rows.map((user) => `
        <tr>
            <td>${escapeHTML(user.employeeId || "N/A")}</td>
            <td>${escapeHTML(user.enrollId || "N/A")}</td>
            <td><strong>${escapeHTML(user.name || "N/A")}</strong></td>
            <td>${escapeHTML(user.department || "N/A")}</td>
            <td>${escapeHTML(user.designation || "N/A")}</td>
            <td>${escapeHTML(user.mobile || "N/A")}</td>
            <td>${user.status === "seen" ? '<span class="pill ok">Seen</span>' : '<span class="pill muted">Unknown</span>'}</td>
            <td><button class="row-action" type="button" onclick="selectUser('${escapeAttr(user.employeeId)}')">View</button></td>
        </tr>
    `).join("") : '<tr><td colspan="8">No users found in punch logs yet.</td></tr>';
    setText("users_count_label", `${rows.length} user${rows.length === 1 ? "" : "s"}`);
    if (rows[0]) {
        selectUser(rows[0].employeeId);
    } else {
        setText("selected_user_name", "No user selected");
        setHTML("selected_user_status", '<span class="pill muted">Empty</span>');
        setHTML("user_profile", '<div class="profile-cell"><span>Status</span><strong>No punch-log users available</strong></div>');
    }
}

window.selectUser = function selectUser(employeeId) {
    const user = state.users.find((item) => item.employeeId === employeeId);
    if (!user) return;
    setText("selected_user_name", `${user.name || "User"} / ${user.employeeId || "N/A"}`);
    setHTML("selected_user_status", user.status === "seen" ? '<span class="pill ok">Seen</span>' : '<span class="pill muted">Unknown</span>');
    setHTML("user_profile", [
        ["Employee ID", user.employeeId || "N/A"],
        ["Enroll ID", user.enrollId || "N/A"],
        ["Device UID", user.uid || "N/A"],
        ["Punch Count", formatCount(user.punchCount)],
        ["Last Device", user.lastDevice || "N/A"],
        ["Last Punch Time", user.lastPunch || "N/A"],
    ].map(([label, value]) => `<div class="profile-cell"><span>${label}</span><strong>${escapeHTML(value)}</strong></div>`).join(""));
};

function runServiceAction(button, endpoint) {
    button.disabled = true;
    fetchJson(endpoint)
        .then(() => updateDashboardData())
        .catch((err) => {
            console.error("Service action failed:", err);
            alert("Service action failed. Check process permissions and logs.");
        })
        .finally(() => { button.disabled = false; });
}

function fetchJson(url) {
    return fetch(url).then((response) => {
        if (!response.ok) throw new Error(`${url} returned ${response.status}`);
        return response.json();
    });
}

function combinedQuery(localId) {
    return `${valueOf("global_search")} ${valueOf(localId)}`.trim();
}

function searchable(object, query) {
    if (!query) return true;
    return Object.values(object).join(" ").toLowerCase().includes(query);
}

function valueOf(id) {
    const element = document.getElementById(id);
    return element ? element.value.trim() : "";
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function setHTML(id, value) {
    const element = document.getElementById(id);
    if (element) element.innerHTML = value;
}

function setMeter(id, value) {
    const element = document.getElementById(id);
    if (element) element.style.width = `${Math.max(0, Math.min(100, value))}%`;
}

function setMetric(id, value) {
    setText(id, `${Number(value || 0).toFixed(1)}%`);
}

function statusPill(status) {
    if (status === "online") return '<span class="pill ok">Online</span>';
    if (status === "offline") return '<span class="pill bad">Offline</span>';
    return '<span class="pill info">Configured</span>';
}

function checkPill(type) {
    return type === "OUT" ? '<span class="pill bad">Check Out</span>' : '<span class="pill ok">Check In</span>';
}

function employeeIdFromText(text) {
    const match = String(text || "").match(/EMP[-\s]?\d+/i);
    return match ? match[0].replace(/\s/g, "-").toUpperCase() : "";
}

function employeeNameFromText(text) {
    const clean = String(text || "").replace(/employee|emp|user|uid|id|[:=]/gi, " ").replace(/\s+/g, " ").trim();
    return clean && clean.length < 42 ? clean : "";
}

function formatDateTime(date) {
    const pad = (value) => String(value).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function formatLocalDate(date) {
    const pad = (value) => String(value).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function timeOnly(value) {
    return String(value).split(" ")[1] || value;
}

function titleCase(value) {
    return String(value).replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function numberFormat(value) {
    return Number(value || 0).toLocaleString();
}

function formatCount(value) {
    if (value === null || value === undefined || value === "") return "N/A";
    return Number(value || 0).toLocaleString();
}

function escapeHTML(value) {
    return String(value).replace(/[&<>'"]/g, (tag) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "'": "&#39;",
        '"': "&quot;",
    }[tag] || tag));
}

function escapeAttr(value) {
    return escapeHTML(value).replace(/`/g, "&#96;");
}
