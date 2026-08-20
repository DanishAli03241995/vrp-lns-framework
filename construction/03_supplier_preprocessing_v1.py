"""Supplier-side preprocessing helpers."""


def supplier_depot_echelon(demand, supplier_supply):
    """Check whether total supplier supply can cover total customer demand."""
    total_demand = sum(
        customer_demand
        for customer_id, customer_demand in demand.items()
        if customer_id != 0
    )
    total_supply = sum(supplier_supply.values())
    supply_feasibility = total_supply >= total_demand

    return supply_feasibility, total_demand, total_supply
