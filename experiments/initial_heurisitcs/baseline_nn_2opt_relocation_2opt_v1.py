import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(PROJECT_ROOT)

from instances import toy_instance_v1_40c as instance

demand = instance.demand
euc_distance = instance.euc_distance
depot_cord = instance.depot_cord
customer_cord = instance.customer_cord
average_speed = instance.average_speed
service_time = instance.service_time
INSTANCE_NAME = instance.__name__.split(".")[-1]


def run_baseline_nn():
    unserved_customers = []
    for customer in customer_cord:
        unserved_customers.append(customer) # “Create a list of unserved customers, initially containing all customers (1 to 8).”

    #print(unserved_customers) # “Create a list of unserved customers, initially containing all customers (1 to 8).”
    route = [] # “Create an empty list to store the route taken by the vehicle.”
    # 1️⃣ Initialize state
    #Test nothing breaks.
    while unserved_customers != []:  # “While there are still unserved customers, do the following:”
        current_node = 0
        current_trip = [0] # “Create a list representing the current trip, starting at the depot (node 0).”
        vehicle_capacity = 25
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
    print(f"Total distance of the route: {total_distance:.3f}") # “Print the total distance of the route to evaluate the solution quality.”

    #number_of_trips = 0                                                              Redundant but helps with readability. 
    #for trip in route:
    #    number_of_trips += 1

    #print("Number of trips in the route: " + str(number_of_trips))     
    number_of_trip = len(route) # “Calculate the number of trips in the route by taking the length of the route list and print it to evaluate the solution quality.”
    print("Number of trips in the route: " + str(number_of_trip))



    total_travel_time = 0
    for trip in route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])
        print(f"Trip distance: {trip_distance:.3f}")
        trip_time = trip_distance / average_speed  # Use average speed from instance

        for customer in trip[1:-1]:  # Add service time for each customer in the trip (excluding the depot)
            trip_time += service_time[customer]/60  # Convert service time from minutes to hours
        print(f"Trip duration (travel + service time): {trip_time:.3f} hours") # “Calculate the travel time of each trip by dividing the trip distance by the average speed and print it to evaluate the solution quality.”
        total_travel_time += trip_time
    #print("Total travel time of the route: " + str(round(total_travel_time, 3)) + " hours") # “Calculate the total travel time of the route by summing the travel time of each trip (distance divided by average speed) and print it to evaluate the solution quality.” 

    print("==================================")
    print("NEAREST NEIGHBOR BASELINE SUMMARY")
    print("==================================")

    print("Capacity feasibility of the route: " + str(capacity_feasibility))
    print("Structural validty of the route: " + str(structural_validity))
    print("All customers served: " + str(unserved_customers == []))
    print("Unsered customers after the route construction: " +str(unserved_customers))
    print("Number of trips : " + str(number_of_trip))
    print("Total Travel Distance: " + str(round(total_distance, 3)) + " km")
    print("Total Travel Time: " + str(round(total_travel_time, 3)) + " hours")
    print("==================================")
    
    new_route = run_2opt(route)
    
    
    #distance 
    total_distance_route = 0
    total_travel_time_after_2opt = 0 
    for trip in new_route:
        distance = 0 
        
        for c in range(len(trip)-1):
            distance += euc_distance(trip[c],trip[c+1])

        print("Trip distance : " + str(round(distance, 3)) + " km" )
        
        trip_time = distance/average_speed
        
        for customer in trip[1:-1]:
            trip_time += service_time[customer]/60 
        print("Trip duration (travel + service time): " + str(round(trip_time, 3)) + " hours") # “Calculate the travel time of each trip by dividing the trip distance by the average speed and print it to evaluate the solution quality.”
        total_travel_time_after_2opt += trip_time

        total_distance_route += distance 
    print("Total distance of the route: " + str(round(total_distance_route, 3)))
    print("Total travel time of the route: " + str(round(total_travel_time_after_2opt, 3)) + " hours") 
    print("==================================")             
    
    return(
        route, 
        total_distance,
        number_of_trip,
        new_route,
        total_distance_route,
        total_travel_time,
        total_travel_time_after_2opt,
        capacity_feasibility,
        structural_validity,
        vehicle_capacity,
        unserved_customers,
    )

