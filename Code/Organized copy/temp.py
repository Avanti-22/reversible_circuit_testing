import itertools
from typing import Set
from Utils.circuitParsingUtilityFunctions import *
from Utils.SimulatorsfaultCoverageFindingUtilities import *
# from Utils.GAUtilityFunctions import *
# from Utils.Ga2 import *
from Utils.Optimized_GA import *
import random
import numpy as np
# # Test with your example



def save_results_to_csv(results, output_path):
        resultDf = pd.DataFrame(results)
        resultDf.to_csv(output_path, index=False)
    
    
def run_ga_for_all_files(input_directory , faultModel = "SMGF", population_size=20, max_generations= 20,  output_path=None, verbose=False):
    # print("here")
    
    circuits =parse_real_directory(input_directory) 
    # print(circuits)
    results = []   
    
    for circuit in circuits:
        # print("here")
        try:
                
            print(circuit["Circuit Name"])
            
            if faultModel =="SMGF":
                
                GAforSMGF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations, time_limit_seconds = 180.0)
                results.append(GAforSMGF.run(verbose))
                
            elif faultModel =="MMGF":
                
                GAforMMGF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations, time_limit_seconds = 180.0)
                results.append(GAforMMGF.run(verbose))
            
            elif faultModel =="PMGF":
                
                GAforPMGF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations, time_limit_seconds = 180.0)
                results.append(GAforPMGF.run(verbose))
            
            elif faultModel =="GAF":
                
                GAforGAF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations, time_limit_seconds = 180.0)
                results.append(GAforGAF.run(verbose))
            
            elif faultModel =="CAF":
                
                GAforCAF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations, time_limit_seconds = 180.0)
                results.append(GAforCAF.run(verbose))
            
            elif faultModel =="SA-1":
                
                GAforSAF1 = GeneticAlgorithm(circuit, faultModel, population_size, max_generations, time_limit_seconds = 180.0)
                results.append(GAforSAF1.run(verbose))
            
            elif faultModel =="SA-0":
                
                GAforSAF0 = GeneticAlgorithm(circuit, faultModel, population_size, max_generations, time_limit_seconds = 180.0)
                results.append(GAforSAF0.run(verbose))
            
            elif faultModel =="RGF":
                
                GAforRGF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations, time_limit_seconds = 180.0)
                results.append(GAforRGF.run(verbose))
            
            elif faultModel =="BF":
                
                GAforBF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations, time_limit_seconds = 180.0)
                results.append(GAforBF.run(verbose))
            
            elif faultModel =="MBF":
                
                GAforMBF = GeneticAlgorithm(circuit, faultModel, population_size, max_generations, time_limit_seconds = 180.0)
                results.append(GAforMBF.run(verbose))
    
            
        except Exception as e:
            circuit_name = None
            try:
                circuit_name = circuit.get("Circuit Name") if circuit is not None else None
            except Exception:
                circuit_name = None
            print(f"Error processing circuit {circuit_name}: {e}")
            continue
        # print(results)
        # print("done for circuit this")
    print("\n\nSaving the results\n\n")
    save_results_to_csv(results, output_path)
    print(f"Results saved to {output_path}")
    
    return results
    
# run the code for all the circuits. add the code to record time
# also save the results




if __name__ == "__main__":

    # circuit = parse_real_file(
    #     r"C:\Users\thale\OneDrive\Documents\Avanti\MTech\Dissertation\benchmark circuits\fredkin_6.real")

    

    folder_path = r"C:\Users\thale\OneDrive\Documents\Avanti\MTech\Dissertation\Benchmarks Used in Base Paper\All Circuits"
    output_path= "BF_all.csv"
    faultModel = "BF"
    
    results = run_ga_for_all_files(folder_path, faultModel, output_path=output_path, verbose=False)


    
    # Ga1= GeneticAlgorithm(circuit, "SMGF")
    
    # results = Ga1.run()
    # print(results)
    
    

    