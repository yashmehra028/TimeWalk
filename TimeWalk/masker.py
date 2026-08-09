def generate_custom_mask(filename="my_mask.txt"):

    pixels_to_enable = set()
    
    # --- Condition 1: Row 0, and columns starting from 431 down to 0, skipping 8.
    # range(start, stop, step)
    for c in range(0, 432, 8):
        pixels_to_enable.add((1, c))
        
    # --- Condition 2: Column 431, and rows 0, 100, 200, 300
    specific_rows = [1, 100, 200, 300]
    for r in specific_rows:
        pixels_to_enable.add((r, 0))
        
    with open(filename, 'w') as f:
        for r, c in sorted(pixels_to_enable):
            f.write(f"row {r} col {c} en\n")
            f.write(f"row {r} col {c} inj\n")
            
    print(f"File {filename} generated successfully!")
    print(f"Total enabled pixels: {len(pixels_to_enable)}")

if __name__ == "__main__":
    generate_custom_mask()