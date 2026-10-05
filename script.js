"use strict";

/*
    SYSTEMCHECK
    Supports:
    - Desktop Executable (pywebview bridge)
    - Windows Server API (http://127.0.0.1:8765)
    - Android Bridge & Browser Fallback
*/

const $ = (id) => document.getElementById(id);


/* =========================================================
   PLATFORM DETECTION
========================================================= */

function detectPlatform() {
    const ua = navigator.userAgent || "";

    if (/Android/i.test(ua)) {
        return "android";
    }

    if (/Windows/i.test(ua) || navigator.platform.includes("Win")) {
        return "windows";
    }

    return "unsupported";
}


/* =========================================================
   BROWSER INFORMATION
========================================================= */

function getBrowserInfo() {
    const screenWidth = window.screen?.width || 0;
    const screenHeight = window.screen?.height || 0;

    return {
        platform: navigator.platform || "Unknown",
        threads: navigator.hardwareConcurrency || null,
        memory: navigator.deviceMemory || null,
        screen:
            screenWidth && screenHeight
                ? `${screenWidth} × ${screenHeight}`
                : "Unavailable",
        pixelRatio: window.devicePixelRatio || 1
    };
}


function setBrowserInfo() {
    const info = getBrowserInfo();

    $("browserPlatform").textContent = info.platform || "Unknown";
    $("browserThreads").textContent = info.threads ? `${info.threads}` : "Unavailable";
    $("browserMemory").textContent = info.memory ? `${info.memory} GB` : "Unavailable";
    $("screenSize").textContent = info.screen;
    $("pixelRatio").textContent = info.pixelRatio;

    if ($("browserResolution")) {
        $("browserResolution").textContent = info.screen;
    }
}


/* =========================================================
   RESET RESULTS
========================================================= */

function resetResults() {
    $("cpuName").textContent = "Unavailable";
    $("cpuCores").textContent = "--";
    $("cpuThreads").textContent = "--";

    $("ramValue").textContent = "Unavailable";

    $("gpuName").textContent = "Unavailable";
    $("gpuVram").textContent = "--";
    $("gpuDriver").textContent = "--";

    $("storageValue").textContent = "Unavailable";

    $("displayValue").textContent = "Unavailable";

    $("osValue").textContent = "Unavailable";
    $("osVersion").textContent = "--";

    $("batteryValue").textContent = "Unavailable";
    $("batteryStatus").textContent = "--";

    $("manufacturerValue").textContent = "Unavailable";
    $("modelValue").textContent = "--";

    $("powerLevel").textContent = "--";
}


/* =========================================================
   VALUE CLEANING
========================================================= */

function cleanValue(value, fallback = "Unavailable") {
    if (
        value === undefined ||
        value === null ||
        value === "" ||
        value === "null" ||
        value === "undefined"
    ) {
        return fallback;
    }

    if (typeof value === "object") {
        if (value.name) return String(value.name);
        if (value.model) return String(value.model);
        if (value.value) return String(value.value);
        return fallback;
    }

    return String(value);
}


/* =========================================================
   RAM & VRAM FORMATTING
========================================================= */

function formatRam(value) {
    if (value === undefined || value === null || value === "") {
        return "Unavailable";
    }

    const gb = Number(value);
    if (!Number.isFinite(gb)) {
        return cleanValue(value);
    }

    return `${gb.toFixed(gb >= 10 ? 0 : 1)} GB`;
}

function formatVram(value) {
    if (value === undefined || value === null || value === "") {
        return "Unavailable";
    }

    const mb = Number(value);
    if (!Number.isFinite(mb)) {
        return cleanValue(value);
    }

    if (mb >= 1024) {
        const gb = mb / 1024;
        return `${gb.toFixed(Number.isInteger(gb) ? 0 : 1)} GB`;
    }

    return `${Math.round(mb)} MB`;
}


/* =========================================================
   POWER ESTIMATE
========================================================= */

