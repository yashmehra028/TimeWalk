import re
import os
import time
import subprocess
import sys
import argparse
import yaml

RUN_MAP_FILE = "scan_runs.yaml"   # {run number: delay}, read by scurve_graph_flank.py --run_map

def run_numbers():
    """Run numbers of all ROOT files in Results/ (a directory listing, fast even for thousands)."""
    if not os.path.isdir("Results"):
        return set()
    return {int(m.group(1)) for f in os.listdir("Results")
            if f.endswith(".root") and (m := re.match(r"Run(\d+)", f))}

def run_scurve_scan(xml_filename="CMSIT_RD53B.xml", num_scans=32, runs_per_delay=5, step_size=2):
    delays = list(range(0, num_scans, step_size))
    total_runs = len(delays) * runs_per_delay
    print(f"Starting SCurve scan: {len(delays)} delay steps x {runs_per_delay} runs/step = {total_runs} total iterations.")
    
    try:
        with open(xml_filename, 'r', encoding='utf-8') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{xml_filename}' was not found in the current directory!")
        sys.exit(1)

    run_map = {}
    for delay_idx, delay in enumerate(delays):
        print(f"\n=======================================================")
        print(f" Configuring CAL_EDGE_FINE_DELAY = {delay}")
        print(f"=======================================================\n")
        
        new_content = re.sub(
            r'CAL_EDGE_FINE_DELAY\s*=\s*"\d+"', 
            f'CAL_EDGE_FINE_DELAY="{delay}"', 
            content
        )
        
        with open(xml_filename, 'w', encoding='utf-8') as file:
            file.write(new_content)
            
        for rep in range(runs_per_delay):
            current_iteration = (delay_idx * runs_per_delay) + rep + 1
            print(f"--> Executing SCurve {rep+1}/{runs_per_delay} for Delay {delay} (Global: {current_iteration}/{total_runs})")
            
            before = run_numbers()   # a crashed run's leftover file is in here, so it's never recorded
            try:
                subprocess.run(
                    ["CMSITminiDAQ", "-f", xml_filename, "-c", "scurve"], 
                    check=True,
                    timeout=180
                )
                print(f"SUCCESS! SCurve {rep+1} for delay {delay} completed.")
                new = run_numbers() - before
                if not new:
                    print(f"[!] SCurve {rep+1} for delay {delay} finished but wrote no ROOT file: point skipped")
                for run in new:
                    run_map[run] = delay

            except subprocess.CalledProcessError:
                print(f"\n[!] WARNING: Run crashed (Data Corruption / Out of range).")
                print(f"    Delay {delay} seems physically unstable. Skipping the remaining {runs_per_delay - rep - 1} runs for this delay...")
                time.sleep(5)
                break
                
            except subprocess.TimeoutExpired:
                print(f"\n[!] TIMEOUT: Run is stuck in infinite 'retries'. Aborting.")
                print(f"    Delay {delay} seems physically unstable. Skipping the remaining {runs_per_delay - rep - 1} runs for this delay...")
                time.sleep(5)
                break
                
        content = new_content

    with open(RUN_MAP_FILE, "w") as f:
        yaml.safe_dump(run_map, f)
    print("\n--- Automated SCurve scan complete! ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute SCurve scans for Ph2_ACF.")
    parser.add_argument('--xml_filename', type=str, default="CMSIT.xml", help="Target XML configuration file")
    parser.add_argument('--num_scans', type=int, default=32, help="Max delay boundary")
    parser.add_argument('--runs_per_delay', type=int, default=4, help="Repeated SCurve runs per delay step")
    parser.add_argument('--step_size', type=int, default=2, help="Step size for delay injection")
    args = parser.parse_args()

    run_scurve_scan(
        xml_filename=args.xml_filename, 
        num_scans=args.num_scans, 
        runs_per_delay=args.runs_per_delay,
        step_size=args.step_size
    )