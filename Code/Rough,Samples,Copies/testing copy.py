# from circuitParsingUtilityFunctions import *

# # # Test with your example
# if __name__ == "__main__":

    
#     # for single file test
    
#     # Parse it
#     circuit = parse_real_file(r"Benchmarks Used in Base Paper\Small\3_17_13.real")
#     print(circuit)
#     # parser = RealFileParser()
#     # internal = parser.to_internal_circuit(circuit)
#     # print("\nInternal Format:")
#     # for gate in internal:
#     #     print(gate)
    
    
    
    
#     # def convert_integer_to_binary(input_vector, maxValue):
#     #     while (input_vector>=1):
#     #         print(input_vector)
#     #         bit = input_vector%2
#     #         binaryVector.append(bit)
#     #         input_vector = input_vector // 2
        
    
#     #     while(len(binaryVector)<maxValue):
#     #         binaryVector.append(0)
            
#     #     binaryVector.reverse()    
        
#     #     return binaryVector
    
    
    
#     # # taking vector input and converting integer to binary
    
#     # maxValue = circuit["No of Lines"]
#     # inputVector= int(input("Enter the integer between 0-"+str(2**maxValue -1)+"for creating binary vector: "))
#     # binaryVector=[]

#     # binaryVector = convert_integer_to_binary(inputVector, maxValue)
#     # print(binaryVector)


#     # # vector processing throught the circuit
#     # gates = circuit["Gates"]
#     # # print("Gates in the circuit are:")
#     # # print(gates)
    
    
#     # # create a circuit with variables replaced with input values
#     # inputVarMap={}
#     # for i in range (len(binaryVector)):
#     #     inputVarMap[circuit["Variables"][i]] = binaryVector[i]

#     # print(inputVarMap)
    

#     # intermediateVector = binaryVector.copy()
    
#     # # replace variables in gates with input values from binary vector
#     # for gate in gates:
#     #     type = gate["gate"]
#     #     variables = gate["vars"]

#     #     for i in range (len(binaryVector)):
#     #         if(variables[i] in inputVarMap):
#     #             intermediateVector[i] = inputVarMap[variables[i]]
            

        
#     #     print("Processing gate:", type, "with variables:", intermediateVector)
        
#     #     if type == "TOFFOLI":
#     #         print("TOFFOLI gate with controls:", variables[:-1], "and target:", variables[-1])
#     #         #target calculation
#     #         if all(v == 1 for v in variables[:-1]):
#     #             intermediateVector[-1] = 1 - variables[-1]
#     #         print("After applying TOFFOLI, target becomes:", intermediateVector[-1])
            
            
#     #     elif type == "FREDKIN":
#     #         print("FREDKIN gate with controls:", variables[:-2], "and swaps:", variables[-2], variables[-1])
#     #         #swap calculation
#     #         if all(v == 1 for v in variables[:-2]):
#     #             intermediateVector[-2], intermediateVector[-1] = intermediateVector[-1], intermediateVector[-2]
#     #         print("After applying FREDKIN, swapped values become:", intermediateVector[-2], intermediateVector[-1])
#     #     elif type == "PERES":
#     #         print("PERES gate with controls:", variables[:-2], "and target:", variables[-2], variables[-1])
#     #         #target calculation
#     #         if all(v == 1 for v in variables[:-2]):
#     #             intermediateVector[-2] = 1 - intermediateVector[-2]
#     #             intermediateVector[-1] = 1 - intermediateVector[-1]
#     #         print("After applying PERES, targets become:", intermediateVector[-2], intermediateVector[-1])
            
#     #     print("Final output vector after processing through the circuit:", intermediateVector)    
    
            
       
     
    
    
    
    
    
    
    
    
#     # for directory test
    
#     # circuits =parse_real_directory(r"Benchmarks Used in Base Paper/All Circuits")

#     # create_circuit_info_sheet(circuits, "allCircuits.csv")
#     # save_to_json(circuits, "allCircuits.json")
    
    
    
    
    
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
            
#             # for all gate parts except the last one
#             # print("gate width: ", len(gateParts))
            
#             # for i in range (len(gateParts)-1):
#                 # print("control bits: ",gateParts[i])
                
#                 # these are the control bits so copy them as it is to the intermediate vector
#                 # i.e., do not change their values

#             # for last gate part i.e target bit
#             # print("target bit: ", gateParts[-1])
#             # controlWidth = len(gateParts)-1
#             # print(controlWidth)
#             # print(gateParts[:-1])
            
            
#             if all(intermediateVector[indexVariableMap[gateParts[c]]] ==1 for c in range(len(gateParts)-1)):
#                 # print("control activates the target bit")
#                 index = indexVariableMap[gateParts[-1]]
#                 intermediateVector[index] = 1- intermediateVector[index]
        
#         count += 1
        
#         # process the vector for toffoli gate at current level    
#         if(type == "FREDKIN"):
#             for i in range (len(gateParts)):
#                 print(gateParts[i])
                
#                 index =inputVarMap[gateParts[i]]
#                 intermediateVector[index] = intermediateVector
#             count += 1
        
#         # # process the vector for toffoli gate at current level    
#         # if(type == "TOFFOLI"):
#         #     for i in range (len(gateParts)):
#         #         print(gateParts[i])
                
#         #         index =inputVarMap[gateParts[i]]
#         #         intermediateVector[index] = intermediateVector
#         #     count += 1
            
            
#         # print("after current gate, the intermediate vector: ",intermediateVector)
#     print("after processing through the circuit, final put vector: ",intermediateVector)
    
    
    
    
   

    # list = [1, 2, 3, 4]
    # list2 = list
    # list3 = list.copy()
    # print(list, list2 , list3)
    # list2.append(5)
    # list3.append(6)
    # print(list, list2 , list3)
    

    # for i, vals in enumerate(list):
    #     print(i, vals)
        
    # for i in range (len(list)):
    #     print(i, list[i])
        
    # for val in list:
    #     print(val)
    

    # tuple1 = (1, 2)
    # print(tuple1[0], tuple1[1])

    
    
# list1 = [1, 2, 3, 4, 5]
# permutations = []
# # permutations:
  
# for i in range(len(list1)):
#     permutations.append([list1[i]])
#     while i < len(list1)-1:
#         permutations[i].append([list1[i]])
#         print(permutations)
#         i += 1
  
  
        
# for maxWidth in range(len(list1)-1):
#     currentWidth =0
        
#     while currentWidth < maxWidth :
#         print("max width: ", maxWidth,"current width: ", currentWidth+1)
#         currentset = []
#         for i in range(len(list1)):
#             currentset.append(list1[i])
#             permutations.append(set(currentset))
#             permutations[i].add(list1[i])
#             print(permutations)
            
#         currentWidth +=1
     
    
    
# nums =set(set())
# nums = {1, 2, 3, 4, 5, 5}
# print(nums)

# # nums.add(nums)

# list = []
# list.append(nums)
# print(list)
# for i in range(len(list)):
#     list[i].add(i+7)
# print(list)

# create permutations of a list
