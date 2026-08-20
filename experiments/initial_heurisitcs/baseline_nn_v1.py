
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)

from instances.toy_instance_v0 import demand, euc_distance, depot_cord, customer_cord

def run_baseline_nn():

    unserved_customers = [1,2,3,4,5,6,7,8] # “Create a list of unserved customers, initially containing all customers (1 to 8).”
    route = [] # “Create an empty list to store the route taken by the vehicle.”
    # 1️⃣ Initialize state
    #Test nothing breaks.
    while unserved_customers != []:  # “While there are still unserved customers, do the following:”
        current_node = 0
        current_trip = [0] # “Create a list representing the current trip, starting at the depot (node 0).”
        vehicle_capacity = 10
        remaining_capacity = vehicle_capacity #redundant but helps with readability. We can use either of the two variables to keep track of the remaining capacity, but having both can make it clearer when we are updating the capacity after serving a customer.
        served_customers = [] #redundant but helps with readability.   

        #2️⃣ Build feasible list logic
        #Print it once to see if filtering works.

        while True:  # “While there are still unserved customers, do the following:”
            feasible_customers = []
            for customer in unserved_customers:   # “For each customer j in the list of unserved customers, do the following:(if only used the if statement without a loop then only one would be checked and moved ahead which is not what is the goal - and only for loop can work in iterating over all to check which are feasible) ” 
                if demand[customer] <= remaining_capacity:  # “If the demand of customer j is less than or equal to the remaining capacity of the vehicle, add customer j to the list of feasible customers.”
                    feasible_customers.append(customer)

            if feasible_customers == []: # “If the list of feasible customers is empty, break the loop to close the current trip and start a new one.”
                break       

        #3️⃣ Implement “choose nearest”
        #Test only that part.
            distances = {} #Create an empty dictionary to store distances from the current node to each feasible customer.
            for customer in feasible_customers: 
                distances[customer] = euc_distance(current_node, customer)  # “Calculate the distance from the current node to the customer and store it in variable a (d                                                                         ict[key] = value).” 
            nearest_customer = min(distances, key=distances.get)  # “Find the customer with the minimum distance and store it in variable b.”

        #4️⃣ Then add state update.
            current_node = nearest_customer  # “Update the current node to be the nearest customer.”
            remaining_capacity = remaining_capacity - demand[nearest_customer] # nearest_customer is the key in demand dict and we get the demand of that customer and subtract it from the current vehicle capacity to update it.
            #global memory of what is done, Never construct a trip from global history.
            served_customers.append(nearest_customer) # “Add the nearest customer to the list of served customers.”
            unserved_customers.remove(nearest_customer) # “Remove the nearest customer from the list of unserved customers.”

        #5️⃣ Only then add trip closing logic.
            current_trip.append(nearest_customer) # “Add the nearest customer to the current trip. Also local memory of this trip only ” 
        print(served_customers) # “Print the list of served customers to see which customers have been served so far.”
        current_trip.append(0) # “After the while loop ends (when there are no more unserved customers), add the depot (node 0) to the end of the current trip to close it.”
        print(current_trip) # “Print the current trip to see the final route taken by the vehicle.”
        route.append(current_trip) # “Add the current trip to the overall route.”
    print(route) # “After the outer while loop ends (when all customers have been served)"

    if unserved_customers == []: # “Check if the list of unserved customers is empty to verify that all customers have been served.”
        print("All customers have been served.")
    else:
        print("Some customers have not been served: " + str(unserved_customers))


    #Verify structural correctness of routes
    structural_validity = True
    for trip in route:
        if trip[0] == 0 and trip[-1] == 0:
            pass # “Check if the first and last node of the trip is the depot (node 0). If it is, do nothing and continue to the next check.” 
        else:
            structural_validity = False
            #print("Structural error: Trip does not start and end at the depot.") 

        for customer in trip [1:-1]: # "Check each customer in the trip between the first and last depot."
            if customer == 0:
                structural_validity = False
                #print("Structural error: Trip contains depot in between.")
                break
    if structural_validity:
        print("Structural validity check passed.")  #All trips start and end at the depot, and have no customers in between.
    else:
        print("Structural validity check failed, a depot is present in between the trip or the trip does not start and end at the depot.")

    for trip in route:
        trip_capacity = []
        trip_cap = 0
        for customer in trip [1:-1]:
            if demand[customer] <= vehicle_capacity: #validity condition check in CVRP (redundant but helps with readability) - 
                trip_capacity.append(demand[customer])
                trip_cap += demand[customer]
                if trip_cap > vehicle_capacity: #Detect violation (most common in constraints) - after adding the demand of the current customer, check if it exceeds the vehicle capacity. 
                    print("Structural error: Trip exceeds vehicle capacity.")
                    break
            else:
                print("Structural error: Trip exceeds vehicle capacity.")    #also redundant but helps with readability
                break       
    #If I looped through everything and never triggered a break, then execute this block of code. 
    #It is mainly used for:
    #Searching, Validating, Detecting absence of violations" ###
        
        else: # "If the loop completes without breaking, it means all customers in the trip are within the vehicle capacity." 
            print("Trip is within vehicle capacity and trip capacity is:" + str(trip_cap))
    
    print("Unserved customers after route construction:" + str(unserved_customers)) # “Print the list of unserved customers after the route construction to verify that all customers have been served.”

    capacity_feasibility = True
    for trip in route:
        trip_capacity = 0
        for customer in trip [1:-1]:
            trip_capacity += demand[customer] 
            if trip_capacity > vehicle_capacity:
                capacity_feasibility = False
                break
    #if capacity_feasibility:
        #print("All trips are capacity feasible.")       
    #else:
        #print("Some trips are not capacity feasible.")


    #compute total distance of the route

    total_distance = 0
    for trip in route:
        for c in range(len(trip)-1): # “For each trip in the route, do the following: For each pair of consecutive nodes in the trip (from the first node to the second-to-last node), do the following:”
            total_distance += euc_distance(trip[c], trip[c+1]) # “Calculate the distance between each pair of consecutive nodes in the trip and add it to the total distance.”
    print("Total distance of the route: " + str(round(total_distance, 3))) # “Print the total distance of the route to evaluate the solution quality.”

    #number_of_trips = 0                                                              Redundant but helps with readability. 
    #for trip in route:
    #    number_of_trips += 1

    #print("Number of trips in the route: " + str(number_of_trips))     

    number_of_trip = len(route) # “Calculate the number of trips in the route by taking the length of the route list and print it to evaluate the solution quality.”
    print("Number of trips in the route: " + str(number_of_trip))


    print("==================================")
    print("NEAREST NEIGHBOR BASELINE SUMMARY")
    print("==================================")

    print("Capacity feasibility of the route: " + str(capacity_feasibility))
    print("Structural validty of the route: " + str(structural_validity))
    print("All customers served: " + str(unserved_customers == []))
    print("Unsered customers after the route construction: " +str(unserved_customers))
    print("Number of trips : " + str(number_of_trip))
    print("Total Travel Distance: " + str(round(total_distance, 3)))

    print("==================================")
    return route, total_distance, number_of_trip

if __name__ == "__main__":
    run_baseline_nn()
