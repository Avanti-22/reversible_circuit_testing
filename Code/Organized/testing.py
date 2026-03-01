import itertools
from typing import Set
from Code.Organized.Utils.circuitParsingUtilityFunctions import *
from Code.Organized.Utils.SimulatorsfaultCoverageFindingUtilities import *
from Code.Organized.Utils.GAUtilityFunctions import *
import random
import numpy as np
# # Test with your example
if __name__ == "__main__":

    # for single file test

    # Parse it
    circuit = parse_real_file(
        r"C:\Users\thale\OneDrive\Documents\Avanti\MTech\Dissertation\benchmark circuits\fredkin_6.real")
    # #print(circuit)
    # parser = RealFileParser()
    # internal = parser.to_internal_circuit(circuit)
    # #print("\nInternal Format:")
    # for gate in internal:
    #     #print(gate)

    
    
    
    # Steps done till now
    # 1. parsing the circuit
    # 2. generating random input vector
    # 3. simulating the circuit with input vector
    # 4. inducing faults in the circuit
    # 5. simulating the faulty circuit with input vector
    # 6. calculating fault coverage
    
    # now we will implement genetic algorithm to find the best vector
    # 1. initialize the population with random vectors
    
    def save_results_to_csv(results, output_path):
        resultDf = pd.DataFrame(results)
        resultDf.to_csv(output_path, index=False)
    
    
    def run_ga_for_all_files(input_directory , faultModel = "SMGF", population_size=20, max_generations= 20,  output_path = None):
    
        
        circuits =parse_real_directory(input_directory) 
        results = []   
        
        for circuit in circuits:
            
            try:
                    
                print(circuit["Circuit Name"])
                
                if faultModel =="SMGF":
                    
                    GAforSMGF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations)
                    results.append(GAforSMGF.run(verbose=False))
                    
                elif faultModel =="MMGF":
                    
                    GAforMMGF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations)
                    GAforMMGF.run()
                
                elif faultModel =="PMGF":
                    
                    GAforPMGF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations)
                    GAforPMGF.run()
                
                elif faultModel =="GAF":
                    
                    GAforGAF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations)
                    GAforGAF.run()
                
                elif faultModel =="CAF":
                    
                    GAforCAF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations)
                    GAforCAF.run()
                
                elif faultModel =="SA-1":
                    
                    GAforSAF1 = GeneticAlgorithm(circuit, faultModel, population_size, max_generations)
                    GAforSAF1.run()
                
                elif faultModel =="SA-0":
                    
                    GAforSAF0 = GeneticAlgorithm(circuit, faultModel, population_size, max_generations)
                    GAforSAF0.run()
                
                elif faultModel =="RGF":
                    
                    GAforRGF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations)
                    GAforRGF.run()
                
                elif faultModel =="BF":
                    
                    GAforBF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations)
                    GAforBF.run()
                
                elif faultModel =="MBF":
                    
                    GAforMBF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations)
                    GAforMBF.run()
        
                
            except:
                if circuit is None:
                    pass
        # print(results)
            print("done for circuit this")
        if output_path is None:
            output_path = f'{faultModel}_{input_directory.split("/")[-1]}.csv'
        
        save_results_to_csv(results, output_path)
    # run the code for all the circuits. add the code to record time
    # also save the results
    
    
    folder_path = r"Benchmarks Used in Base Paper/small"
    run_ga_for_all_files(folder_path, faultModel = "SMGF")
    
    
    
    
    # str1 = "010"
    # str2  = ("").join(str1)
    # print(str2, str1)
    
    # vector = 4
    
    # binary_vector = format(vector, f'0{3}b')
    # binary_vector = format(vector, '02b')
            
    # print(binary_vector)
    
    # model = "SMGF"
    # calculate_FC_for_fault_model(circuit, model)

    # for directory test

    # circuits =parse_real_directory(r"Benchmarks Used in Base Paper/All Circuits")

    # create_circuit_info_sheet(circuits, "allCircuits.csv")
    # save_to_json(circuits, "allCircuits.json")
