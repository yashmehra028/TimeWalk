import os
import yaml
import ROOT
import pandas as pd
import re
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy.optimize import curve_fit

# ==========================================
# Geometry and Mask Management
# ==========================================
def parse_mask_file(filepath):
    """
    Reads a pixel mask file and extracts the active pixels.
    Returns a set of (row, col) tuples.
    """
    active_pixels = set()
    if not os.path.isfile(filepath):
        print(f" [!] Error: The mask file '{filepath}' was not found.")
        return active_pixels

    with open(filepath, 'r') as file:
        for line in file:
            line = line.strip()
            # Ignore empty lines or lines that do not contain the 'en' (enable) flag
            if not line or 'en' not in line:
                continue
            
            # Extract row and column indices from the string
            parts = line.split()
            try:
                row = int(parts[1])
                col = int(parts[3])
                active_pixels.add((row, col))
            except (IndexError, ValueError):
                pass
    return active_pixels

class GeometryManager:
    """
    Handles the classification of pixels based on their physical dimensions using a YAML configuration file.
    """
    def __init__(self, yaml_filepath="sensor_geometry.yaml"):
        with open(yaml_filepath, 'r') as file:
            self.geometry_config = yaml.safe_load(file)
            
    def get_pixel_type(self, row, col, chip_id):
        # Determine the configuration block based on the logical chip ID
        if chip_id in [0, 2]:
            config = self.geometry_config['chip_0_2']
        elif chip_id in [1, 3]:
            config = self.geometry_config['chip_1_3']
        else:
            raise ValueError(f"Invalid Chip ID: {chip_id}")

        is_long_row = row in config['long_rows']
        is_long_col = col in config['long_cols']

        # Classify the pixel into one of the four physical sensor geometries
        if is_long_row and is_long_col: return "Macro_Corner" 
        elif is_long_row:               return "Long_Row"
        elif is_long_col:               return "Long_Col"
        else:                           return "Standard"

# ==========================================
# Extraction (ROOT + XML)
# ==========================================
def extract_delay_from_xml(xml_filepath):
    """
    Parses the Ph2_ACF XML configuration file to find the injection delay value.
    """
    if not os.path.isfile(xml_filepath):
        raise FileNotFoundError(f"Error: XML file '{xml_filepath}' not found.")

    pattern = r'CAL_EDGE_FINE_DELAY\s*=\s*"(\d+)"'
    with open(xml_filepath, 'r', encoding='utf-8') as file:
        content = file.read()
        
    match = re.search(pattern, content)
    if match: return int(match.group(1))
    else: raise ValueError(f"Could not find CAL_EDGE_FINE_DELAY in {xml_filepath}")

def get_hist_from_file(root_file, path):
    """
    Extracts TH2 histogram from a ROOT file.
    """
    obj = root_file.Get(path)
    if obj and obj.InheritsFrom("TH2"):
        return obj
    if obj and obj.InheritsFrom("TCanvas"):
        return next((p for p in obj.GetListOfPrimitives() if p.InheritsFrom("TH2")), None)
    return None

