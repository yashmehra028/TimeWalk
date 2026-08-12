import re
import time
import subprocess
import sys

def run_scurve_scan(xml_filename="CMSIT_RD53B.xml", num_scans=32, runs_per_delay=5):
    total_runs = num_scans * runs_per_delay
    print(f"Starting SCurve scan: {num_scans} delays x {runs_per_delay} runs/delay = {total_runs} total iterations.")
    
    # 1. Load the initial XML file
    try:
        with open(xml_filename, 'r', encoding='utf-8') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{xml_filename}' was not found in the current directory!")
        sys.exit(1)

    # 2. Loop over the delay values
    for delay in range(num_scans):
        print(f"\n=======================================================")
        print(f" Configuring CAL_EDGE_FINE_DELAY = {delay}")
        print(f"=======================================================\n")
        
        # Modify the XML content in memory (Only needs to happen once per delay)
        new_content = re.sub(
            r'CAL_EDGE_FINE_DELAY\s*=\s*"\d+"', 
            f'CAL_EDGE_FINE_DELAY="{delay}"', 
            content
        )
        
        # Write the updated content back to the file
        with open(xml_filename, 'w', encoding='utf-8') as file:
            file.write(new_content)
            
        # 3. Inner loop: Run the DAQ multiple times for this specific delay
        for rep in range(runs_per_delay):
            current_iteration = (delay * runs_per_delay) + rep + 1
            print(f"--> Executing SCurve {rep+1}/{runs_per_delay} for Delay {delay} (Global: {current_iteration}/{total_runs})")
            
            try:
                # timeout=180 stops the process if it takes more than 3 minutes (180 seconds).
                subprocess.run(
                    ["CMSITminiDAQ", "-f", xml_filename, "-c", "scurve"], 
                    check=True,
                    timeout=180
                )
                print(f"SUCCESS! SCurve {rep+1} for delay {delay} completed.")

            except subprocess.CalledProcessError:
                # Triggered if CMSITminiDAQ exits with an error code (Data Corruption)
                print(f"\n[!] WARNING: Run crashed (Data Corruption / Out of range).")
                print(f"    Delay {delay} seems physically unstable. Skipping the remaining {runs_per_delay - rep - 1} runs for this delay...")
                time.sleep(5)
                break
                
            except subprocess.TimeoutExpired:
                # Triggered if CMSITminiDAQ gets stuck in an infinite "retry" loop
                print(f"\n[!] TIMEOUT: Run is stuck in infinite 'retries'. Aborting.")
                print(f"    Delay {delay} seems physically unstable. Skipping the remaining {runs_per_delay - rep - 1} runs for this delay...")
                time.sleep(5)
                break
                
        # Update the content variable
        content = new_content

    print("\n--- Automated SCurve scan complete! ---")

if __name__ == "__main__":
    run_scurve_scan(xml_filename="CMSIT_RD53B.xml", num_scans=32, runs_per_delay=5)