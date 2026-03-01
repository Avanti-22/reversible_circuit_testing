from matplotlib.pylab import size


list1 = [1, 2, 3, 4, 5]
list2 = [2, 4, 6, 8, 10]
list3 = [3, 6, 9, 12, 15]

print(list1)
#  make permutations
maxSetSize = len(list1)


# singleton sets

start =0
start = 0
answer = []
elementCount =0

for setSize in range( maxSetSize):
    # controls the size of each set
    print("\n==Inside the outermost forloop that controls the setsize=======\n\n")

    mset = answer.copy()
    print("Set before adding the elements==>", mset)
    print("Forming sets of size(setSize+1) =>", setSize+1)
    ("\n\n")    
    while elementCount <= setSize:
        # keeps track of which element are we adding in the individual sets        
        print("Adding the", elementCount+1,"/",setSize+1,"th element in each set\n\n")
        
        # # forms different sets in each iteration
        # print("Set size from the previous iteration==>",len(mset))
        
        if not mset:
            print("==First generation for the set======")
            print("==Adding the all the single ton sets")
            ("\n\n")
            for index in range(maxSetSize):
                
                iset = []
                # print("Current Set:", iset)
                if index< maxSetSize:
                    iset.append(list1[index])
                    mset.append(iset)
                    print("Adding element:", list1[index])
            # start +=1    
            
        elif mset:
            print("==Not first generation for the set======")
            print("==Adding the elements to prev itern sets to get new sets===")
            print("\n\n")
            
            for index, subset  in  enumerate(mset) :                
                print("Current Subset:", subset, "size:", len(subset), "index:", index, "maxSetSize:", maxSetSize)
                
                if (len(subset) == setSize):
                    # print("Index:", index)
                    print("==Creating new subset of size",setSize+1,"with current subset====\n\n")
                    
                    nextIndex = subset[-1]-1
                    if(nextIndex+1>=maxSetSize):
                        print("Index out of bound")
                        
                    for i in range(nextIndex+1, maxSetSize):
                        
                        iset = subset.copy()
                        print("Adding element:", list1[i], "to current subset")
                        iset.append(list1[i])
                        print("Resultant subset==>", iset)
                        mset.append(iset)
                        
                    print("Sets formed after this iteration: ",mset,"\n\n")
                    
                    
                else:
                    print("Cannot add to this set, subset size is not required size-1")
                    
            # start +=1    
        print("DOne adding", elementCount+1,"th element to the sets\n\n")
        elementCount+=1
        
        print("Sets formed for currrent set size(", setSize+1,"):", mset)
    print("Done creating sets for setsize==>", setSize+1)
    setSize+=1
    answer = mset.copy()
    # mset.append(list1)
    print("Final set:", mset)   
    

    
    # how to check if a list is empty
    # if not list:
    
    # setsize = 1
    # 1   2   3   4   5      #singleton sets
    # 1 2  1 3  1 4  1 5  2 3  2 4  2 5  3 4  3 5  4 5   # size two sets
    # 1 2 3  1 2 4  1 2 5  1 3 4  1 3 5  1 4 5  2 3 4  2 3 5  2 4 5  3 4 5   # size three sets
    # 1 2 3 4  1 2 3 5  1 2 4 5  1 3 4 5  2 3 4 5   # size four sets
    # 1 2 3 4 5   # size five set
    
    