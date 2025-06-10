# Google Places API Data Acqusition and Cleaning Procedure (10/06/2025)

This procedure outlines the complete workflow for collecting and refining location data using the Google Places API, aiming to produce a balanced and high-quality dataset.

---

## Step 1: Initial Data Collection

The initial dataset is gathered using a NearbySearch query across predefined circular search zones and a list of place types.

---

## Step 2: Initial Data Cleaning

The following operations are performed:

1. **Remove closed places**  
   - Drop any row where `business_status == "TEMPORARILY_CLOSED"`.

2. **Remove missing values**  
   - Drop rows with null or missing values in essential columns: `latitude`, `longitude`, `rating`, `reviews`.

3. **Filter by engagement to maintain high-quality data**  
   - Drop rows where `reviews` < 30.

---

## Step 3: Data Enrichment

Using `maps_id`, this script fetches detailed information via the Place Details API and appends it to the existing data.

---

## Step 4: Advanced Filtering and Scoring

The script performs the following:

4. **Prioritize editorial content**  
   - If `editorial_summary` is present, retain and prioritize this location for scoring.

5. **Compute score and filter by quality**  
   - Compute a custom score (e.g., based on rating, reviews, editorial content, etc.).
   - Remove all locations where `score < 3`.

6. **Filter by relevance**  
   - Remove rows where `"tourist_attraction"` is not in the `types` list.

---

## Step 5: Category-Balanced Selection

Perform the following steps:

1. **Compute type counts**  
   - Let `T_i` be the count of each `primary_type` i.

2. **Compute percentage per type**  
   - `PERCENT_i = T_i / Total_count`

3. **Filter to significant categories**  
   - Keep only types where `T_i > 4`.  
   - Let `SUM5 = sum(T_i)` for the valid types.

4. **Normalize category percentages**  
   - `PERCENT5_i = T_i / SUM5`  
   - Ensure ∑ `PERCENT5_i` = 100%

5. **Allocate slots per type**  
   - `NUMBER_i = min(int(PERCENT5_i * 150), T_i)`  
   - Select top `NUMBER_i` locations by score for each type.

6. **Fill remaining slots (if needed)**  
   - If total selected < 150, fill remaining slots using top leftover locations (regardless of type) by score.

---

## Final Output

A cleaned, scored, and category-balanced list of 150 top POIs per city, suitable for recommendation systems, dashboards, or downstream analysis.

---

## Dependencies

- Python 3.x
- Pandas, NumPy
- Google Places API access
- Bash (for `.sh` scripts)

---