def run_2opt(route):
    #2-opt Implementation Steps

    new_route = [] 
    #1️⃣ trip selection
    for trip in route:
        print("\n==============================")
        print("NEW TRIP START")
        print("==============================")    
    #2️⃣ Initialize tracking variables
        print(trip)
        current_trip = trip
        
        
        #Outer Loop                          1. j loop, all j for one i   2. the i loop, another i and all possible j(s)
        while True:                   #if improvement - then 3. while loop starts with the improved trip     4. same i,j loops which same logics run again till no improvement is left  
            improved = False          #5. only after this is done is when 1 trip's potential modifications are done and then the start for loop picks the next trip 
                                      #6. and we have an empty new_route outside the 1st for loop to later appnd updated trips to it - so actual route is not overwritten   
            best_trip = current_trip

            trip_distance = 0
            for c in range(len(current_trip)-1):
                trip_distance += euc_distance(current_trip[c],current_trip[c+1])
            print(f"Trip distance: {trip_distance:.6f}")
            print("------------------------------")
            best_distance = trip_distance


            for i in range(len(current_trip)-3):
                for j in range(i+2,len(current_trip)-1):

                    print("\n(i, j) combination:", i, j)
                    #candidate generaton 

                    part_1 = current_trip[:i+1]                           #changing trip to current_trip
                    part_2 = current_trip[i+1:j+1]
                    part_3 = current_trip[j+1:]

                    print(part_1, part_2, part_3)

            #part between i+1 and j reversed 
                    reverse_part_2 = part_2[::-1]
            #new trip 
                    #connect trip[i] with trip[j]
                    #connect trip[i+1] with trip[j+1]
                    new_trip = part_1 + reverse_part_2 + part_3
                    print(new_trip)
        #2️⃣ Initialize tracking variables
                    new_trip_distance = 0
                    for c in range(len(new_trip)-1):
                        new_trip_distance += euc_distance(new_trip[c],new_trip[c+1])
                    print(f"New Trip Distance: {new_trip_distance:.6f}")
                    print("-----------")
                    if new_trip_distance < best_distance:
                        improved = True                    #critical condition - linked with the improved at the top 
                        print("Improvement found:")
                        print(f"Old distance: {best_distance:.6f}")
                        best_distance = new_trip_distance
                        print(f"New distance: {new_trip_distance:.6f}")
                        best_trip = new_trip
                        print("New best trip:", new_trip)
                        print("-----------")

                    elif new_trip_distance == best_distance:
                        pass

            if not improved:
                break

            # 🔥 PLACE IT EXACTLY HERE (same indent as 'for i')
            current_trip = best_trip   
            
           

            print("Best trip after this pass:", best_trip)
            print(f"Best distance after this pass: {best_distance:.6f}")
            print("\n====== END OF PASS ======\n")
 
        new_route.append(current_trip)
    print("New Route is :" + str(new_route))

    return new_route

def total_solution_distance(new_route):
    total = 0
    for trip in new_route:
        for i in range(len(trip)-1):
            total += euc_distance(trip[i], trip[i+1])
    return total

