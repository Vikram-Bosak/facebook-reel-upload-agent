import time
import subprocess
import sys
import os

def run_agent():
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Reel Automation Agent...")
    python_exe = sys.executable
    script_path = os.path.join(os.path.dirname(__file__), 'src', 'scheduler.py')
    try:
        # We run the scheduler script directly
        subprocess.run([python_exe, script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Agent execution failed: {e}")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Unexpected execution failure: {e}")

def main():
    # Run immediately on start
    run_agent()
    
    # Run every 30 minutes (1800 seconds)
    interval_seconds = 30 * 60 
    print(f"\nAgent loop is active. Scanning queue and schedules every 30 minutes. Press Ctrl+C to stop.")
    try:
        while True:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sleeping for 30 minutes...")
            time.sleep(interval_seconds)
            run_agent()
    except KeyboardInterrupt:
        print("\nLocal agent loop stopped by user.")


if __name__ == '__main__':
    main()
