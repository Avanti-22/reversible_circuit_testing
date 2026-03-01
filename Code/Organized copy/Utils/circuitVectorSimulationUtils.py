import numpy as np

def np_array(x, copy=True):
    return np.array(x, dtype=np.int8, copy=copy)

def apply_toffoli(vec, controls, target):
    if all(vec[c] == 1 for c in controls):
        vec[target] ^= 1

def apply_fredkin(vec, controls, s1, s2):
    if all(vec[c] == 1 for c in controls):
        vec[s1], vec[s2] = vec[s2], vec[s1]

# ----------------------
# FAULT-FREE SIMULATION
# ----------------------
def simulate_circuit(circuit, input_vector):
    vec = np_array(input_vector, copy=True)
    for gate in circuit:
        gtype = gate[0].upper()
        if gtype == "TOFFOLI":
            controls, target = gate[1], gate[2]
            apply_toffoli(vec, controls, target)
        elif gtype == "FREDKIN":
            controls, s1, s2 = gate[1]
            apply_fredkin(vec, controls, s1, s2)
    return vec

