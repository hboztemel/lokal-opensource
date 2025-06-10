import pandas as pd
import numpy as np

class PDpostprocessor:
    def __init__(self, input_path1, input_path2, output_path, top_n=150, type_col="primary_type", w=[0.2, 0.6, 1.0]):
        self.input_path1 = input_path1
        self.input_path2 = input_path2
        self.output_path = output_path
        self.top_n = top_n
        self.type_col = type_col
        self.w1 = w[0]
        self.w2 = w[1]
        self.w3 = w[2]
        self.df = None # Initialize df as an instance variable

    def compute_score(self, row):
        reviews = row["reviews"] if row["reviews"] >= 0 else 0
        return (
            self.w1 * row["rating"]
            + self.w2 * np.log1p(reviews)
            + self.w3 * (1 if pd.notnull(row.get("editorial_summary", None)) else 0)
        )

    def load_data(self):
        print(f"Loading data from {self.input_path1} and {self.input_path2}...")
        df1 = pd.read_csv(self.input_path1)
        df2 = pd.read_csv(self.input_path2)
        print(f"df1 (np_postprocessed.csv) initial rows: {len(df1)}")
        print(f"df2 (pd_output.csv) initial rows: {len(df2)}")

        # --- MODIFIED PART FOR 'types' COLUMN ---
        if 'types' in df1.columns:
            print("Processing 'types' column in df1...")
            # Convert / separated strings to lists for internal processing
            df1['types'] = df1['types'].apply(
                lambda x: [item.strip() for item in str(x).split('/')] if pd.notnull(x) else []
            )
            print(f"Example of processed 'types' column: {df1['types'].head(1).iloc[0]}")
        else:
            print("WARNING: 'types' column not found in df1.")
        # --- END MODIFIED PART ---

        # --- Handle duplicate 'primary_type' column before merge ---
        if 'primary_type' in df1.columns:
            df1 = df1.rename(columns={'primary_type': 'primary_type_from_np'})
            print("Renamed 'primary_type' in df1 to 'primary_type_from_np' to avoid merge conflict.")

        # Merge and check the result
        self.df = pd.merge(df1, df2, how="inner", on="maps_id")
        print(f"DataFrame after inner merge (self.df): {len(self.df)} rows")
        if self.df.empty:
            print("WARNING: Merged DataFrame is empty. Check 'maps_id' column for common values and data types in both input files.")
            print(f"Unique maps_id in df1: {df1['maps_id'].nunique()}")
            print(f"Unique maps_id in df2: {df2['maps_id'].nunique()}")
        
        if self.type_col not in self.df.columns:
            print(f"ERROR: '{self.type_col}' column not found in the merged DataFrame 'self.df'!")
            print(f"Available columns: {self.df.columns.tolist()}")
            raise KeyError(f"Critical column '{self.type_col}' not found after merge. Check input files and merge logic.")


    def clean_city(self, df_city):
        initial_rows = len(df_city)
        print(f"\n--- Cleaning city group, initial rows: {initial_rows} ---")

        df = df_city.copy()

        df_filtered_status = df[df["business_status"] != "CLOSED"]
        print(f"After business_status != 'CLOSED': {len(df_filtered_status)} rows (removed {len(df) - len(df_filtered_status)})")
        df = df_filtered_status

        df_filtered_dropna = df.dropna(subset=["lat", "long", "rating", "reviews"])
        print(f"After dropna on essential columns: {len(df_filtered_dropna)} rows (removed {len(df) - len(df_filtered_dropna)})")
        df = df_filtered_dropna

        df_filtered_reviews = df[df["reviews"] >= 30]
        print(f"After reviews >= 30: {len(df_filtered_reviews)} rows (removed {len(df) - len(df_filtered_reviews)})")
        df = df_filtered_reviews
        
        if 'types' in df.columns:
             df_filtered_types = df[df['types'].apply(lambda x: "tourist_attraction" in x if isinstance(x, list) else False)]
             print(f"After 'tourist_attraction' type filter: {len(df_filtered_types)} rows (removed {len(df) - len(df_filtered_types)})")
             non_list_types = df[~df['types'].apply(lambda x: isinstance(x, list))]
             if not non_list_types.empty:
                 print(f"WARNING: {len(non_list_types)} rows in 'types' column were not lists after eval. Example: {non_list_types['types'].head(1).iloc[0]}")
             df = df_filtered_types
        else:
            print("WARNING: 'types' column not found in DataFrame. Skipping 'tourist_attraction' filter.")


        if not df.empty:
            df["score"] = df.apply(self.compute_score, axis=1)
            df_filtered_score = df[df["score"] >= 3]
            print(f"After score >= 3: {len(df_filtered_score)} rows (removed {len(df) - len(df_filtered_score)})")
            df = df_filtered_score
        else:
            print("DataFrame is empty before score computation/filtering. Skipping score filtering.")


        print(f"--- Finished cleaning city group, final rows: {len(df)} ---")
        return self.select_balanced_types(df)

    def select_balanced_types(self, df):
        if df.empty:
            print("select_balanced_types: Input DataFrame is empty. Returning empty DataFrame.")
            return pd.DataFrame(columns=df.columns)

        print(f"select_balanced_types: Initial rows: {len(df)}")
        counts = df[self.type_col].value_counts()
        print(f"Value counts for {self.type_col}:\n{counts.head()}")

        valid_types = counts[counts > 4]
        print(f"Types with count > 4: {len(valid_types)} types")

        sum5 = valid_types.sum()
        if sum5 == 0:
            print(f"No valid types found with count > 4. Taking top {self.top_n} by score.")
            return df.sort_values("score", ascending=False).head(self.top_n)

        proportions = valid_types / sum5
        selections = []

        for t, p in proportions.items():
            n = min(int(p * self.top_n), counts[t])
            top_items = df[df[self.type_col] == t].sort_values("score", ascending=False).head(n)
            selections.append(top_items)
        
        if not selections:
            print("No selections made based on type proportions. Taking top N by score.")
            return df.sort_values("score", ascending=False).head(self.top_n)

        result = pd.concat(selections, axis=0)
        print(f"Result after balanced type selection: {len(result)} rows")

        if len(result) < self.top_n:
            remaining = df[~df.index.isin(result.index)]
            fill = remaining.sort_values("score", ascending=False).head(self.top_n - len(result))
            print(f"Filling with {len(fill)} remaining rows to reach {self.top_n}.")
            result = pd.concat([result, fill], axis=0)
        
        print(f"select_balanced_types: Final rows: {len(result)}")
        return result

    def clean_all(self):
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")

        print(f"\nStarting clean_all for {self.df['city'].nunique()} cities...")
        cleaned = []
        if 'city' not in self.df.columns:
            raise ValueError("The input DataFrame must contain a 'city' column for grouping.")

        for city, group in self.df.groupby("city"):
            print(f"Processing city: {city} with {len(group)} rows.")
            city_df = self.clean_city(group)
            if not city_df.empty:
                city_df["city"] = city
                cleaned.append(city_df)
            else:
                print(f"No data remaining for city: {city} after cleaning filters.")
        
        if cleaned:
            self.df = pd.concat(cleaned, axis=0).reset_index(drop=True)
            print(f"Finished clean_all. Total cleaned rows: {len(self.df)}")
        else:
            self.df = pd.DataFrame(columns=self.df.columns)
            print("Finished clean_all. No data remained after processing all cities.")


    def save_balanced_data(self):
        if self.df is None or self.df.empty:
            print(f"No data to save to {self.output_path}.")
            return

        # Define the desired columns in their exact order
        desired_columns = [
            'maps_id', 'location_name', 'rating', 'reviews', 'lat', 'long',
            'primary_type', 'types', 'business_status', 'city', 'country',
            'good_for_groups', 'good_for_children', 'editorial_summary'
        ]

        # Convert the 'types' column from list to '/' separated string BEFORE final selection
        if 'types' in self.df.columns:
            self.df['types'] = self.df['types'].apply(
                lambda x: '/'.join(x) if isinstance(x, list) else (str(x) if pd.notnull(x) else '')
            )
            print("Converted 'types' column back to '/' separated string.")
        else:
            print("WARNING: 'types' column not found before saving. Skipping conversion.")

        # Filter the DataFrame to include only the desired columns
        final_df = self.df.reindex(columns=desired_columns)

        # Optional: Handle potential data type issues if a column was not present and got NaN
        final_df['good_for_groups'] = final_df['good_for_groups'].fillna('').astype(str)
        final_df['good_for_children'] = final_df['good_for_children'].fillna('').astype(str)
        final_df['editorial_summary'] = final_df['editorial_summary'].fillna('')
        # Ensure primary_type is not NaN if it was empty from API
        final_df['primary_type'] = final_df['primary_type'].fillna('')


        final_df.to_csv(self.output_path, index=False)
        print(f"Results saved to: {self.output_path} ({len(final_df)} rows) with desired columns.")


    def run(self):
        self.load_data()
        if not self.df.empty:
            self.clean_all()
        else:
            print("Skipping cleaning and saving as initial merged DataFrame is empty.")
        self.save_balanced_data()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run PDpostprocessor")
    parser.add_argument("--input1", type=str, required=True, help="Input1 CSV path (e.g., np_postprocessed.csv)")
    parser.add_argument("--input2", type=str, required=True, help="Input2 CSV path (e.g., pd_output.csv)")
    parser.add_argument("--output", type=str, required=True, help="Output CSV path")
    parser.add_argument("--top_n", type=int, default=150, help="Top N entries to select per city")
    parser.add_argument("--type_col", type=str, default="primary_type", help="Type column name")
    parser.add_argument("--weights", nargs=3, type=float, default=[0.2, 0.6, 1.0], help="Weights for scoring [rating, reviews, editorial]")

    args = parser.parse_args()
    selector = PDpostprocessor(
        input_path1=args.input1,
        input_path2=args.input2,
        output_path=args.output,
        top_n=args.top_n,
        type_col=args.type_col,
        w=args.weights
    )
    selector.run()
