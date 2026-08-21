# VRP-LNS Framework

**A Python-based routing optimisation framework integrating constructive heuristics, local search, alternative fulfilment structures, Large Neighbourhood Search, and operational timing constraints.**

## Overview

This repository contains a modular routing optimisation framework developed as part of a Master's thesis in Mobility and Supply Chain Engineering at KU Leuven. The framework investigates routing problems involving suppliers, depots, and customers, with particular emphasis on how routing quality and operational feasibility interact as progressively richer operational constraints are introduced.

The computational framework develops from constructive routing and local-search improvement to alternative customer-construction strategies and supplier--customer fulfilment structures. Large Neighbourhood Search (LNS) is subsequently introduced using multiple destroy--repair operator combinations and simulated annealing acceptance to further improve routing quality.

The framework then extends beyond distance-based optimisation by incorporating depot-side operational timing. Supplier arrivals, goods availability, depot dispatch timing, dispatch-wave scheduling, and feasibility-repair procedures are used to evaluate whether distance-efficient routing solutions remain operationally feasible under timing constraints. Sensitivity experiments further examine how changes in operational assumptions affect the resulting feasibility.

Finally, Time-Aware LNS integrates routing optimisation with these operational requirements. Candidate routing improvements are evaluated subject to the relevant timing-feasibility conditions, allowing additional routing improvements to be investigated while preserving the operational feasibility established by the timing framework.

## Framework at a Glance

The project follows a progressive experimental structure:

```text
Constructive Routing
        ↓
Local-Search Improvement
        ↓
Customer Construction and Clustering
        ↓
Alternative Supplier--Customer Fulfilment Structures
        ↓
Large Neighbourhood Search
        ↓
Operational Depot Timing
        ↓
Feasibility Repair
        ↓
Dispatch-Wave Scheduling
        ↓
Operational Sensitivity Analysis
        ↓
Time-Aware Large Neighbourhood Search
```

The resulting framework therefore progresses from routing construction and distance optimisation toward the joint consideration of **routing quality and operational feasibility**.
