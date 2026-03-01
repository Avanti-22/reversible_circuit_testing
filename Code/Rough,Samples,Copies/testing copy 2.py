from Code.Organized.Utils.circuitParsingUtilityFunctions import *
import random
# # Test with your example
if __name__ == "__main__":

    
    # for single file test
    
    # Parse it
    circuit = parse_real_file(r"C:\Users\thale\OneDrive\Documents\Avanti\MTech\Dissertation\benchmark circuits\fredkin_6.real")
    print(circuit)
    # parser = RealFileParser()
    # internal = parser.to_internal_circuit(circuit)
    # print("\nInternal Format:")
    # for gate in internal:
    #     print(gate)
    
    def convert_integer_to_binary(input_vector, maxValue):
        binaryVector = []
        while (input_vector>=1):
            print(input_vector)
            bit = input_vector%2
            binaryVector.append(bit)
            input_vector = input_vector // 2
        
    
        while(len(binaryVector)<maxValue):
            binaryVector.append(0)
            
        binaryVector.reverse()    
        
        return binaryVector
        
    def generate_random_vector(circuit):
        maxValue = circuit["No of Lines"]
        # inputVector= int(input("Enter the integer between 0-"+str(2**maxValue -1)+"for creating binary vector: "))
        
        inputVector = random.randint(0, 2**maxValue -1)
        binaryVector = convert_integer_to_binary(inputVector, maxValue)
        print(binaryVector)
        return binaryVector

    def simulate_circuit(circuit, binaryVector):
        # vector processing throught the circuit
        gates = circuit["Gates"]
        
        # create a circuit with variables replaced with input values
        indexVariableMap={}
        for i in range (len(binaryVector)):
            indexVariableMap[circuit["Variables"][i]] = i

        print(indexVariableMap)
              
        intermediateVector = binaryVector.copy()
        
        # replace variables in gates with input values from binary vector
        count = 0
        for gate in gates:
            type = gate["gate"]
            gateParts = gate["vars"]
            
            print("For gate level: ",count)
            print("Input vector: ",intermediateVector)
            
            # ****WORKING FOR TOFFOLI GATE
            # process the vector for toffoli gate at current level
            if(type == "TOFFOLI"):        
                
                if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-1)):
                    # print("control activates the target bit")
                    index = indexVariableMap[gateParts[-1]]
                    intermediateVector[index] = 1- intermediateVector[index]
            
                count += 1
            
            # process the vector for toffoli gate at current level    
            elif(type == "FREDKIN"):
                if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-2)):
                    # print("control activates the target bit")
                    index1 = indexVariableMap[gateParts[-2]]
                    index2 = indexVariableMap[gateParts[-1]]
                    
                    # swap the target bits
                    intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
                count += 1
            
            # process the vector for toffoli gate at current level    
            if(type == "PERES"):
                
                # calculate the secondlast target bit
                secondLastIndex = indexVariableMap[gateParts[-2]]
                thirdLastIndex = indexVariableMap[gateParts[-3]]
                intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex]^intermediateVector[secondLastIndex]
                    
                if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-1)):
                    lastIndex =indexVariableMap[gateParts[-1]]
                    intermediateVector[lastIndex] = 1-intermediateVector[lastIndex]
                
                count += 1
                
                
            # print("after current gate, the intermediate vector: ",intermediateVector)
        print("after processing through the circuit, final put vector: ",intermediateVector)
        return intermediateVector     
    # taking vector input and converting integer to binary
    
    def print_circuit_representation(circuit, isFaulty=False):
        if isFaulty:
            faultPosition = circuit["Fault Position"]
            faultModel = circuit["Fault Model"]
            
            for i, gate in enumerate(circuit["Gates"]):
                print(f"Gate {i}: ", end=" ")
                for j, var in enumerate(gate["vars"]):
                    if (i, var) == faultPosition:
                        if faultModel == "SA0":
                            print(f"{var}(0)", end=" ")
                        elif faultModel == "SA1":
                            print(f"{var}(1)", end=" ")
                    else:
                        print(f"{var}", end=" ")                
                print()    
                    
    def faultCov_for_SAF(circuit, fault_model):
        # for each gate in gates
            # for each control point(var in vars)
        level= None
        wire=None
        faultPosition=(level, wire)
        faultyCircuit = circuit.copy()
        faultCount =0
        
        # SA -0 FAULT 
        if fault_model =="SA-0":
            faultyCircuit["Fault Model"] = fault_model
            for i, gate in enumerate(circuit["Gates"]):
                # print(gate)
                for j, var in enumerate(gate["vars"]):
                    # print(var)  
                    faultPosition = (i, var)
                    faultCount +=1
                    print("SA-0 at level(Gate)", i,"wire(variable)", j,"(", var,")")  
                    faultyCircuit["Fault Position"] = faultPosition
                    # print_circuit_representation(faultyCircuit, isFaulty=True)
        
        # SA -1 FAULT             
        elif fault_model =="SA-1":  
            faultyCircuit["Fault Model"] = fault_model
            for i, gate in enumerate(circuit["Gates"]):
                # print(gate)
                for j, var in enumerate(gate["vars"]):
                    # print(var)  
                    faultPosition = (i, var)
                    faultCount +=1
                    print("SA-1 at level(Gate)", i,"wire(variable)", j,"(", var,")")  
                    faultyCircuit["Fault Position"] = faultPosition  
                    # print_circuit_representation(faultyCircuit, isFaulty=True)
        
        print("SAF count:", faultCount)            # print("here")
                    
    def faultCov_for_SMGF(circuit):
        
        # for each gate in gates
            # for each control point(var in vars)
        level= None
        faultyCircuit = circuit.copy()
        faultyCircuit["Fault Model"] = "SMGF"
        faultCount=0
        for i, gate in enumerate(circuit["Gates"]):
            # skip gate
            faultPosition=[]
            faultPosition.append()
            faultyCircuit["Fault Position"] = faultPosition
            print("SMGF at level(Gate)", i)
            faultCount +=1
            # print_circuit_representation(faultyCircuit, isFaulty=True)
               # print("here")
        print("SMGF count:",faultCount)            
                    
    def faultCov_for_MMGF(circuit):  
        
        # for each gate in gates
            # for each control point(var in vars)
        faultPositions=[]
        faultyCircuit = circuit.copy()
        faultyCircuit["Fault Model"] = "MMFG"
        faultCount=0
        
        # for different no of missing gates starting from single missing, double missing to n-1 missing
        noLevels = circuit["No of Gates"]
        maxFaults = circuit["No of Gates"]-1
        # maxFaults = 5
        # singleton sets

        answer = []
        elementCount =0
        
        for setSize in range( maxFaults):
      
            mset = answer.copy()

            
            while elementCount <= setSize:

                if not mset:
                    for index in range(noLevels):
                        iset = []
                        iset.append(index)
                        mset.append(iset)
                        faultyCircuit["Fault Position"] = iset
                        print("MMGF faults at levels(Gate)", faultyCircuit["Fault Position"])
                        faultCount +=1
                    
                elif mset:
                    for index, subset  in  enumerate(mset) :
                        if (len(subset) == setSize):
                            
                            nextIndex = subset[-1]
                            for i in range(nextIndex+1, noLevels):
                                iset = subset.copy()
                                iset.append(i)
                                mset.append(iset)
                                faultyCircuit["Fault Position"] = iset
                                print("MMGF faults at levels(Gate)", faultyCircuit["Fault Position"])
                                faultCount +=1
                elementCount+=1
            setSize+=1
            answer = mset.copy()
        print("MMGF count:", faultCount)   
            
    def faultCov_for_PMGF(circuit):
        
        level= None
        wires=[]
        faultPosition=(level, wires)
        faultyCircuit = circuit.copy()
        faultyCircuit["Fault Model"] = "PMFG"
        faultCount=0
        noLines = circuit["No of Lines"]
        maxFaults = circuit["No of Lines"]-1
        
        
        # outer for loop for iterating through the gates
        for i, gate in enumerate(circuit["Gates"]):
            # inner for loop to miss the partial control bits with all the possible combinations
            
            # for different no of missing gates starting from single missing, double missing to n-1 missing
            answer = []
            elementCount =0
            
            for setSize in range( maxFaults):
                
                mset = answer.copy()
                while elementCount <= setSize:

                    if not mset:
                        for wire, var in enumerate(gate["Vars"]): 
                            iset = []
                            iset.append(wire)
                            mset.append(iset)
                            wires = iset
                            level =i
                            faultyCircuit["Fault Position"] = faultPosition
                            print("PMGF faults for gate (",level,") at control(var) ", wires)
                            faultCount +=1
                        
                    elif mset:
                        for index, subset  in  enumerate(mset) :
                            if (len(subset) == setSize):
                                
                                nextIndex = subset[-1]
                                for i in range(nextIndex+1, len(gate["Vars"])):
                                    iset = subset.copy()
                                    iset.append(i)
                                    mset.append(iset)
                                    wires = iset
                                    level =i
                                    faultyCircuit["Fault Position"] = faultPosition
                                    print("PMGF faults for gate (",level,") at control(var) ", wires)
                                    faultCount +=1
                    elementCount+=1
                setSize+=1
                answer = mset.copy()
            # print_circuit_representation(faultyCircuit, isFaulty=True)
               # print("here")
        print("PMGF count:",faultCount)      
        
    def faultCov_for_RGF(circuit, n = "Even"):
        # for each gate in gates repeate the gates 
        level= None
        faultyCircuit = circuit.copy()
        faultyCircuit["Fault Model"] = "RGF-Even" if n=="Even" else "RGF-Odd"
        faultCount=0
        for i, gate in enumerate(circuit["Gates"]):
            # skip gate
            faultyCircuit["Fault Position"] = i
            print("RGF at level(Gate)", i)
            faultCount +=1
            # print_circuit_representation(faultyCircuit, isFaulty=True)
               # print("here")
        print("RGF count:",faultCount)    
        
    def faultCov_for_GAF(circuit):
        # add extra gate after any one gate in the circuit
        level= None
        faultyCircuit = circuit.copy()
        faultyCircuit["Fault Model"] = "GAF"
        faultCount=0
        for i in range(len(circuit["Gates"])+1):
            # add gate
            faultyCircuit["Fault Position"] = i-1
            print("GAF at level(Gate)", i-1)
            faultCount +=1
            # print_circuit_representation(faultyCircuit, isFaulty=True)
               # print("here")
        print("GAF count:",faultCount)    
        
    def faultCov_for_CAF(circuit):
        # add extra control in any one gate in the circuit
        level= None
        wire=None
        faultPosition=(level, wire)
        faultyCircuit = circuit.copy()
        faultyCircuit["Fault Model"] = "CAF"
        faultCount=0
        for i, gate in enumerate(circuit["Gates"]):
            for j, var in enumerate(circuit["Variables"]):
                # skip gate
                if var in gate["vars"]:
                    continue
                faultPosition = (i, var)
                faultyCircuit["Fault Position"] = faultPosition
                print("CAF at level(Gate)", faultPosition[0],"wire(variable)", faultPosition[1])
                faultCount +=1
            # print_circuit_representation(faultyCircuit, isFaulty=True)
               # print("here")
        print("CAF count:",faultCount)      
        
    def faultCov_for_BridgingFault(circuit):
        # for each gate in gates
        # for each pair of wires 
        # induce "AND-wired" and "OR-wired" bridging faults
        faultyCircuit = circuit.copy()
        faultyCircuit["Fault Model"] = "BF"
        faultCount=0
        variables = circuit["Variables"]
        for i, gate in enumerate(circuit["Gates"]):
            for j in range (len(variables)):
                for k in range(j+1, len(variables)):
                    wire1 = variables[j]
                    wire2 = variables[k]
                    
                    # AND-wired bridging fault
                    faultPosition = (i, wire1, wire2, "AND-wired")
                    faultyCircuit["Fault Position"] = faultPosition
                    print("Bridging Fault (AND-wired) at level(Gate)", faultPosition[0],"between wires(variables)", faultPosition[1], "and", faultPosition[2])
                    faultCount +=1
                    
                    # OR-wired bridging fault
                    faultPosition = (i, wire1, wire2, "OR-wired")
                    faultyCircuit["Fault Position"] = faultPosition
                    print("Bridging Fault (OR-wired) at level(Gate)", faultPosition[0],"between wires(variables)", faultPosition[1], "and", faultPosition[2])
                    faultCount +=1
                    
            # print_circuit_representation(faultyCircuit, isFaulty=True)
               # print("here")
        print("Bridging Fault count:",faultCount) 
             
    def faultCov_for_MultipleBridgingFault(circuit, max_faults_per_gate=2):
        # for each gate in gates
        # consider multiple simultaneous bridging faults
        # induce "AND-wired" and "OR-wired" bridging faults
        faultyCircuit = circuit.copy()
        faultyCircuit["Fault Model"] = "Multiple BF"
        faultCount=0
        variables = circuit["Variables"]
        for i, gate in enumerate(circuit["Gates"]):
            # build all possible single bridging faults first
            single_faults = []
            for j in range(len(variables)):
                for k in range(j+1, len(variables)):
                    wire1 = variables[j]
                    wire2 = variables[k]
                    single_faults.append((wire1, wire2, "AND-wired"))
                    single_faults.append((wire1, wire2, "OR-wired"))

            # cap to avoid combinational explosion unless user asks otherwise
            if max_faults_per_gate is None:
                max_faults = len(single_faults)
            else:
                max_faults = min(max_faults_per_gate, len(single_faults))

            # generate combinations of multiple faults (size 2..max_faults)
            for set_size in range(2, max_faults + 1):
                answer = []
                elementCount = 0
                mset = []

                while elementCount <= set_size:
                    if not mset:
                        for index in range(len(single_faults)):
                            iset = []
                            iset.append(index)
                            mset.append(iset)
                            if len(iset) == set_size:
                                faultPosition = [(i, *single_faults[x]) for x in iset]
                                faultyCircuit["Fault Position"] = faultPosition
                                print("Multiple BF at level(Gate)", i, "faults", faultPosition)
                                faultCount +=1
                    else:
                        for subset in mset:
                            if len(subset) == set_size:
                                continue
                            nextIndex = subset[-1]
                            for idx in range(nextIndex+1, len(single_faults)):
                                iset = subset.copy()
                                iset.append(idx)
                                if len(iset) == set_size:
                                    faultPosition = [(i, *single_faults[x]) for x in iset]
                                    faultyCircuit["Fault Position"] = faultPosition
                                    print("Multiple BF at level(Gate)", i, "faults", faultPosition)
                                    faultCount +=1
                                mset.append(iset)
                    elementCount +=1
        print("Multiple Bridging Fault count:", faultCount)
    
    faultCov_for_SAF(circuit, fault_model="SA-0") 
    # faultCov_for_SMGF(circuit)
    # faultCov_for_MMGF(circuit)    
    # faultCov_for_PMGF(circuit) 
    # faultCov_for_RGF(circuit, n="Even")   
    # faultCov_for_RGF(circuit, n="Odd")   
    # faultCov_for_GAF(circuit)
    # faultCov_for_CAF(circuit)
    # faultCov_for_BridgingFault(circuit)
    # faultCov_for_MultipleBridgingFault(circuit)
     
            
