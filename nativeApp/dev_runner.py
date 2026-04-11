# nativeApp/dev_runner.py
import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AutoRestartHandler(FileSystemEventHandler):
    def __init__(self, script_to_run):
        self.script_to_run = script_to_run
        self.process = None
        self.last_restart = time.time()
        self.start_app()

    def start_app(self):
        # Clear terminal for a fresh log view
        import os
        os.system('cls' if os.name == 'nt' else 'clear')

        # Matikan proses lama jika ada
        if self.process:
            self.process.terminate()
            self.process.wait()
            print("\n[DEV] App terminated. Restarting...")
        else:
            print("[DEV] Starting app...")
            
        # Jalankan main.py sebagai subprocess
        self.process = subprocess.Popen([sys.executable, self.script_to_run])

    def on_any_event(self, event):
        # Abaikan folder-folder sistem dan virtual environment
        path = event.src_path.replace("\\", "/").lower()
        ignore_patterns = ["/venv/", "/.venv/", "/__pycache__/", "/.git/", "/.idea/", "/.vscode/"]
        
        if any(p in path for p in ignore_patterns) or path.startswith("venv/"):
            return

        # Hanya peduli jika file .py atau .qss yang berubah
        if event.src_path.endswith('.py') or event.src_path.endswith('.qss'):
            # Mekanisme Debounce: Cegah restart beruntun karena 1 kali save (OS sering mengirim multiple event)
            current_time = time.time()
            if current_time - self.last_restart < 1.0:
                return
            
            self.last_restart = current_time
            print(f"\n[DEV] Detected change in: {event.src_path}")
            self.start_app()

    def check_process(self):
        """Check if the process has died unexpectedly and restart it."""
        if self.process:
            retcode = self.process.poll()
            if retcode is not None:
                # App exited on its own
                if retcode == 0:
                    print(f"\n[DEV] App finished normally (exit 0).")
                else:
                    print(f"\n[DEV] App CRASHED with exit code {retcode}. Restarting in 1s...")
                    time.sleep(1)
                    self.start_app()

if __name__ == "__main__":
    script_name = "main.py"
    
    # Inisialisasi Watcher
    event_handler = AutoRestartHandler(script_name)
    observer = Observer()
    
    # Pantau direktori saat ini (.) beserta subdirektorinya
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()
    
    try:
        while True:
            # Check for crash every second
            event_handler.check_process()
            time.sleep(1) 
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
            print("\n[DEV] Development server stopped.")
    
    observer.join()