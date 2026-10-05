import os
import json
import re
import platform
import subprocess
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


# ============================================================
# SERVER CONFIGURATION
# ============================================================

HOST = "0.0.0.0"

# Render provides its own PORT.
# When running locally, it will use 8765.
PORT = int(os.environ.get("PORT", 8765))


# ============================================================
# PLATFORM CHECK
# ============================================================

IS_WINDOWS = platform.system().lower() == "windows"


# ============================================================
# POWERSHELL
# ============================================================

def powershell(command):
    """
    Runs PowerShell only when SystemCheck is running on Windows.
    Render normally runs Linux, so this will safely return empty.
    """

    if not IS_WINDOWS:
        return ""

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            return ""

        return result.stdout.strip()

    except Exception as e:
        print("PowerShell error:", e)
        return ""


def powershell_json(command):
    output = powershell(command)

    if not output:
        return None

    try:
        return json.loads(output)

    except Exception as e:
        print("JSON error:", e)
        return None


# ============================================================
# CPU
# ============================================================

def get_cpu():

    if not IS_WINDOWS:
        return {
            "name": "Browser / client detection",
            "cores": None,
            "threads": None,
        }

    command = """
    Get-CimInstance Win32_Processor |
    Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors |
    ConvertTo-Json -Compress
    """

    data = powershell_json(command)

    if not data:
        return {
            "name": "Unavailable",
            "cores": None,
            "threads": None,
        }

    return {
        "name": data.get("Name", "Unavailable"),
        "cores": data.get("NumberOfCores"),
        "threads": data.get("NumberOfLogicalProcessors"),
    }


# ============================================================
# SYSTEM / RAM
# ============================================================

def get_system():

    if not IS_WINDOWS:
        return {
            "manufacturer": "Browser / client",
            "model": "Browser / client",
            "ram_gb": None,
        }

    command = """
    Get-CimInstance Win32_ComputerSystem |
    Select-Object Manufacturer,Model,TotalPhysicalMemory |
    ConvertTo-Json -Compress
    """

    data = powershell_json(command)

    if not data:
        return {
            "manufacturer": "Unavailable",
            "model": "Unavailable",
            "ram_gb": None,
        }

    ram_bytes = data.get("TotalPhysicalMemory")

    ram_gb = None

    if ram_bytes:

        try:
            ram_gb = round(
                int(ram_bytes) / (1024 ** 3),
                2
            )

        except (ValueError, TypeError):
            ram_gb = None

    return {
        "manufacturer": data.get(
            "Manufacturer",
            "Unavailable"
        ),

        "model": data.get(
            "Model",
            "Unavailable"
        ),

        "ram_gb": ram_gb,
    }


# ============================================================
# NVIDIA GPU
# ============================================================

