#!/usr/bin/env python3
"""
Interactive terminal app to control the Ollama service.
Run this script to access an interactive menu for starting, stopping, 
and checking the status of the Ollama service.
"""

import sys
import subprocess
import requests
import time


def check_ollama_running(base_url: str = "http://localhost:11434") -> bool:
    """Check if Ollama service is running by attempting to connect."""
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=2)
        return response.status_code == 200
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False


def run_command(cmd: list, check: bool = True) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout, e.stderr


def start_ollama():
    """Start the Ollama service."""
    print("\n" + "="*50)
    print("Starting Ollama service...")
    print("="*50)
    
    # First check if it's already running
    if check_ollama_running():
        print("✓ Ollama is already running.")
        input("\nPress Enter to continue...")
        return 0
    
    # Try systemd service first (Linux)
    code, stdout, stderr = run_command(["systemctl", "start", "ollama"], check=False)
    if code == 0:
        print("✓ Started Ollama via systemd.")
        # Wait a bit for service to start
        time.sleep(2)
        if check_ollama_running():
            print("✓ Ollama service is running.")
            input("\nPress Enter to continue...")
            return 0
        else:
            print("⚠ Ollama service started but not responding yet. It may still be starting.")
            input("\nPress Enter to continue...")
            return 0
    
    # Try direct ollama serve command (if installed as user service)
    code, stdout, stderr = run_command(["ollama", "serve"], check=False)
    if code == 0 or "already" in stderr.lower() or "already" in stdout.lower():
        print("✓ Started Ollama directly.")
        time.sleep(2)
        if check_ollama_running():
            print("✓ Ollama service is running.")
            input("\nPress Enter to continue...")
            return 0
    
    # Check if it's running now (may have started in background)
    if check_ollama_running():
        print("✓ Ollama is now running.")
        input("\nPress Enter to continue...")
        return 0
    
    print("✗ Failed to start Ollama. Try running 'ollama serve' manually.")
    print(f"  Error: {stderr}")
    input("\nPress Enter to continue...")
    return 1


def stop_ollama():
    """Stop the Ollama service."""
    print("\n" + "="*50)
    print("Stopping Ollama service...")
    print("="*50)
    
    # First check if it's running
    if not check_ollama_running():
        print("✓ Ollama is not running.")
        input("\nPress Enter to continue...")
        return 0
    
    # Try systemd service first (Linux)
    code, stdout, stderr = run_command(["systemctl", "stop", "ollama"], check=False)
    if code == 0:
        print("✓ Stopped Ollama via systemd.")
        time.sleep(1)
        if not check_ollama_running():
            print("✓ Ollama service stopped.")
            input("\nPress Enter to continue...")
            return 0
    
    # Try to find and kill ollama processes
    code, stdout, stderr = run_command(["pkill", "-f", "ollama"], check=False)
    if code == 0:
        print("✓ Stopped Ollama processes.")
        time.sleep(1)
        if not check_ollama_running():
            print("✓ Ollama service stopped.")
            input("\nPress Enter to continue...")
            return 0
    
    # Final check
    if not check_ollama_running():
        print("✓ Ollama service stopped.")
        input("\nPress Enter to continue...")
        return 0
    
    print("⚠ Ollama may still be running. Check with 'ps aux | grep ollama'")
    input("\nPress Enter to continue...")
    return 1


def restart_ollama():
    """Restart the Ollama service."""
    print("\n" + "="*50)
    print("Restarting Ollama service...")
    print("="*50)
    
    # Stop without user interaction prompts
    if check_ollama_running():
        print("Stopping Ollama...")
        run_command(["systemctl", "stop", "ollama"], check=False)
        run_command(["pkill", "-f", "ollama"], check=False)
        time.sleep(2)
    
    # Start
    return start_ollama()


def status_ollama():
    """Check the status of the Ollama service."""
    print("\n" + "="*50)
    print("Ollama Service Status")
    print("="*50)
    
    is_running = check_ollama_running()
    
    if is_running:
        print("✓ Ollama is running.")
        print(f"  URL: http://localhost:11434")
        # Try to get version info
        try:
            response = requests.get("http://localhost:11434/api/version", timeout=2)
            if response.status_code == 200:
                version_info = response.json()
                print(f"  Version: {version_info.get('version', 'unknown')}")
        except:
            pass
        # Try to get model list
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                if models:
                    print(f"  Available models: {len(models)}")
                    for model in models[:5]:  # Show first 5
                        print(f"    - {model.get('name', 'unknown')}")
                    if len(models) > 5:
                        print(f"    ... and {len(models) - 5} more")
        except:
            pass
    else:
        print("✗ Ollama is not running.")
    print("="*50)
    input("\nPress Enter to continue...")
    return 0 if is_running else 1


def clear_screen():
    """Clear the terminal screen."""
    subprocess.run(["clear"], check=False)


def print_menu(current_status: str):
    """Print the interactive menu."""
    clear_screen()
    print("╔" + "="*48 + "╗")
    print("║" + " "*10 + "Ollama Service Controller" + " "*12 + "║")
    print("╠" + "="*48 + "╣")
    print(f"║ Status: {current_status:<39} ║")
    print("╠" + "="*48 + "╣")
    print("║" + " "*48 + "║")
    print("║  1. Start Ollama service" + " "*24 + "║")
    print("║  2. Stop Ollama service" + " "*25 + "║")
    print("║  3. Restart Ollama service" + " "*22 + "║")
    print("║  4. Check Status" + " "*31 + "║")
    print("║  5. Exit" + " "*39 + "║")
    print("║" + " "*48 + "║")
    print("╚" + "="*48 + "╝")
    print()


def main():
    """Main interactive entry point."""
    print("Starting Ollama Service Controller...")
    time.sleep(0.5)
    
    while True:
        # Get current status
        is_running = check_ollama_running()
        status_text = "✓ Running" if is_running else "✗ Stopped"
        
        # Print menu
        print_menu(status_text)
        
        # Get user choice
        try:
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == "1":
                start_ollama()
            elif choice == "2":
                stop_ollama()
            elif choice == "3":
                restart_ollama()
            elif choice == "4":
                status_ollama()
            elif choice == "5":
                print("\n" + "="*50)
                print("Exiting Ollama Service Controller...")
                print("="*50 + "\n")
                break
            else:
                print("\n✗ Invalid choice. Please enter a number between 1 and 5.")
                time.sleep(1.5)
        
        except KeyboardInterrupt:
            print("\n\n" + "="*50)
            print("Exiting Ollama Service Controller...")
            print("="*50 + "\n")
            break
        except EOFError:
            print("\n\n" + "="*50)
            print("Exiting Ollama Service Controller...")
            print("="*50 + "\n")
            break
        except Exception as e:
            print(f"\n✗ An error occurred: {e}")
            input("Press Enter to continue...")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
