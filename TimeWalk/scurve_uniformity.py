import os
import yaml
import ROOT
import pandas as pd
import re
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ==========================================
# Geometry and Mask Management
# ==========================================
def parse_mask_file(filepath):
    active_pixels = set()
    if not os.path.isfile(filepath):
        print(f" [!] Error: The mask file '{filepath}' was not found.")
        return active_pixels

    with open(filepath, 'r') as file:
        for line in file:
            line = line.strip()
            if not line or 'en' not in line:
                continue

            parts = line.split()
            try:
                row = int(parts[1])
                col = int(parts[3])
                active_pixels.add((row, col))
            except (IndexError, ValueError):
                pass
    return active_pixels

class GeometryManager:
    def __init__(self, yaml_filepath="sensor_geometry.yaml"):
        with open(yaml_filepath, 'r') as file:
            self.geometry_config = yaml.safe_load(file)
            
    def get_pixel_type(self, row, col, chip_id):
        if chip_id in [0, 2]:
            config = self.geometry_config['chip_0_2']
        elif chip_id in [1, 3]:
            config = self.geometry_config['chip_1_3']
        else:
            raise ValueError(f"Invalid Chip ID: {chip_id}")

        is_long_row = row in config['long_rows']
        is_long_col = col in config['long_cols']

        if is_long_row and is_long_col: return "Macro_Corner" 
        elif is_long_row:               return "Long_Row"
        elif is_long_col:               return "Long_Col"
        else:                           return "Standard"

# ==========================================
# Data Extraction
# ==========================================
def get_hist_from_file(root_file, path):
    obj = root_file.Get(path)
    if obj and obj.InheritsFrom("TH2"):
        return obj
    if obj and obj.InheritsFrom("TCanvas"):
        return next((p for p in obj.GetListOfPrimitives() if p.InheritsFrom("TH2")), None)
    return None

def extract_pixel_data(root_filepath, active_pixels, geo_manager, delay_value, hw_chip_id, logical_chip_id, scan_label):
    root_file = ROOT.TFile.Open(root_filepath, "READ")
    if not root_file or root_file.IsZombie(): 
        return pd.DataFrame()

    exact_thr_path = f"Detector/Board_0/OpticalGroup_0/Hybrid_0/Chip_{hw_chip_id}/D_B(0)_O(0)_H(0)_Threshold2D_Chip({hw_chip_id})"
    exact_noise_path = f"Detector/Board_0/OpticalGroup_0/Hybrid_0/Chip_{hw_chip_id}/D_B(0)_O(0)_H(0)_Noise2D_Chip({hw_chip_id})"

    hist_thr = get_hist_from_file(root_file, exact_thr_path)
    hist_noise = get_hist_from_file(root_file, exact_noise_path)
        
    if not hist_thr or not hist_noise:
        root_file.Close()
        return pd.DataFrame()

    data_list = []
    for row, col in active_pixels:
        thr = hist_thr.GetBinContent(col + 1, row + 1)
        
        # Filter out masked/failed pixels
        if thr == 0:
            continue
            
        noise = hist_noise.GetBinContent(col + 1, row + 1)
        data_list.append({
            "ScanLabel": scan_label, # NEW: Track which scan this belongs to
            "Delay": delay_value, 
            "Chip": logical_chip_id, 
            "Row": row, 
            "Col": col,
            "Type": geo_manager.get_pixel_type(row, col, logical_chip_id),
            "Threshold": thr,
            "Noise": noise
        })

    root_file.Close()
    return pd.DataFrame(data_list)

# ==========================================
# Comparison Plot Generation
# ==========================================
def generate_comparison_plots(chip_dataframe, chip_id):
    plot_dir = "Comparison_Plots"
    os.makedirs(plot_dir, exist_ok=True)
    print(f"[{plot_dir}] Generating comparative plots for Chip {chip_id} in progress...")

    sns.set_theme(style="ticks", context="talk", font_scale=0.85)
    
    pixel_types = {
        "Macro_Corner": "Big Pixels (87.5 x 225 $\mu m^2$)",
        "Long_Row": "Row Pixels (25 x 225 $\mu m^2$)",
        "Long_Col": "Column Pixels (87.5 x 100 $\mu m^2$)",
        "Standard": "Regular Pixels (25 x 100 $\mu m^2$)"
    }
    
    # Get unique scans to create a color palette for the different masks
    unique_scans = chip_dataframe["ScanLabel"].unique()
    scan_colors = dict(zip(unique_scans, sns.color_palette("husl", len(unique_scans))))

    # 1. Individual Graphs for Each Pixel Type Comparing the N Scans
    for p_type, title in pixel_types.items():
        df_filtered = chip_dataframe[chip_dataframe["Type"] == p_type]
        if df_filtered.empty:
            continue
            
        plt.figure(figsize=(12, 8))
        
        # Aggregate data: Group by ScanLabel and Delay
        agg_df = df_filtered.groupby(["ScanLabel", "Delay"]).agg(
            Mean_Thr=("Threshold", "mean"),
            Mean_Noise=("Noise", "mean"),
            Total_Count=("RunCount", "sum") 
        ).reset_index()
        
        agg_df["Custom_Err"] = agg_df["Mean_Noise"] / np.sqrt(agg_df["Total_Count"])
        
        # Plot a line with error bars for each scan
        for scan_label in unique_scans:
            scan_data = agg_df[agg_df["ScanLabel"] == scan_label]
            if not scan_data.empty:
                plt.errorbar(
                    x=scan_data["Delay"], y=scan_data["Mean_Thr"], yerr=scan_data["Custom_Err"],
                    color=scan_colors[scan_label], marker="o", linewidth=2, capsize=4, 
                    label=f"{scan_label} (Mean $\pm$ Noise/$\sqrt{{N}}$)"
                )
        
        plt.title(f"Chip {chip_id} - {title}\nStability Comparison Across Different Masks", pad=15, fontweight="bold")
        plt.xlabel("CAL_EDGE_FINE_DELAY [DAC units]")
        plt.ylabel("Threshold [VCAL units]")
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.legend(title="Scan Configurations", loc="upper right", framealpha=0.95)
        plt.tight_layout()
        
        filename = os.path.join(plot_dir, f"Chip{chip_id}_Comparison_{p_type}.png")
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        plt.close()

