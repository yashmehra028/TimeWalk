def generate_custom_mask(filename="my_mask.txt"):

    pixels_to_enable = set()
    
    # --- Condition 1: Row R, and columns starting from A down to B, skipping C.
    # range(start, stop, step)
    for c in range(A, B, C):
        pixels_to_enable.add((R, c))
        
    # --- Condition 2: Column C, and rows D, E, F, G
    specific_rows = [D, E, F, G]
    for r in specific_rows:
        pixels_to_enable.add((r, C))
        
    with open(filename, 'w') as f:
        for r, c in sorted(pixels_to_enable):
            f.write(f"row {r} col {c} en\n")
            f.write(f"row {r} col {c} inj\n")
            
    print(f"File {filename} generated successfully!")
    print(f"Total enabled pixels: {len(pixels_to_enable)}")

if __name__ == "__main__":
    generate_custom_mask()