def run_relocation(new_route):
#1-0 relocate implementation steps
    improvement = True
    iteration = 0
    while improvement:
        iteration += 1
        improvement = False
        best_delta = float("inf")
        best_move = None

        for original_trip in new_route:
            #print(original_trip)
            
            #One customer from the trip removal phase 
            for i in original_trip[1:-1]: #excluding the depot at the start and end of the trip
                candidate_trip = []
                removed_customer = [i]
                for j in original_trip:
                    if j == i:
                        #print("Customer removed for relocation:", i)
                        continue
                    else:
                        candidate_trip.append(j)
                #print(candidate_trip)

                # original_trip distance BEFORE removal
                original_trip_distance = 0
                for x in range(len(original_trip)-1):
                    original_trip_distance += euc_distance(original_trip[x], original_trip[x+1])
                #insertion of the removed customer in all possible positions in the trip    
                for new_trip in new_route:
                    if new_trip == original_trip:
                        #print(new_trip)
                        #print("Same trip, skipping insertion phase for this trip.")
                        continue
                    else:
                        #print("Inserting customer:", removed_customer[0])
        #time 
                        for k in range(1, len(new_trip)): #inserting the removed customer in all possible positions in the trip except the depot at the start (index 0)
                            candidate_trip_2 = []
                            part_1 = new_trip[:k]
                            part_2 = new_trip[k:]
                            candidate_trip_2 = part_1 + removed_customer + part_2
                            #print(candidate_trip_2)

                            trip_demand = 0
                            for c in range(1,len(candidate_trip_2)-1): #check if the candidate trip is within vehicle capacity - if not then skip to the next insertion position or next trip for insertion.
                                trip_demand += demand[candidate_trip_2[c]] 
                                if trip_demand > vehicle_capacity:
                                    #print("Capacity violation detected, skipping this candidate trip.")
                                    break
                            else: #if no break was triggered, then we can evaluate the trip distance and travel
                                # NEW inserted trip distance
                                inserted_trip_distance = 0
                                for x in range(len(candidate_trip_2)-1):
                                    inserted_trip_distance += euc_distance(candidate_trip_2[x], candidate_trip_2[x+1])

                                # NEW removed trip distance (after removal)
                                removed_trip_distance = 0
                                for x in range(len(candidate_trip)-1):
                                    removed_trip_distance += euc_distance(candidate_trip[x], candidate_trip[x+1])

                                # OLD target trip distance (before insertion)
                                target_trip_distance = 0
                                for x in range(len(new_trip)-1):
                                    target_trip_distance += euc_distance(new_trip[x], new_trip[x+1])

                                # OLD vs NEW
                                old_cost = original_trip_distance + target_trip_distance
                                new_cost = removed_trip_distance + inserted_trip_distance

                                # DELTA
                                delta = new_cost - old_cost

                                # BEST MOVE UPDATE
                                if delta < best_delta:
                                    best_delta = delta
                                    best_move = {
                                        "removed_customer": removed_customer[0],
                                        "from_trip": original_trip,
                                        "to_trip": new_trip,
                                        "new_trip_after_removal": candidate_trip,
                                        "new_trip_after_insertion": candidate_trip_2,
        
                                    }
                                    

        #print("Best delta:", best_delta)
        #print("Best move:", best_move)

        print(f"\nIteration {iteration}")
        print(f"Best delta: {best_delta}") 
        print(f"Total distance: {total_solution_distance(new_route)}")         

        if best_move is not None and best_delta < 0:
            # remove old trips
            from_idx = new_route.index(best_move["from_trip"])
            to_idx = new_route.index(best_move["to_trip"])

            # add updated trips
            new_route[from_idx] = best_move["new_trip_after_removal"]
            new_route[to_idx] = best_move["new_trip_after_insertion"]
            improvement = True

            # 👉 DEBUG PRINT (PLACE HERE)
            print(f"Number of trips: {len(new_route)}")
            #print("Updated routes:")
            #for r in new_route:
            #   print(r)

            # =========================
            # ✅ CHECK 1 + CHECK 2 HERE
            # =========================
            # CHECK 1 — all customers served exactly once
            #Checking the served customers 
            served = []

            for trip in new_route: 
                for node in trip:
                    if node != 0:
                        served.append(node)
            #Detecting Duplication 
            unique_served = set(served)
            if len(served) == len(unique_served):
                print("All customers unique")
            else:
                print("Duplication exists")

            #Check 2 - Capacity feasibiltiy 
            for trip in new_route:
                load = 0 

                for node in trip: 
                    load += demand[node]

                if load > vehicle_capacity:
                    print("Capacity violation detected in trip:", trip)       


    print("\nOptimization finished")
    print(f"Final total distance: {total_solution_distance(new_route)}")

    return new_route