# ==========================================
# MASTER LOOP
# ==========================================
if __name__ == "__main__":
    
    # ===================================================
    # USER CONFIGURATION: DEFINE YOUR N SCANS HERE
    # ===================================================
    num_scans_per_config = 32
    runs_per_delay = 5     
    chip_mapping = {0: 0, 1: 1, 2: 2, 3: 3} 
    delays_to_skip = []
    
    # Define as many scans as you want to compare
    scans_config = [
        {
            "label": "Mask 1", 
            "start_run": 12081, 
            "masks": {0: "masks/my_mask_run1.txt", 1: "txt/row0/my_mask_full_1.txt", 2: "txt/row0/my_mask_full_2.txt", 3: "txt/row0/my_mask_full_3.txt"}
        },
        {
            "label": "Mask 2", 
            "start_run": 12248, 
            "masks": {0: "masks/my_mask_run2.txt", 1: "txt/row0/my_mask_check_1.txt", 2: "txt/row0/my_mask_check_2.txt", 3: "txt/row0/my_mask_check_3.txt"}
        },
        {
            "label": "Mask 3", 
            "start_run": 12415, 
            "masks": {0: "masks/my_mask_run3.txt", 1: "txt/row0/my_mask_sparse_1.txt", 2: "txt/row0/my_mask_sparse_2.txt", 3: "txt/row0/my_mask_sparse_3.txt"}
        },
         {
            "label": "Mask 4", 
            "start_run": 12582, 
            "masks": {0: "masks/my_mask_run4.txt", 1: "txt/row0/my_mask_full_1.txt", 2: "txt/row0/my_mask_full_2.txt", 3: "txt/row0/my_mask_full_3.txt"}
        },
         {
            "label": "Mask 5", 
            "start_run": 12762, 
            "masks": {0: "masks/my_mask_run5.txt", 1: "txt/row0/my_mask_full_1.txt", 2: "txt/row0/my_mask_full_2.txt", 3: "txt/row0/my_mask_full_3.txt"}
        }
    ]
    # ===================================================
    
    geo = GeometryManager("sensor_geometry.yaml")
    raw_dataframes = []

    # Loop over the N different scan configurations
    for scan in scans_config:
        scan_label = scan["label"]
        start_run = scan["start_run"]
        mask_dict = scan["masks"]
        
        print(f"\n=======================================================")
        print(f" Processing Scan: {scan_label} | Start Run: {start_run}")
        print(f"=======================================================\n")
        
        # Parse the active pixels for this specific scan
        active_masks = {}
        for log_id, filepath in mask_dict.items():
            if log_id in chip_mapping.values():
                active_masks[log_id] = parse_mask_file(filepath)

        for delay_step in range(num_scans_per_config):
            if delay_step in delays_to_skip:
                continue
                
            for rep in range(runs_per_delay):
                current_run = start_run + (delay_step * runs_per_delay) + rep
                root_file_name = f"Results/Run{current_run:06d}_SCurve.root"
                
                print(f" [{delay_step+1}/{num_scans_per_config}] Delay {delay_step} | Extracting Run {current_run} ({rep+1}/{runs_per_delay})...")
                
                for hw_id, log_id in chip_mapping.items():
                    try:
                        current_mask = active_masks.get(log_id, set())
                        if not current_mask: continue
                        
                        df_chip = extract_pixel_data(
                            root_filepath=root_file_name, 
                            active_pixels=current_mask, 
                            geo_manager=geo, 
                            delay_value=delay_step, 
                            hw_chip_id=hw_id, 
                            logical_chip_id=log_id,
                            scan_label=scan_label # Pass the label to the dataframe
                        )
                        
                        if not df_chip.empty:
                            raw_dataframes.append(df_chip)
                    except Exception as e:
                        print(f" [!] Error loading chip {hw_id} from run {current_run}: {e}")

    if raw_dataframes:
        raw_master_df = pd.concat(raw_dataframes, ignore_index=True)
        
        # Per-Pixel Pre-Averaging (Now including ScanLabel in the groupby)
        master_df = raw_master_df.groupby(
            ["ScanLabel", "Delay", "Chip", "Type", "Row", "Col"]
        ).agg(
            Threshold=("Threshold", "mean"),
            Noise=("Noise", "mean"),
            RunCount=("Threshold", "count")
        ).reset_index()

        print(f"\n======================================")
        print(f"Extraction completed! Total raw measurements: {len(raw_master_df)}")
        print(f"Total valid pixels processed: {len(master_df)}")
        print(f"======================================\n")
        
        chip_ids_found = master_df["Chip"].unique()
        
        for c_id in chip_ids_found:
            df_for_this_chip = master_df[master_df["Chip"] == c_id]
            generate_comparison_plots(df_for_this_chip, chip_id=c_id)
            
        print("\nAll comparison plots saved in the 'Comparison_Plots/' directory.")
    else:
        print("\nERROR: No data was extracted. Please check the paths and the start runs.")