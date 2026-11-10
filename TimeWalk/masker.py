def generate_custom_mask_02(filename="my_mask.txt"):
    pixels_to_enable = set()
    
    # Row 1 on one set of alternating core columns (0, 16, 32...)
    for c in range(0, 432, 16):
        pixels_to_enable.add((1, c))

    # Row 50 on the OTHER set of alternating core columns (8, 24, 40...)
    for c in range(8, 432, 16):
       pixels_to_enable.add((100, c))

    specific_rows = [1, 50, 100, 150, 200, 250, 300]
    for r in specific_rows:
       pixels_to_enable.add((r, 0))

    pixels_to_enable.add((0, 0))

    with open(filename, 'w') as f:
        for r, c in sorted(pixels_to_enable):
            f.write(f"row {r} col {c} en\n")
            f.write(f"row {r} col {c} inj\n")

    print(f"File {filename} generated successfully!")
    print(f"Total enabled pixels: {len(pixels_to_enable)}")

def generate_custom_mask_13(filename="my_mask.txt"):
    pixels_to_enable = set()
    
    # Row 1 on one set of alternating core columns (0, 16, 32...)
    for c in range(0, 431, 16):
        pixels_to_enable.add((1, c))

    # Row 50 on the OTHER set of alternating core columns (8, 24, 40...)
    for c in range(8, 431, 16):
       pixels_to_enable.add((100, c))

    specific_rows = [1, 50, 100, 150, 200, 250, 300]
    for r in specific_rows:
        pixels_to_enable.add((r, 431))

    pixels_to_enable.add((0, 431))

    with open(filename, 'w') as f:
        for r, c in sorted(pixels_to_enable):
            f.write(f"row {r} col {c} en\n")
            f.write(f"row {r} col {c} inj\n")

    print(f"File {filename} generated successfully!")
    print(f"Total enabled pixels: {len(pixels_to_enable)}")

if __name__ == "__main__":
    generate_custom_mask_02("my_mask_02.txt")
    generate_custom_mask_13("my_mask_13.txt")