if __name__ == "__main__":
    from utils.experiment_logger import create_experiment_folder
    from utils.plot_routes import plot_routes
    import json

    results_path = create_experiment_folder("baseline_nn_2opt_1_0_relocate", INSTANCE_NAME)

    (
        route,
        total_distance,
        number_of_trip,
        new_route,
        total_distance_route,
        total_travel_time,
        total_travel_time_after_2opt,
        capacity_feasibility,
        structural_validity,
        vehicle_capacity,
        unserved_customers,
    ) = run_baseline_nn()

    baseline_route = route
    two_opt_route = [trip.copy() for trip in new_route]
    
    # 🔁 Apply 1-0 relocation improvement
    relocation_route = run_relocation(two_opt_route)

    # 🔁 Apply 2-opt again after relocation
    post_reloc_2opt_route = run_2opt([trip.copy() for trip in relocation_route])
    
    # 🔁 recompute FINAL distance after relocation
    relocation_total_distance = total_solution_distance(relocation_route)
    post_reloc_2opt_distance = total_solution_distance(post_reloc_2opt_route)

    relocation_travel_time = 0
    for trip in relocation_route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])

        trip_time = trip_distance / average_speed
        for customer in trip[1:-1]:
            trip_time += service_time[customer] / 60

        relocation_travel_time += trip_time

    post_reloc_2opt_travel_time = 0
    for trip in post_reloc_2opt_route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])

        trip_time = trip_distance / average_speed
        for customer in trip[1:-1]:
            trip_time += service_time[customer] / 60

        post_reloc_2opt_travel_time += trip_time
    
    # compute trip distances for all three stages
    baseline_trip_distances = []
    for trip in baseline_route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])
        baseline_trip_distances.append(trip_distance)

    two_opt_trip_distances = []
    for trip in two_opt_route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])
        two_opt_trip_distances.append(trip_distance)

    relocation_trip_distances = []
    for trip in relocation_route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])
        relocation_trip_distances.append(trip_distance)

    post_reloc_2opt_trip_distances = []
    for trip in post_reloc_2opt_route:
        trip_distance = 0
        for c in range(len(trip)-1):
            trip_distance += euc_distance(trip[c], trip[c+1])
        post_reloc_2opt_trip_distances.append(trip_distance)
    
    # demand load for all three stages
    baseline_trip_loads = []
    for trip in baseline_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        baseline_trip_loads.append(trip_load)

    two_opt_trip_loads = []
    for trip in two_opt_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        two_opt_trip_loads.append(trip_load)

    relocation_trip_loads = []
    for trip in relocation_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        relocation_trip_loads.append(trip_load)

    post_reloc_2opt_trip_loads = []
    for trip in post_reloc_2opt_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        post_reloc_2opt_trip_loads.append(trip_load)

    # customers per trip for all three stages
    customers_per_trip_baseline = []
    for trip in baseline_route:
        customers_per_trip_baseline.append(len(trip)-2) #subtracting 2 to exclude the depot at the start and end of the trip

    customers_per_trip_2opt = []
    for trip in two_opt_route:
        customers_per_trip_2opt.append(len(trip)-2) #subtracting 2 to exclude the depot at the start and end of the trip

    customers_per_trip_relocation = []
    for trip in relocation_route:
        customers_per_trip_relocation.append(len(trip)-2) #subtracting 2 to exclude the depot at the start and end of the trip

    customers_per_trip_post_reloc_2opt = []
    for trip in post_reloc_2opt_route:
        customers_per_trip_post_reloc_2opt.append(len(trip)-2) #subtracting 2 to exclude the depot at the start and end of the trip

    # trip utilization rate for all three stages
    baseline_trip_utilization = []
    for trip in baseline_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        utilization = trip_load / vehicle_capacity
        baseline_trip_utilization.append(utilization)

    two_opt_trip_utilization = []
    for trip in two_opt_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        utilization = trip_load / vehicle_capacity
        two_opt_trip_utilization.append(utilization)

    relocation_trip_utilization = []
    for trip in relocation_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        utilization = trip_load / vehicle_capacity
        relocation_trip_utilization.append(utilization)

    post_reloc_2opt_trip_utilization = []
    for trip in post_reloc_2opt_route:
        trip_load = 0
        for customer in trip[1:-1]:
            trip_load += demand[customer]
        utilization = trip_load / vehicle_capacity
        post_reloc_2opt_trip_utilization.append(utilization)

    # average trip utilization for all three stages
    baseline_avg_utilization = sum(baseline_trip_utilization) / len(baseline_trip_utilization)
    two_opt_avg_utilization = sum(two_opt_trip_utilization) / len(two_opt_trip_utilization)
    relocation_avg_utilization = sum(relocation_trip_utilization) / len(relocation_trip_utilization)
    post_reloc_2opt_avg_utilization = sum(post_reloc_2opt_trip_utilization) / len(post_reloc_2opt_trip_utilization)

    # max trip utilization for all three stages
    baseline_max_utilization = max(baseline_trip_utilization)
    two_opt_max_utilization = max(two_opt_trip_utilization)
    relocation_max_utilization = max(relocation_trip_utilization)
    post_reloc_2opt_max_utilization = max(post_reloc_2opt_trip_utilization)

    # min trip utilization for all three stages
    baseline_min_utilization = min(baseline_trip_utilization)
    two_opt_min_utilization = min(two_opt_trip_utilization)
    relocation_min_utilization = min(relocation_trip_utilization)
    post_reloc_2opt_min_utilization = min(post_reloc_2opt_trip_utilization)


    metrics = {
        "algorithm": "baseline_nn_2opt_relocation_2opt",
        "instance": INSTANCE_NAME,
        "seed": 42,
        "construction": "nearest_neighbor",
        "local_search": "2-opt + relocation + 2-opt",
        "baseline_distance": total_distance,
        "two_opt_distance": total_distance_route,
        "relocation_distance": relocation_total_distance,
        "post_reloc_2opt_distance": post_reloc_2opt_distance,
        "two_opt_gain_over_baseline": total_distance - total_distance_route,
        "two_opt_percent_gain_over_baseline": ((total_distance - total_distance_route) / total_distance) * 100,
        "relocation_gain_over_2opt": total_distance_route - relocation_total_distance,
        "relocation_percent_gain_over_2opt": ((total_distance_route - relocation_total_distance) / total_distance_route) * 100,
        "relocation_gain_over_baseline": total_distance - relocation_total_distance,
        "relocation_percent_gain_over_baseline": ((total_distance - relocation_total_distance) / total_distance) * 100,
        "post_reloc_2opt_gain_over_relocation": relocation_total_distance - post_reloc_2opt_distance,
        "post_reloc_2opt_percent_gain_over_relocation": ((relocation_total_distance - post_reloc_2opt_distance) / relocation_total_distance) * 100,
        "baseline_travel_time": total_travel_time,
        "two_opt_travel_time": total_travel_time_after_2opt,
        "relocation_travel_time": relocation_travel_time,
        "post_reloc_2opt_travel_time": post_reloc_2opt_travel_time,
        "trips": number_of_trip,
        "absolute_improvement": total_distance - post_reloc_2opt_distance,
        "percent_improvement": ((total_distance - post_reloc_2opt_distance) / total_distance) * 100,
        "final_absolute_improvement": total_distance - post_reloc_2opt_distance,
        "final_percent_improvement": ((total_distance - post_reloc_2opt_distance) / total_distance) * 100,
        "capacity_feasibility": capacity_feasibility,
        "structural_validity": structural_validity,
        "all_customers_served": unserved_customers == [],
        "vehicle_capacity": vehicle_capacity,
        "unserved_customers": unserved_customers,
        "n_customers": len(customer_cord),
        "depot": depot_cord,
        "baseline_trip_distances": baseline_trip_distances,
        "two_opt_trip_distances": two_opt_trip_distances,
        "relocation_trip_distances": relocation_trip_distances,
        "post_reloc_2opt_trip_distances": post_reloc_2opt_trip_distances,
        "baseline_trip_loads": baseline_trip_loads,
        "two_opt_trip_loads": two_opt_trip_loads,
        "relocation_trip_loads": relocation_trip_loads,
        "post_reloc_2opt_trip_loads": post_reloc_2opt_trip_loads,
        "customers_per_trip_baseline": customers_per_trip_baseline,
        "customers_per_trip_2opt": customers_per_trip_2opt,
        "customers_per_trip_relocation": customers_per_trip_relocation,
        "customers_per_trip_post_reloc_2opt": customers_per_trip_post_reloc_2opt,
        "baseline_trip_utilization": baseline_trip_utilization,
        "two_opt_trip_utilization": two_opt_trip_utilization,
        "relocation_trip_utilization": relocation_trip_utilization,
        "post_reloc_2opt_trip_utilization": post_reloc_2opt_trip_utilization,
        "baseline_avg_utilization": baseline_avg_utilization,
        "two_opt_avg_utilization": two_opt_avg_utilization,
        "relocation_avg_utilization": relocation_avg_utilization,
        "post_reloc_2opt_avg_utilization": post_reloc_2opt_avg_utilization,
        "baseline_max_utilization": baseline_max_utilization,
        "two_opt_max_utilization": two_opt_max_utilization,
        "relocation_max_utilization": relocation_max_utilization,
        "post_reloc_2opt_max_utilization": post_reloc_2opt_max_utilization,
        "baseline_min_utilization": baseline_min_utilization,
        "two_opt_min_utilization": two_opt_min_utilization,
        "relocation_min_utilization": relocation_min_utilization,
        "post_reloc_2opt_min_utilization": post_reloc_2opt_min_utilization,
    }

    with open(f"{results_path}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)

    with open(f"{results_path}/route_baseline.txt", "w") as f:
        f.write(str(baseline_route))    

    with open(f"{results_path}/route_2opt.txt", "w") as f:
        f.write(str(two_opt_route))

    with open(f"{results_path}/route_relocation.txt", "w") as f:
        f.write(str(relocation_route))

    with open(f"{results_path}/route_post_reloc_2opt.txt", "w") as f:
        f.write(str(post_reloc_2opt_route))

    plot_routes(
        baseline_route,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_baseline_nn.png",
        title="Vehicle Routes - Baseline NN",
    )
    plot_routes(
        two_opt_route,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_2opt.png",
        title="Vehicle Routes - 2-Opt",
    )
    plot_routes(
        relocation_route,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_relocation.png",
        title="Vehicle Routes - Relocation",
    )
    plot_routes(
        post_reloc_2opt_route,
        depot_cord,
        customer_cord,
        results_path,
        filename="route_plot_post_reloc_2opt.png",
        title="Vehicle Routes - Post Relocation 2-Opt",
    )

    print("Results stored in:", results_path)