# use this function to calculate fault coverage for different fault models
# in this function we will call the respective fault coverage functions defined above
# the above cunctions will generate all faulty circuits for the given fault model
# and immediately simulate the generated faulty circuit with a set of input vectors
# and compare the output with the golden output to calculate the fault coverage
# it means that inside each fault coverage function we will have to call the simulate_circuit function
# and compare the output with the golden output obtained from simulating the original circuit
# the golden output can be given as an input to the faultCov functions by canculating it at the start of the below function
# once we have the golden output we can pass it to each fault coverage function
# then inside each fault coverage function we can simulate the faulty circuit and compare the output with the golden output
# finally we can calculate the fault coverage as the ratio of detected faults to total faults injected
# we can return the fault coverage value from each fault coverage function

# one thing needs to be decided, whether we want a single simulation function which can be called inside each fault coverage function
# or we will have to define separate simulation functions for each fault model
# the single simulation function approach is better as it will reduce code redundancy
# but it will require passing additional parameters to the simulation function to handle different fault models
# and we will also have modify the simulation function to handle faults during simulation
# first we will make changes to the simulate_circuit function to handle faults during simulation
# one more thing, should we have one function for simulating fault free circuit and another for simulating faulty circuit
# or should we have a single function which can handle both fault free and faulty circuit simulation
# the single function approach is better as it will reduce code redundancy
# but it will require passing additional parameters to the simulation function to handle faults
# we can pass a flag to the simulation function to indicate whether we are simulating a faulty circuit or a fault free circuit

