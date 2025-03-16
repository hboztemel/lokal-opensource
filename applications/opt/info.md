# RouteOrderOptimizer: In-House Itinerary Optimization (17/03/2025)

## Overview
The `RouteOrderOptimizer` class is designed for **customized touristic itinerary planning**, selecting the most optimal locations based on **proximity and attraction score**. Unlike Google API-based solutions, this in-house approach provides greater flexibility and efficiency without relying on continuous geolocation services.

## Problem & Motivation
- **Efficient Tour Planning:** Ensures travelers visit the most relevant locations in an optimal order.
- **Balancing Distance & Attraction Score:** Prioritizes high-interest locations while minimizing travel effort.
- **Independence from External APIs:** Avoids dependencies on third-party services like Google Maps.

## How It Works
1. **Haversine Distance Calculation** - Computes the great-circle distance between locations.
2. **Weighted Distance Adjustment** - Adjusts the distance based on an **indicator (attraction score)** to prioritize important locations.
3. **Iterative Selection Process** - Picks the best location at each step, updating the reference point for the next selection.
4. **Final Optimized Route** - Returns a list of `n_points` locations in an efficient visiting order.

By integrating both **geographic efficiency and personalized interest scoring**, this approach enhances user experiences by tailoring itineraries to **maximize enjoyment while minimizing travel time**.
