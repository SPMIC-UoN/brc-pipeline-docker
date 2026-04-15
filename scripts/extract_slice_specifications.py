import json
import sys
import numpy as np

with open(sys.argv[1], "r") as f:
    data = json.load(f)

slice_timing = [float(x) for x in data.get("SliceTiming", [])]
sorted_indices = sorted(range(len(slice_timing)), key=lambda i: slice_timing[i])
sorted_values = np.array([slice_timing[i] for i in sorted_indices])

# Number of bands
nb = len(sorted_indices) // (len(np.unique(sorted_values[sorted_values !=0])) + 1)

reshaped_indices = np.reshape(sorted_indices, [-1, nb])
with open(sys.argv[2], "w") as f:
    for vals in reshaped_indices:
        f.write(" ".join([str(v).rjust(3) for v in vals]) + "\n")