function estimatePower(data, platform) {
    let score = 0;

    const cpu = cleanValue(data?.CPU ?? data?.cpu ?? data?.cpuName, "").toLowerCase();
    const gpu = cleanValue(data?.GPU ?? data?.gpu ?? data?.gpuName, "").toLowerCase();
    const ram = Number(data?.RAM_GB ?? data?.ram_gb ?? data?.ram ?? 0);
    const cores = Number(data?.CPU_Cores ?? data?.cpu_cores ?? data?.cores ?? 0);

    /* RAM */
    if (ram >= 32) score += 3;
    else if (ram >= 16) score += 2;
    else if (ram >= 8) score += 1;

    /* CPU cores */
    if (cores >= 16) score += 3;
    else if (cores >= 8) score += 2;
    else if (cores >= 4) score += 1;

    /* GPU */
    if (gpu.includes("rtx 4090") || gpu.includes("rtx 4080") || gpu.includes("rx 7900")) {
        score += 4;
    } else if (gpu.includes("rtx 4070") || gpu.includes("rtx 4060") || gpu.includes("rx 7800")) {
        score += 3;
    } else if (gpu.includes("rtx 4050") || gpu.includes("gtx 1660") || gpu.includes("rx 6600")) {
        score += 2;
    } else if (gpu && !gpu.includes("intel") && !gpu.includes("uhd") && !gpu.includes("integrated")) {
        score += 1;
    }

    /* CPU family */
    if (cpu.includes("i9") || cpu.includes("ryzen 9") || cpu.includes("core ultra 9")) {
        score += 2;
    } else if (cpu.includes("i7") || cpu.includes("ryzen 7") || cpu.includes("core ultra 7")) {
        score += 1;
    }

    if (platform === "android") {
        if (score >= 7) return "High";
        if (score >= 4) return "Medium";
        return "Basic";
    }

    if (score >= 9) return "High";
    if (score >= 5) return "Medium";
    return "Basic";
}


/* =========================================================
   SHOW DATA
========================================================= */

function showData(data, platform) {
    resetResults();

    if (!data || typeof data !== "object") {
        console.error("Invalid system data:", data);
        return;
    }

    /* CPU */
    $("cpuName").textContent = cleanValue(data.CPU ?? data.cpu ?? data.cpuName);
    $("cpuCores").textContent = cleanValue(data.CPU_Cores ?? data.cpu_cores ?? data.cores, "--");
    $("cpuThreads").textContent = cleanValue(data.CPU_Threads ?? data.cpu_threads ?? data.threads, "--");

    /* RAM */
    $("ramValue").textContent = formatRam(data.RAM_GB ?? data.ram_gb ?? data.ram);

    /* GPU */
    $("gpuName").textContent = cleanValue(data.GPU ?? data.gpu ?? data.gpuName);
    $("gpuVram").textContent = formatVram(data.VRAM_MB ?? data.vram_mb ?? data.VRAM ?? data.vram);
    $("gpuDriver").textContent = cleanValue(data.GPU_Driver ?? data.gpu_driver ?? data.DriverVersion, "--");

    /* STORAGE */
    $("storageValue").textContent = cleanValue(data.Storage ?? data.storage);

    /* DISPLAY */
    const display = data.Display ?? data.display ?? data.DisplayResolution;
    $("displayValue").textContent = cleanValue(display);

    /* OS */
    $("osValue").textContent = cleanValue(data.OS ?? data.os);
    $("osVersion").textContent = cleanValue(data.OS_Version ?? data.os_version ?? data.osVersion, "--");

    /* BATTERY */
    $("batteryValue").textContent = cleanValue(data.Battery ?? data.battery);
    $("batteryStatus").textContent = cleanValue(data.Battery_Status ?? data.battery_status ?? data.batteryStatus, "--");

    /* DEVICE */
    $("manufacturerValue").textContent = cleanValue(data.Manufacturer ?? data.manufacturer);
    $("modelValue").textContent = cleanValue(data.Model ?? data.model, "--");

    /* POWER */
    $("powerLevel").textContent = estimatePower(data, platform);
}


/* =========================================================
   WEBGL GPU FALLBACK
========================================================= */

function getGpuInfo() {
    try {
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
        if (!gl) return "Unavailable";

        const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
        if (!debugInfo) return "Unavailable";

        return gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) || "Unavailable";
    } catch (e) {
        return "Unavailable";
    }
}


/* =========================================================
   WINDOWS SCANNER (DESKTOP APP -> LOCAL SERVER -> BROWSER FALLBACK)
========================================================= */

