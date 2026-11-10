#!/usr/bin/env python3
"""
Shared helpers for the parabola method in claude_suggested/ (copied and adapted from auto_align.py and
scurve_graph.py so this directory does not depend on its parent).

All relative paths (CMSIT.xml, sensor_geometry.yaml, masks, Results/, H0_ROC*.txt) resolve
inside the folder this file is in: the scripts call enter_workdir() first.
"""
import os
import sys
import yaml
import xml.etree.ElementTree as ET
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# Configuration
# ==========================================
XML_CONFIG = "CMSIT.xml"
YAML_GEO = "sensor_geometry.yaml"
Z_THRESHOLD = 1.5  # Defines Z-compatibility threshold (1.0 = 1 sigma)
REQUIRE_Z_TEST = False  # False: converge on MAX_ABS_SHIFT alone (the Z-score is still printed)
MAX_ABS_SHIFT = 2.0  # delay units (CAL_EDGE_FINE_DELAY steps): a geometry is aligned within this
MAX_ITERATIONS = 5
DRIFT_SIGMA = 2.0  # an aligned geometry is re-opened only if it is past MAX_ABS_SHIFT by more than this many error bars
DAC_HARD_MIN = 0  # register limits only (the search itself has no bounds); 10-bit register, check against the chip manual
DAC_HARD_MAX = 1023
DEFAULT_SLOPE = 0.015  # shift [delay units] per DAC step, used when two scans do not give a usable slope
MIN_SLOPE = 0.002  # a measured slope below this (flat or noisy) is replaced by DEFAULT_SLOPE
MAX_DAC_STEP = 200  # largest DAC change in one iteration
NO_DIP_STEP = 100  # DAC change per iteration while a curve has no dip in the scan window

TARGET_CHIPS = [0, 1, 2, 3]

NUM_SCANS = 32
RUNS_PER_DELAY = 2
DELAY_STEP_SIZE = 2

PIXEL_AREAS = {
    'Macro_Corner': 87.5 * 225.0,
    'Long_Row':     25.0 * 225.0,
    'Long_Col':     87.5 * 100.0,
    'Standard':     25.0 * 100.0,
    'Default':      25.0 * 100.0
}

def enter_workdir():
    os.chdir(HERE)

def mask_for_chip(logical_id):
    return "my_mask_02.txt" if logical_id in [0, 2] else "my_mask_13.txt"

# ==========================================
# Terminal & File Logger (The "Tee" Pattern)
# ==========================================
class Logger:
    def __init__(self, filename="auto_align.log"):
        self.terminal = sys.stdout
        self.log_file = open(filename, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()  # Forces write to disk immediately

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

# ==========================================
# XML / geometry helpers
# ==========================================
def configure_target_chips(xml_file, target_chips):
    tree = ET.parse(xml_file)
    for chip in tree.getroot().iter("RD53Bv2"):
        chip_id = int(chip.attrib.get("Id", -1))
        chip.attrib["enable"] = "1" if chip_id in target_chips else "0"
    tree.write(xml_file, encoding="UTF-8", xml_declaration=True)

def get_dac_mappings(chip_id):
    with open(YAML_GEO, 'r') as file:
        geo = yaml.safe_load(file)
    config_key = 'chip_0_2' if chip_id in [0, 2] else 'chip_1_3'
    return geo[config_key]['preamp_dac_mapping']

def get_xml_register(xml_file, register_name, chip_id):
    tree = ET.parse(xml_file)
    for chip in tree.getroot().iter("RD53Bv2"):
        if chip.attrib.get("Id") == str(chip_id):
            return int(chip.find("Settings").attrib[register_name])

def update_xml_registers(xml_file, multi_updates_dict):
    tree = ET.parse(xml_file)
    for chip in tree.getroot().iter("RD53Bv2"):
        chip_id = int(chip.attrib.get("Id", -1))
        if chip_id in multi_updates_dict:
            settings = chip.find("Settings")
            for reg, val in multi_updates_dict[chip_id].items():
                settings.attrib[reg] = str(int(val))
    tree.write(xml_file, encoding="UTF-8", xml_declaration=True)

class GeometryManager:
    def __init__(self, yaml_filepath=YAML_GEO):
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
# Masks and ROOT extraction
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
                active_pixels.add((int(parts[1]), int(parts[3])))
            except (IndexError, ValueError):
                pass
    return active_pixels

def get_hist_from_file(root_file, path):
    obj = root_file.Get(path)
    if obj and obj.InheritsFrom("TH2"):
        return obj
    if obj and obj.InheritsFrom("TCanvas"):
        return next((p for p in obj.GetListOfPrimitives() if p.InheritsFrom("TH2")), None)
    return None

def extract_pixel_data(root_filepath, active_pixels, geo_manager, delay_value, hw_chip_id, logical_chip_id):
    import ROOT  # imported here so the aligner does not need ROOT

    root_file = ROOT.TFile.Open(root_filepath, "READ")
    if not root_file or root_file.IsZombie():
        return pd.DataFrame()

    base = f"Detector/Board_0/OpticalGroup_0/Hybrid_0/Chip_{hw_chip_id}/D_B(0)_O(0)_H(0)"
    hist_thr = get_hist_from_file(root_file, f"{base}_Threshold2D_Chip({hw_chip_id})")
    hist_noise = get_hist_from_file(root_file, f"{base}_Noise2D_Chip({hw_chip_id})")
    if not hist_thr or not hist_noise:
        root_file.Close()
        return pd.DataFrame()

    data_list = []
    for row, col in active_pixels:
        thr = hist_thr.GetBinContent(col + 1, row + 1)
        if thr == 0:
            continue
        data_list.append({
            "Delay": delay_value,
            "Chip": logical_chip_id,
            "Row": row,
            "Col": col,
            "Type": geo_manager.get_pixel_type(row, col, logical_chip_id),
            "Threshold": thr,
            "Noise": hist_noise.GetBinContent(col + 1, row + 1),
        })

    root_file.Close()
    return pd.DataFrame(data_list)
