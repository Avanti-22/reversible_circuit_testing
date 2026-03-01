from .base import np_array, apply_toffoli, apply_fredkin

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


# ----------------------
# FAULTY SIMULATIONS
# ----------------------

def simulate_faulty_saf(circuit, input_vector, fault):
    vec = input_vector.copy()
    for i, gate in enumerate(circuit):

        if i == fault["location"]:
            vec[fault["wire"]] = fault["value"]

        gtype = gate[0].upper()
        if gtype == "TOFFOLI":
            apply_toffoli(vec, gate[1], gate[2])
        elif gtype == "FREDKIN":
            apply_fredkin(vec, *gate[1])
    return vec


def simulate_faulty_mmgf(circuit, input_vector, fault):
    faulty_circuit = [g for i, g in enumerate(circuit) if i != fault["location"]]
    return simulate_circuit(faulty_circuit, input_vector.copy())


def simulate_faulty_smgf(circuit, input_vector, fault):
    return simulate_faulty_mmgf(circuit, input_vector, fault)


def simulate_faulty_pmgf(circuit, input_vector, fault):
    vec = input_vector.copy()
    for i, gate in enumerate(circuit):
        gtype = gate[0].upper()

        # unconditional flip if fault at this gate
        if i == fault["location"]:
            if gtype == "TOFFOLI":
                apply_toffoli(vec, [], gate[2])
            elif gtype == "FREDKIN":
                _, s1, s2 = gate[1]
                vec[s1], vec[s2] = vec[s2], vec[s1]
            continue

        # normal
        if gtype == "TOFFOLI":
            apply_toffoli(vec, gate[1], gate[2])
        elif gtype == "FREDKIN":
            apply_fredkin(vec, *gate[1])
    return vec


def simulate_faulty_gaf(circuit, input_vector, fault):
    faulty_circuit = []
    for i, gate in enumerate(circuit):
        if i == fault["location"]:
            faulty_circuit.append(fault["extra_gate"])
        faulty_circuit.append(gate)
    return simulate_circuit(faulty_circuit, input_vector.copy())


def simulate_faulty_caf(circuit, input_vector, fault):
    faulty_circuit = []

    for i, gate in enumerate(circuit):
        gtype = gate[0].upper()

        if i == fault["location"]:
            if gtype == "TOFFOLI":
                controls, target = gate[1], gate[2]
                new_controls = list(controls)
                if fault["control"] not in new_controls:
                    new_controls.append(fault["control"])
                faulty_circuit.append(("TOFFOLI", new_controls, target))

            elif gtype == "FREDKIN":
                controls, s1, s2 = gate[1]
                new_controls = list(controls)
                if fault["control"] not in new_controls:
                    new_controls.append(fault["control"])
                faulty_circuit.append(("FREDKIN", (new_controls, s1, s2)))
        else:
            faulty_circuit.append(gate)

    return simulate_circuit(faulty_circuit, input_vector.copy())


def simulate_faulty_bf(circuit, input_vector, fault):
    vec = input_vector.copy()

    for gate in circuit:
        gtype = gate[0].upper()

        if gtype == "TOFFOLI":
            apply_toffoli(vec, gate[1], gate[2])
        elif gtype == "FREDKIN":
            apply_fredkin(vec, *gate[1])

        # Apply bridging
        if fault["mode"] == "AND":
            val = vec[fault["wire1"]] & vec[fault["wire2"]]
        else:
            val = vec[fault["wire1"]] | vec[fault["wire2"]]

        vec[fault["wire1"]] = vec[fault["wire2"]] = val

    return vec