# ==========================================
# Data Merger
# ==========================================
def extract_pixel_data(root_filepath, active_pixels, geo_manager, delay_value, hw_chip_id, logical_chip_id):
    """
    Opens the ROOT file produced by Ph2_ACF, extracts the 2D Threshold and Noise maps and values.
    """
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
        
        # Exclude pixels with a threshold of 0
        if thr == 0:
            continue
            
        noise = hist_noise.GetBinContent(col + 1, row + 1)
        data_list.append({
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
# Mathematical Fit Functions
# ==========================================
def sine_func(x, A, B, C, D):
    # Standard sinusoidal function used to find the global trend of the delay scan
    return A * np.sin(B * x + C) + D

def parabola_func(x, a, b, c):
    # Parabolic function. 
    return a * (x - b)**2 + c

# ==========================================
# Graphs Generation
# ==========================================
def generate_plots(chip_dataframe, chip_id):
    plot_dir = "Plots"
    os.makedirs(plot_dir, exist_ok=True)
    print(f"[{plot_dir}] Generating plots for Chip {chip_id} in progress...")

    sns.set_theme(style="ticks", context="talk", font_scale=0.85)
    
    pixel_types = {
        "Macro_Corner": "Big Pixels (87.5 x 225 $\mu m^2$)",
        "Long_Row": "Row Pixels (25 x 225 $\mu m^2$)",
        "Long_Col": "Column Pixels (87.5 x 100 $\mu m^2$)",
        "Standard": "Regular Pixels (25 x 100 $\mu m^2$)"
    }
    
    color_palette = sns.color_palette("Set1", n_colors=4)
    color_map = dict(zip(pixel_types.keys(), color_palette))

    # Iterate over the 4 geometric pixel types to generate individual plots
    for p_type, title in pixel_types.items():
        df_filtered = chip_dataframe[chip_dataframe["Type"] == p_type]
        if df_filtered.empty:
            continue
            
        plt.figure(figsize=(10, 6))
        
        # Plot individual pixel measurements
        sns.scatterplot(
            data=df_filtered, x="Delay", y="Threshold", 
            color=color_map[p_type], alpha=0.05, edgecolor=None, s=20, label="Singular Pixels (Mean)"
        )
        
        # Error bar computation
        # Aggregate the data by delay step. 
        # Compute the mean threshold and noise, and sum the total number of physical runs contributing to this point.
        agg_df = df_filtered.groupby("Delay").agg(
            Mean_Thr=("Threshold", "mean"),
            Mean_Noise=("Noise", "mean"),
            Total_Count=("RunCount", "sum")
        ).reset_index()
        
        # Statistical error of the mean: Average Noise divided by sqrt(N)
        agg_df["Custom_Err"] = agg_df["Mean_Noise"] / np.sqrt(agg_df["Total_Count"])
        
        plt.errorbar(
            x=agg_df["Delay"], y=agg_df["Mean_Thr"], yerr=agg_df["Custom_Err"],
            color="black", marker="o", linewidth=2, capsize=4, label="Mean $\pm$ Noise/$\sqrt{N_{total}}$"
        )
        
        # Fit
        x_data = agg_df['Delay'].values
        y_data = agg_df['Mean_Thr'].values
        yerr_data = agg_df['Custom_Err'].values
        
        # Require at least 5 points to fit a 4-parameter curve
        if len(x_data) >= 5:
            # Skip fitting if the curve is physically flat
            if (np.max(y_data) - np.min(y_data)) < 2.0:
                print(f"   -> Skipping fits for {p_type}: Threshold is practically flat.")
            else:
                try:
                    import warnings
                    from scipy.optimize import OptimizeWarning
                    
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", OptimizeWarning)
                        
                        # Global Sine Fit (Used as a hint)
                        guess_offset = np.mean(y_data)
                        guess_amp = (np.max(y_data) - np.min(y_data)) / 2.0
                        guess_freq = 2.0 * np.pi / 32.0 
                        p0_sine = [guess_amp, guess_freq, 0.0, guess_offset]
                        
                        popt_sine, _ = curve_fit(sine_func, x_data, y_data, p0=p0_sine, maxfev=10000)
                        
                        # Generate sine curve to find its mathematical peak
                        x_sine_scan = np.linspace(np.min(x_data), np.max(x_data), 500)
                        y_sine_scan = sine_func(x_sine_scan, *popt_sine)
                        
                        # Search for the max of the sine wave
                        max_x_sine = x_sine_scan[np.argmax(y_sine_scan)]
                        
                        plt.plot(x_sine_scan, y_sine_scan, color='gray', linestyle=':', alpha=0.5, label='Sine Hint')

                        # Local Parabolic Fit
                        # Use only a 21-point window around the sine maximum
                        idx_center = np.argmin(np.abs(x_data - max_x_sine))
                        idx_start = max(0, idx_center - 10)
                        idx_end = min(len(x_data), idx_center + 11)
                        
                        x_window = x_data[idx_start:idx_end]
                        y_window = y_data[idx_start:idx_end]
                        yerr_window = yerr_data[idx_start:idx_end]
                        
                        yerr_safe = np.where(yerr_window <= 0, 1e-3, yerr_window)
                        
                        # Parabola fit
                        p0_para = [-1.0, max_x_sine, np.max(y_window)]
                        popt_para, pcov_para = curve_fit(
                            parabola_func, x_window, y_window, 
                            p0=p0_para, bounds=([-np.inf, -np.inf, -np.inf], [0, np.inf, np.inf]),
                            sigma=yerr_safe, absolute_sigma=True, maxfev=10000
                        )
                        
                        # Extract the statistical error of the fit parameters
                        perr_para = np.sqrt(np.diag(pcov_para))
                        
                        # Extract the X-coordinate of the vertex and uncertainty
                        max_x_para = popt_para[1]
                        err_x_para = perr_para[1]
                        max_y_para = popt_para[2]

                        # Chi-squared per DOF
                        y_fit_para_pts = parabola_func(x_window, *popt_para)
                        chi_sq = np.sum(((y_window - y_fit_para_pts) / yerr_safe)**2)
                        ndf = len(x_window) - len(popt_para)
                        reduced_chi_sq = chi_sq / ndf if ndf > 0 else 0
                        
                        # Plot the final parabolic fit
                        x_para_plot = np.linspace(np.min(x_window), np.max(x_window), 200)
                        y_para_plot = parabola_func(x_para_plot, *popt_para)
                        
                        plt.plot(x_para_plot, y_para_plot, color='red', linestyle='--', linewidth=2.5, 
                                 label=f'Parabolic Fit ($\chi^2$/ndf = {reduced_chi_sq:.2f})')
                        
                        plt.plot(max_x_para, max_y_para, marker='*', color='gold', markersize=18, 
                                 markeredgecolor='black', 
                                 label=f'Optimal Delay (Max): {max_x_para:.2f} $\pm$ {err_x_para:.2f}')
                        
                except Exception as e:
                    print(f" [!] Fit sequence failed for {p_type}: {e}")
        
        plt.title(f"Chip {chip_id} - Threshold vs Injection Delay\n{title}", pad=15)
        plt.xlabel("CAL_EDGE_FINE_DELAY [DAC units]")
        plt.ylabel("Threshold [VCAL units]")
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        plt.legend(loc="upper right", framealpha=0.95)
        plt.tight_layout()
        
        filename = os.path.join(plot_dir, f"Chip{chip_id}_Threshold_vs_Delay_{p_type}.png")
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        plt.close()

    # Combined Graph (All geometries overlayed)
    plt.figure(figsize=(12, 8))
    
    sns.scatterplot(
        data=chip_dataframe, x="Delay", y="Threshold", hue="Type", palette=color_map,
        alpha=0.03, edgecolor=None, s=15, legend=False
    )
    
    agg_combined = chip_dataframe.groupby(["Delay", "Type"]).agg(
        Mean_Thr=("Threshold", "mean"),
        Mean_Noise=("Noise", "mean"),
        Total_Count=("RunCount", "sum")
    ).reset_index()
    agg_combined["Custom_Err"] = agg_combined["Mean_Noise"] / np.sqrt(agg_combined["Total_Count"])

    for p_type, title in pixel_types.items():
        df_ptype = agg_combined[agg_combined["Type"] == p_type]
        if not df_ptype.empty:
            plt.errorbar(
                x=df_ptype["Delay"], y=df_ptype["Mean_Thr"], yerr=df_ptype["Custom_Err"],
                color=color_map[p_type], marker="o", linewidth=2, capsize=3, label=title
            )
    
    plt.title(f"Chip {chip_id} - Threshold vs Injection Delay: Comparison by Geometry", pad=15, fontweight="bold")
    plt.xlabel("CAL_EDGE_FINE_DELAY [DAC units]")
    plt.ylabel("Threshold [VCAL units]")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.legend(title="Pixel Geometry", loc="upper right", framealpha=0.95)
    plt.tight_layout()
    filename = os.path.join(plot_dir, f"Chip{chip_id}_Threshold_vs_Delay_Combined.png")
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()

# ==========================================
# MASTER LOOP
# ==========================================
if __name__ == "__main__":
    
    # ===================================================
    # USER CONFIGURATION
    # ===================================================
    start_run = 13131
    num_scans = 32
    runs_per_delay = 1
    
    # Map for Quad Module. Format is {Hardware_ID : Logical_ID} and option to esclude certain delays 
    chip_mapping = {0: 0, 1: 1, 2: 2, 3: 3} 
    delays_to_skip = []

    geo = GeometryManager("sensor_geometry.yaml")
    
    # Pre-load mask file for each logical chip ID
    active_masks = {}
    for log_id in chip_mapping.values():
        mask_filepath = f"my_mask_{log_id}.txt"
        print(f"Loading mask for Chip {log_id} from {mask_filepath}...")
        active_masks[log_id] = parse_mask_file(mask_filepath)

    raw_dataframes = []

    # Main execution loop over all delay steps and repetitions
    for delay_step in range(num_scans):
        
        if delay_step in delays_to_skip:
            print(f"\n[!] Skipping Delay = {delay_step} as requested in configuration.")
            continue
            
        for rep in range(runs_per_delay):
            
            # ROOT file number computation
            current_run = start_run + (delay_step * runs_per_delay) + rep
            root_file_name = f"Results/Run{current_run:06d}_SCurve.root"
            
            print(f"\n[{delay_step+1}/{num_scans}] Delay {delay_step} | Extracting Run {current_run} ({rep+1}/{runs_per_delay})...")
            
            for hw_id, log_id in chip_mapping.items():
                try:
                    current_mask = active_masks[log_id]
                    
                    df_chip = extract_pixel_data(
                        root_filepath=root_file_name, 
                        active_pixels=current_mask, 
                        geo_manager=geo, 
                        delay_value=delay_step, 
                        hw_chip_id=hw_id, 
                        logical_chip_id=log_id
                    )
                    
                    if not df_chip.empty:
                        raw_dataframes.append(df_chip)
                        print(f" -> Chip Data {log_id} extracted successfully.")
                    else:
                        print(f" -> No useful data for logical chip {log_id} in this run.")

                except Exception as e:
                    print(f" [!] Error loading chip {hw_id} from run {current_run}: {e}")

    # Process all aggregated data frames
    if raw_dataframes:
        raw_master_df = pd.concat(raw_dataframes, ignore_index=True)
        
        # Per-Pixel Pre-Averaging
        # Groups identical pixels together across their N multiple runs to average their values.
        master_df = raw_master_df.groupby(
            ["Delay", "Chip", "Type", "Row", "Col"]
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
        
        # Generate plots for each chip found in the data
        for c_id in chip_ids_found:
            df_for_this_chip = master_df[master_df["Chip"] == c_id]
            generate_plots(df_for_this_chip, chip_id=c_id)
            
        print("\nAll plots saved in the 'Plots/' directory.")
        
    else:
        print("\nERROR: No data was extracted. Please check the paths and the number of Start Runs.")