def get_nvidia_gpu():

    if not IS_WINDOWS:
        return None

    try:

        result = subprocess.run(
            [
                "nvidia-smi",

                "--query-gpu=name,memory.total,driver_version",

                "--format=csv,noheader,nounits",
            ],

            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return None

        lines = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

        if not lines:
            return None

        parts = [
            part.strip()
            for part in lines[0].split(",")
        ]

        if len(parts) < 3:
            return None

        gpu_name = parts[0]
        driver = parts[2]

        try:

            vram_mb = int(
                re.sub(
                    r"[^0-9]",
                    "",
                    parts[1]
                )
            )

        except (ValueError, TypeError):

            vram_mb = None

        return {
            "name": gpu_name,
            "vram_mb": vram_mb,
            "driver": driver,
        }

    except Exception as e:

        print(
            "NVIDIA detection error:",
            e
        )

        return None


# ============================================================
# GPU FALLBACK
# ============================================================

def get_gpu_fallback():

    if not IS_WINDOWS:
        return None

    command = """
    Get-CimInstance Win32_VideoController |
    Select-Object Name,AdapterRAM,DriverVersion |
    ConvertTo-Json -Compress
    """

    data = powershell_json(command)

    if not data:
        return None

    if not isinstance(data, list):
        data = [data]

    for gpu in data:

        name = gpu.get("Name")

        if not name:
            continue

        if "Microsoft Basic Display" in str(name):
            continue

        adapter_ram = gpu.get("AdapterRAM")

        vram_mb = None

        if adapter_ram:

            try:

                vram_mb = round(
                    int(adapter_ram)
                    / (1024 ** 2)
                )

            except (ValueError, TypeError):

                pass

        return {
            "name": name,

            "vram_mb": vram_mb,

            "driver": gpu.get(
                "DriverVersion"
            ),
        }

    return None


# ============================================================
# GPU
# ============================================================

def get_gpu():

    gpu = get_nvidia_gpu()

    if gpu:
        return gpu

    return get_gpu_fallback()


# ============================================================
# STORAGE
# ============================================================

def get_storage():

    if not IS_WINDOWS:
        return "Client-side detection required"

    command = """
    Get-CimInstance Win32_DiskDrive |
    Select-Object Model,Size,MediaType |
    ConvertTo-Json -Compress
    """

    data = powershell_json(command)

    if not data:
        return "Unavailable"

    if not isinstance(data, list):
        data = [data]

    drives = []

    for drive in data:

        model = drive.get(
            "Model"
        ) or "Drive"

        size = drive.get("Size")

        if size:

            try:

                size_gb = round(
                    int(size)
                    / (1024 ** 3)
                )

                drives.append(
                    f"{model} ({size_gb} GB)"
                )

            except (ValueError, TypeError):

                drives.append(
                    str(model)
                )

        else:

            drives.append(
                str(model)
            )

    return (
        " | ".join(drives)
        if drives
        else "Unavailable"
    )


# ============================================================
# MOTHERBOARD
# ============================================================

def get_motherboard():

    if not IS_WINDOWS:
        return "Client-side detection required"

    command = """
    Get-CimInstance Win32_BaseBoard |
    Select-Object Manufacturer,Product |
    ConvertTo-Json -Compress
    """

    data = powershell_json(command)

    if not data:
        return "Unavailable"

    if isinstance(data, list):
        data = data[0]

    manufacturer = data.get(
        "Manufacturer"
    )

    product = data.get(
        "Product"
    )

    parts = []

    if manufacturer:
        parts.append(
            str(manufacturer)
        )

    if product:
        parts.append(
            str(product)
        )

    return (
        " ".join(parts)
        if parts
        else "Unavailable"
    )


# ============================================================
# WINDOWS
# ============================================================

def get_windows():

    if not IS_WINDOWS:
        return {
            "name": platform.system(),
            "version": platform.version(),
        }

    command = """
    Get-CimInstance Win32_OperatingSystem |
    Select-Object Caption,Version,BuildNumber |
    ConvertTo-Json -Compress
    """

    data = powershell_json(command)

    if not data:

        return {
            "name": "Windows",
            "version": "Unavailable",
        }

    return {
        "name": data.get(
            "Caption",
            "Windows"
        ),

        "version": (
            f"{data.get('Version', '')} "
            f"(Build {data.get('BuildNumber', '')})"
        ).strip(),
    }


# ============================================================
# BATTERY
# ============================================================

def get_battery():

    if not IS_WINDOWS:

        return {
            "value": "Browser detection",
            "status": "Client-side",
        }

    command = """
    Get-CimInstance Win32_Battery |
    Select-Object EstimatedChargeRemaining,BatteryStatus |
    ConvertTo-Json -Compress
    """

    data = powershell_json(command)

    if not data:

        return {
            "value": "Not available",
            "status": "Desktop / unavailable",
        }

    if isinstance(data, list):
        data = data[0]

    charge = data.get(
        "EstimatedChargeRemaining"
    )

    status_code = data.get(
        "BatteryStatus"
    )

    if charge is not None:
        value = f"{charge}%"

    else:
        value = "Unavailable"

    statuses = {

        1: "Discharging",

        2: "AC power",

        3: "Fully charged",

        4: "Low",

        5: "Critical",

        6: "Charging",

        7: "Charging",

        8: "Charging",

        9: "Charging",

        10: "Undefined",

        11: "Partially charged",
    }

    status = statuses.get(
        status_code,
        "Unknown"
    )

    return {
        "value": value,
        "status": status,
    }


# ============================================================
# DISPLAY
# ============================================================

def get_display():

    if not IS_WINDOWS:
        return "Browser detection"

    command = """
    Get-CimInstance Win32_VideoController |
    Where-Object {
        $_.CurrentHorizontalResolution -gt 0
    } |
    Select-Object -First 1 CurrentHorizontalResolution,
        CurrentVerticalResolution,
        CurrentRefreshRate |
    ConvertTo-Json -Compress
    """

    data = powershell_json(command)

    if not data:
        return "Unavailable"

    if isinstance(data, list):
        data = data[0]

    width = data.get(
        "CurrentHorizontalResolution"
    )

    height = data.get(
        "CurrentVerticalResolution"
    )

    refresh = data.get(
        "CurrentRefreshRate"
    )

    if not width or not height:
        return "Unavailable"

    result = (
        f"{width} × {height}"
    )

    if refresh:
        result += (
            f" @ {refresh} Hz"
        )

    return result


# ============================================================
# COLLECT SYSTEM
# ============================================================

def collect_system():

    cpu = get_cpu()

    system = get_system()

    gpu = get_gpu()

    windows = get_windows()

    battery = get_battery()

    return {

        "CPU": cpu.get(
            "name",
            "Unavailable"
        ),

        "CPU_Cores": cpu.get(
            "cores"
        ),

        "CPU_Threads": cpu.get(
            "threads"
        ),

        "RAM_GB": system.get(
            "ram_gb"
        ),

        "GPU": (
            gpu.get("name")
            if gpu
            else "Unavailable"
        ),

        "VRAM_MB": (
            gpu.get("vram_mb")
            if gpu
            else None
        ),

        "GPU_Driver": (
            gpu.get("driver")
            if gpu
            else "Unavailable"
        ),

        "Manufacturer": system.get(
            "manufacturer",
            "Unavailable"
        ),

        "Model": system.get(
            "model",
            "Unavailable"
        ),

        "Motherboard": get_motherboard(),

        "OS": windows.get(
            "name",
            "Windows"
        ),

        "OS_Version": windows.get(
            "version",
            "Unavailable"
        ),

        "Storage": get_storage(),

        "Battery": battery.get(
            "value",
            "Unavailable"
        ),

        "Battery_Status": battery.get(
            "status",
            "Unknown"
        ),

        "Display": get_display(),

        "Server_Platform": platform.system(),

        "Scanner_Mode": (
            "Windows local scanner"
            if IS_WINDOWS
            else "Browser / Render mode"
        ),
    }


# ============================================================
# HTTP HANDLER
# ============================================================

class SystemCheckHandler(
    SimpleHTTPRequestHandler
):

    def end_headers(self):

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        super().end_headers()


    def do_OPTIONS(self):

        self.send_response(204)

        self.end_headers()


    def do_GET(self):

        # ----------------------------------------------------
        # SYSTEM API
        # ----------------------------------------------------

        if self.path == "/api/system":

            try:

                data = collect_system()

                body = json.dumps(
                    data
                ).encode("utf-8")

                self.send_response(200)

                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8"
                )

                self.send_header(
                    "Cache-Control",
                    "no-store"
                )

                self.send_header(
                    "Content-Length",
                    str(len(body))
                )

                self.end_headers()

                self.wfile.write(body)

            except Exception as e:

                print(
                    "SCAN ERROR:",
                    e
                )

                body = json.dumps(
                    {
                        "error": str(e)
                    }
                ).encode("utf-8")

                self.send_response(500)

                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8"
                )

                self.send_header(
                    "Content-Length",
                    str(len(body))
                )

                self.end_headers()

                self.wfile.write(body)

            return


        # ----------------------------------------------------
        # STATUS API
        # ----------------------------------------------------

        if self.path == "/api/status":

            body = json.dumps(
                {
                    "status": "online",
                    "service": "SystemCheck",
                    "platform": platform.system(),
                    "port": PORT,
                }
            ).encode("utf-8")

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(body))
            )

            self.end_headers()

            self.wfile.write(body)

            return


        # ----------------------------------------------------
        # NORMAL WEBSITE FILES
        # ----------------------------------------------------

        super().do_GET()


# ============================================================
# MAIN SERVER
# ============================================================

def main():

    print()
    print("=" * 55)
    print("                 SYSTEMCHECK")
    print("=" * 55)
    print()

    print(
        f"Platform: {platform.system()}"
    )

    print(
        f"Server: http://{HOST}:{PORT}"
    )

    print()

    if IS_WINDOWS:

        print(
            "Scanner: Windows hardware scanner"
        )

    else:

        print(
            "Scanner: Browser / Render mode"
        )

    print()

    print(
        "SystemCheck server starting..."
    )

    print("=" * 55)
    print()


    server = ThreadingHTTPServer(
        (HOST, PORT),
        SystemCheckHandler
    )


    try:

        server.serve_forever()


    except KeyboardInterrupt:

        print(
            "\nSystemCheck stopped."
        )


    finally:

        server.server_close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()