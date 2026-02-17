
const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let backendProcess;
let backendPort = 8010; // Default, will be updated by stdout

const isDev = process.env.NODE_ENV === 'development';

// Disable hardware acceleration to prevent GPU errors
app.disableHardwareAcceleration();

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 800,
        autoHideMenuBar: true,
        icon: path.join(__dirname, '../frontend/public/TerraSim.png'),
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
        },
    });

    mainWindow.removeMenu();

    if (isDev) {
        // In dev, wait for Vite to serve
        // mainWindow.loadURL('http://localhost:5173');
        mainWindow.loadURL(`http://localhost:5173?backendPort=${backendPort}`);
        mainWindow.webContents.openDevTools();
    } else {
        // In prod, load the built index.html
        // mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
        mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'), { query: { backendPort: backendPort.toString() } });
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startBackend() {
    let scriptPath;
    let cmd;
    let args;

    if (isDev) {
        // Determine python command
        const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
        scriptPath = path.join(__dirname, '../backend/desktop_entry.py');
        cmd = pythonCmd;
        args = [scriptPath];
    } else {
        // Output of PyInstaller
        const exeName = process.platform === 'win32' ? 'backend.exe' : 'backend';
        // In packaged app, resources are usually in process.resourcesPath
        // path depends on electron-builder config
        const backendPath = path.join(process.resourcesPath, 'backend', exeName);
        cmd = backendPath;
        args = [];
    }

    console.log(`Starting backend: ${cmd} ${args.join(' ')}`);

    backendProcess = spawn(cmd, args);

    backendProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log(`[Backend]: ${output}`);

        // Check for "PORT: 12345"
        const match = output.match(/PORT:\s*(\d+)/);
        if (match) {
            backendPort = parseInt(match[1]);
            console.log(`Backend started on port ${backendPort}`);
            if (!mainWindow) {
                createWindow();
            }
        }
    });

    backendProcess.stderr.on('data', (data) => {
        console.error(`[Backend Error]: ${data}`);
    });

    backendProcess.on('close', (code) => {
        console.log(`Backend process exited with code ${code}`);
    });
}

app.whenReady().then(() => {
    startBackend();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    if (backendProcess) {
        backendProcess.kill();
    }
});
