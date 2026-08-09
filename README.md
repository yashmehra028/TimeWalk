# MasterThesis
# Master Thesis: CROCv2 Chip Characterization for CMS Inner Tracker

This repository contains the codebase developed for my Master's thesis in Physics at the University of Milano-Bicocca. The work focuses on the characterization, calibration, and performance analysis of the CROCv2 readout chips designed for the Inner Tracker of the CMS experiment.

## Repository Structure

The repository is organized into two main directories, reflecting the primary phases of the thesis project:

### 1. PowerTrimming
This section contains the calibration code developed to tune the analog current consumption of the CROCv2 chips. 
* **Objective:** Establish a reliable calibration routine to optimize the analog power consumption of the readout chips.
* **Contents:** 
  * Scripts for current measurement and tuning.
  * Configuration files for the chip's analog front-end.

### 2. Timewalk
This section is dedicated to studying the timewalk phenomenon and its dependency on the chip's pixel size.
* **Objective:** Investigate and quantify how different pixel geometries impact the timewalk effect, which is critical for the timing resolution of the tracker.
* **Contents:**
  * Code to process and analyze timing data.
  * Algorithms to extract timewalk curves from the raw datasets.
  * Plotting scripts to compare the performance across different pixel dimensions.

## Getting Started

### Prerequisites
*(List the main frameworks and libraries required to run your code here. Common examples in high-energy physics include:)*
* [ROOT](https://root.cern/) (v6.x or higher)
* Python 3.x (numpy, matplotlib, pandas)
* Specific DAQ software (Ph2_ACF)

### Installation
Clone the repository to your local machine:
```bash
git clone [https://github.com/yourusername/your-repo-name.git](https://github.com/yourusername/your-repo-name.git)
cd your-repo-name