async function scanWindows() {
    $("scanStatus").textContent = "Scanning system hardware...";

    try {
        let data = null;

        /* 1. Check Desktop App API Bridge (pywebview) */
        if (window.pywebview && window.pywebview.api) {
            data = await window.pywebview.api.get_system_specs();
        } 
        /* 2. Check Local Python Server */
        else {
            try {
                const response = await fetch("http://127.0.0.1:8765/api/system", {
                    method: "GET",
                    cache: "no-store"
                });

                if (response.ok) {
                    data = await response.json();
                }
            } catch (err) {
                console.log("Local server.py not available, switching to browser fallback.");
            }
        }

        /* 3. If Native Data Exists, Render Native Specs */
        if (data && typeof data === "object") {
            showData(data, "windows");
            $("deviceType").textContent = cleanValue(data.Model ?? data.Manufacturer, "Windows Device");
            $("scanStatus").textContent = "Full system scan complete.";
            return;
        }

        /* 4. Fallback: Browser Scan Mode (For Web Viewers without .exe / server.py) */
        const browser = getBrowserInfo();
        const gpuName = getGpuInfo();

        const browserFallback = {
            CPU: browser.threads ? `Browser detects ${browser.threads} threads` : "Unavailable",
            CPU_Cores: "--",
            CPU_Threads: browser.threads || "--",
            RAM_GB: browser.memory || "Unavailable",
            GPU: gpuName,
            VRAM_MB: null,
            GPU_Driver: "Managed by Web Browser",
            Storage: "Requires Desktop App or server.py",
            Display: browser.screen,
            OS: "Windows",
            OS_Version: "Managed by Web Browser",
            Battery: "Unavailable",
            Battery_Status: "--",
            Manufacturer: "Browser Sandbox",
            Model: browser.platform
        };

        showData(browserFallback, "windows");
        $("deviceType").textContent = "Windows Device (Browser Mode)";
        $("scanStatus").textContent = "Basic scan complete. Launch SystemCheck.exe for 100% specs.";

    } catch (error) {
        console.error("Windows scanner error:", error);
        $("scanStatus").textContent = "Error scanning system specs.";
    }
}


/* =========================================================
   ANDROID SCANNER
========================================================= */

function androidBridgeAvailable() {
    return typeof window.AndroidScanner !== "undefined";
}

function getAndroidBridgeData() {
    if (!androidBridgeAvailable()) return null;

    try {
        if (typeof AndroidScanner.getSystemInfo === "function") {
            const result = AndroidScanner.getSystemInfo();
            return typeof result === "string" ? JSON.parse(result) : result;
        }

        if (typeof AndroidScanner.scanDevice === "function") {
            const result = AndroidScanner.scanDevice();
            return typeof result === "string" ? JSON.parse(result) : result;
        }

        return null;
    } catch (error) {
        console.error("Android bridge error:", error);
        return null;
    }
}

async function getAndroidBrowserData() {
    const browser = getBrowserInfo();
    let battery = null;

    try {
        if ("getBattery" in navigator) {
            const batteryManager = await navigator.getBattery();
            battery = {
                level: Math.round(batteryManager.level * 100),
                charging: batteryManager.charging
            };
        }
    } catch (error) {
        console.log("Battery API unavailable");
    }

    return {
        CPU: browser.threads ? `Browser reports ${browser.threads} logical threads` : "Unavailable",
        CPU_Threads: browser.threads || null,
        CPU_Cores: null,
        RAM_GB: browser.memory || null,
        GPU: getGpuInfo(),
        VRAM_MB: null,
        Storage: "Browser cannot reliably identify total storage",
        Display: browser.screen,
        OS: "Android",
        OS_Version: "Available to Android app bridge",
        Battery: battery ? `${battery.level}%` : "Unavailable",
        Battery_Status: battery ? (battery.charging ? "Charging" : "Not charging") : "Unavailable",
        Manufacturer: "Available to Android app bridge",
        Model: "Available to Android app bridge"
    };
}

async function scanAndroid() {
    $("scanStatus").textContent = "Scanning Android device...";

    const nativeData = getAndroidBridgeData();

    if (nativeData && typeof nativeData === "object") {
        showData(nativeData, "android");
        $("deviceType").textContent = cleanValue(nativeData.Model ?? nativeData.model, "Android Device");
        $("scanStatus").textContent = "Android device scan complete.";
        return;
    }

    const browserData = await getAndroidBrowserData();
    showData(browserData, "android");
    $("deviceType").textContent = "Android Device";
    $("scanStatus").textContent = "Browser scan complete. Some hardware requires the Android app.";
}


/* =========================================================
   MAIN SCANNER & INITIALIZE
========================================================= */

async function scanSystem() {
    const platform = detectPlatform();

    setBrowserInfo();
    $("results").classList.remove("hidden");
    $("scanButton").disabled = true;

    try {
        if (platform === "windows") {
            $("platformStatus").textContent = "Windows detected";
            await scanWindows();
        } else if (platform === "android") {
            $("platformStatus").textContent = "Android detected";
            await scanAndroid();
        } else {
            $("platformStatus").textContent = "Unsupported device";
            $("scanStatus").textContent = "SystemCheck currently supports Windows and Android.";
        }
    } catch (error) {
        console.error("SystemCheck error:", error);
    } finally {
        $("scanButton").disabled = false;
    }
}

function initialize() {
    const platform = detectPlatform();

    setBrowserInfo();

    if (platform === "windows") {
        $("platformStatus").textContent = "Windows detected";
    } else if (platform === "android") {
        $("platformStatus").textContent = "Android detected";
    } else {
        $("platformStatus").textContent = "Unsupported device";
    }

    $("scanButton").addEventListener("click", scanSystem);
}

/* START */
initialize();