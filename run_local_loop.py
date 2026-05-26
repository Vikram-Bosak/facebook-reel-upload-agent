import time
import subprocess
import sys
import os

def run_agent():
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Reel Automation Agent...")
    python_exe = sys.executable
    script_path = os.path.join(os.path.dirname(__file__), 'src', 'scheduler.py')
    try:
        subprocess.run([python_exe, script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Agent execution failed: {e}")

def main():
    # Run immediately on start
    run_agent()
    
    # Run every 4 hours
    interval_seconds = 4 * 60 * 60 
    print(f"\nAgent loop is active. It will run every 4 hours. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(interval_seconds)
            run_agent()
    except KeyboardInterrupt:
        print("\nLocal agent loop stopped by user.")

if __name__ == '__main__':
    main()