# so lets make the changes to the simulate_circuit function first to handle faults during simulation
    
    
    
    
    # def simulate_MGF_circuit(circuit, binaryVector, faultModel, faultPosition):
    #     # vector processing throught the circuit
    #     gates = circuit["Gates"]
        
    #     # create a circuit with variables replaced with input values
    #     indexVariableMap={}
    #     for i in range (len(binaryVector)):
    #         indexVariableMap[circuit["Variables"][i]] = i

    #     print(indexVariableMap)
              
    #     intermediateVector = binaryVector.copy()
        
    #     # replace variables in gates with input values from binary vector
    #     count = 0
    #     for gate in gates:
    #         type = gate["gate"]
    #         gateParts = gate["vars"]
            
    #         print("For gate level: ",count)
    #         print("Input vector: ",intermediateVector)
            
    #         # check if current gate is faulty
    #         if faultModel in ["SMGF", "MMGF", "PMGF"] and count in faultPosition:
    #             print(f"Skipping gate at level {count} due to {faultModel} fault")
    #             count += 1
    #             continue
            
    #         # ****WORKING FOR TOFFOLI GATE
    #         # process the vector for toffoli gate at current level
    #         if(type == "TOFFOLI"):        
                
    #             if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-1)):
    #                 # print("control activates the target bit")
    #                 index = indexVariableMap[gateParts[-1]]
    #                 intermediateVector[index] = 1- intermediateVector[index]
            
    #             count += 1
            
    #         # process the vector for toffoli gate at current level    
    #         elif(type == "FREDKIN"):
    #             if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-2)):
    #                 # print("control activates the target bit")
    #                 index1 = indexVariableMap[gateParts[-2]]
    #                 index2 = indexVariableMap[gateParts[-1]]
                    
    #                 # swap the target bits
    #                 intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
    #             count += 1
            
    #         # process the vector for toffoli gate at current level    
    #         if(type == "PERES"):
                
    #             # calculate the secondlast target bit
    #             secondLastIndex = indexVariableMap[gateParts[-2]]
    #             thirdLastIndex = indexVariableMap[gateParts[-3]]
    #             intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex]^intermediateVector[secondLastIndex]
    #         count += 1
                
                
    #         # print("after current gate, the intermediate vector: ",intermediateVector)
    #     print("after processing through the circuit, final put vector: ",intermediateVector)
    #     return intermediateVector         
    
    # def simulate_SAF_circuit(circuit, binaryVector, faultModel, faultPosition):
    #     # vector processing throught the circuit
    #     gates = circuit["Gates"]
        
    #     # create a circuit with variables replaced with input values
    #     indexVariableMap={}
    #     for i in range (len(binaryVector)):
    #         indexVariableMap[circuit["Variables"][i]] = i

    #     print(indexVariableMap)
              
    #     intermediateVector = binaryVector.copy()
        
    #     # replace variables in gates with input values from binary vector
    #     count = 0
    #     for gate in gates:
    #         type = gate["gate"]
    #         gateParts = gate["vars"]
            
    #         print("For gate level: ",count)
    #         print("Input vector: ",intermediateVector)
            
    #         # check if current gate has a SAF fault
    #         if faultModel in ["SA-0", "SA-1"]:
    #             for var in gateParts:
    #                 if (count, var) == faultPosition:
    #                     if faultModel == "SA-0":
    #                         print(f"Stuck-at-0 fault at level {count} on variable {var}")
    #                         intermediateVector[indexVariableMap[var]] = 0
    #                     elif faultModel == "SA-1":
    #                         print(f"Stuck-at-1 fault at level {count} on variable {var}")
    #                         intermediateVector[indexVariableMap[var]] = 1
            
    #         # ****WORKING FOR TOFFOLI GATE
    #         # process the vector for toffoli gate at current level
    #         if(type == "TOFFOLI"):        
                
    #             if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-1)):
    #                 # print("control activates the target bit")
    #                 index = indexVariableMap[gateParts[-1]]
    #                 intermediateVector[index] = 1- intermediateVector[index]
            
    #             count += 1
            
    #         # process the vector for toffoli gate at current level    
    #         elif(type == "FREDKIN"):
    #             if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-2)):
    #                 # print("control activates the target bit")
    #                 index1 = indexVariableMap[gateParts[-2]]
    #                 index2 = indexVariableMap[gateParts[-1]]
                    
    #                 # swap the target bits
    #                 intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
    #             count += 1
    #             # print("after current gate, the intermediate vector: ",intermediateVector)
    #     print("after processing through the circuit, final put vector: ",intermediateVector)
    #     return intermediateVector
            
    
    # def simulate_PMGF_circuit(circuit, binaryVector, faultModel, faultPosition):
        
    
    def simulate_circuit_with_fault(circuit, binaryVector, isFaulty=False):

        # vector processing throught the circuit
        gates = circuit["Gates"]
        
        # create a circuit with variables replaced with input values
        indexVariableMap={}
        for i in range (len(binaryVector)):
            indexVariableMap[circuit["Variables"][i]] = i

        print(indexVariableMap)
              
        intermediateVector = binaryVector.copy()
        
        # replace variables in gates with input values from binary vector
        count = 0
        for gate in gates:
            type = gate["gate"]
            gateParts = gate["vars"]
            
            print("For gate level: ",count)
            print("Input vector: ",intermediateVector)
            
            if isFaulty:
                faultModel = circuit["Fault Model"]
                faultPosition = circuit["Fault Positions"]
                
                # check if current gate is faulty
                if faultModel in ["SMGF", "MMGF"] and count in faultPosition:
                    print(f"Skipping gate at level {count} due to {faultModel} fault")
                    count += 1
                    continue
                
                if faultModel in ["SA-1", "SA-0"]:
                    for var in gateParts:
                        if (count, var) == faultPosition:
                            if faultModel == "SA-0":
                                print(f"Stuck-at-0 fault at level {count} on variable {var}")
                                intermediateVector[indexVariableMap[var]] = 0
                            elif faultModel == "SA-1":
                                print(f"Stuck-at-1 fault at level {count} on variable {var}")
                                intermediateVector[indexVariableMap[var]] = 1
                
                if faultModel in ["PMGF"]:
                    for i, var in enumerate(gateParts):
                        if count == faultPosition[0] and i in faultPosition[1]:
                            print(f"PMGF at level {count} on variable {var}")
                            intermediateVector[indexVariableMap[var]] = 0
                            
                    
                    
                
                    
                # if faultModel in [""]:
                
            
            
            # ****WORKING FOR TOFFOLI GATE
            # process the vector for toffoli gate at current level
            if(type == "TOFFOLI"):        
                
                if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-1)):
                    # print("control activates the target bit")
                    index = indexVariableMap[gateParts[-1]]
                    intermediateVector[index] = 1- intermediateVector[index]
            
                count += 1
            
            # process the vector for toffoli gate at current level    
            elif(type == "FREDKIN"):
                if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-2)):
                    # print("control activates the target bit")
                    index1 = indexVariableMap[gateParts[-2]]
                    index2 = indexVariableMap[gateParts[-1]]
                    
                    # swap the target bits
                    intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
                count += 1
            
            # process the vector for toffoli gate at current level    
            if(type == "PERES"):
                
                # calculate the secondlast target bit
                secondLastIndex = indexVariableMap[gateParts[-2]]
                thirdLastIndex = indexVariableMap[gateParts[-3]]
                intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex]^intermediateVector[secondLastIndex]
                    
                if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-1)):
                    lastIndex =indexVariableMap[gateParts[-1]]
                    intermediateVector[lastIndex] = 1-intermediateVector[lastIndex]
                
                count += 1
                
                
            # print("after current gate, the intermediate vector: ",intermediateVector)
        print("after processing through the circuit, final put vector: ",intermediateVector)
        return intermediateVector     
    
    
    
    
    
    
    
    
    
    
    # def simulate_circuit(circuit, binaryVector):
        
    #     # vector processing throught the circuit
    #     gates = circuit["Gates"]
        
    #     # create a circuit with variables replaced with input values
    #     indexVariableMap={}
    #     for i in range (len(binaryVector)):
    #         indexVariableMap[circuit["Variables"][i]] = i

    #     print(indexVariableMap)
              
    #     intermediateVector = binaryVector.copy()
        
    #     # replace variables in gates with input values from binary vector
    #     count = 0
    #     for gate in gates:
    #         type = gate["gate"]
    #         gateParts = gate["vars"]
            
    #         print("For gate level: ",count)
    #         print("Input vector: ",intermediateVector)
            
    #         # ****WORKING FOR TOFFOLI GATE
    #         # process the vector for toffoli gate at current level
    #         if(type == "TOFFOLI"):        
                
    #             if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-1)):
    #                 # print("control activates the target bit")
    #                 index = indexVariableMap[gateParts[-1]]
    #                 intermediateVector[index] = 1- intermediateVector[index]
            
    #             count += 1
            
    #         # process the vector for toffoli gate at current level    
    #         elif(type == "FREDKIN"):
    #             if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-2)):
    #                 # print("control activates the target bit")
    #                 index1 = indexVariableMap[gateParts[-2]]
    #                 index2 = indexVariableMap[gateParts[-1]]
                    
    #                 # swap the target bits
    #                 intermediateVector[index1], intermediateVector[index2] = intermediateVector[index2], intermediateVector[index1]
    #             count += 1
            
    #         # process the vector for toffoli gate at current level    
    #         if(type == "PERES"):
                
    #             # calculate the secondlast target bit
    #             secondLastIndex = indexVariableMap[gateParts[-2]]
    #             thirdLastIndex = indexVariableMap[gateParts[-3]]
    #             intermediateVector[secondLastIndex] = intermediateVector[thirdLastIndex]^intermediateVector[secondLastIndex]
                    
    #             if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-1)):
    #                 lastIndex =indexVariableMap[gateParts[-1]]
    #                 intermediateVector[lastIndex] = 1-intermediateVector[lastIndex]
                
    #             count += 1
                
                
    #         # print("after current gate, the intermediate vector: ",intermediateVector)
    #     print("after processing through the circuit, final put vector: ",intermediateVector)
    #     return intermediateVector     
    # # taking vector input and converting integer to binary




#   def calculate_FC_for_fault_model(circuit, fault_model):
              
#         # SMGF FAULT
#         elif fault_model =="SMGF":
            
                    
#         # PMGF FAULT
#         elif fault_model =="PMGF":
        
#         # MMGF FAULT    
#         elif fault_model =="MMGF":
        
#         # RGF FAULT
#         elif fault_model =="RGF":
        
#         # GAF FAULT    
#         elif fault_model =="GAF":
        
#         # CAF FAULT    
#         elif fault_model =="CAF":
        
#         # BF FAULT    
#         elif fault_model =="BF":
        
        
        
        
        
        # print("Fault injected circuit: ", circuit["Gates"])
        # return faultyCircuit
 
    
    
    
    # for directory test
    
    # circuits =parse_real_directory(r"Benchmarks Used in Base Paper/All Circuits")

    # create_circuit_info_sheet(circuits, "allCircuits.csv")
    # save_to_json(circuits, "allCircuits.json")
