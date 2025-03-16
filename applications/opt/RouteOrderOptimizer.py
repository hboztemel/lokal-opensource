class RouteOrderOptimizer:
    def __init__(self, df, reference_point, n_points):
        self.df = df.copy()
        self.reference_point = reference_point
        self.result_df = pd.DataFrame(columns=df.columns)
        self.n_points = n_points

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        distance = R * c
        return distance

    def calculate_distances(self):
        self.df.loc[:, 'distance'] = self.df.apply(lambda row: self.haversine_distance(
            self.reference_point[0], self.reference_point[1], row['lat'], row['long']
        ), axis=1)
        return self.df

    def divide_by_indicator(self):
        self.df.loc[:, 'adjusted_distance'] = self.df['distance'] / self.df['indicator']
        return self.df

    def select_nearest(self):
        nearest_row = self.df.loc[self.df['adjusted_distance'].idxmin()]

        nearest_row_df = pd.DataFrame([nearest_row]).dropna(how='all')
        if not nearest_row_df.empty:
            self.result_df = pd.concat([self.result_df, nearest_row_df], ignore_index=True)

        self.reference_point = [nearest_row['lat'], nearest_row['long']]
        self.df = self.df[self.df['location_id'] != nearest_row['location_id']].copy()  # Remove selected location
        return nearest_row

    def iterate_selection(self):
        for _ in range(self.n_points):
            self.calculate_distances()
            self.divide_by_indicator()
            self.select_nearest()
        return self.result_df.reset_index(drop=True)


# Application
# if predictions is a DataFrame with recommended place names for the itinerary,

# ...        
        if not predictions.empty:
            optimizer = RouteOrderOptimizer(predictions, reference_point, n_points)
            optimized_route = optimizer.iterate_selection()
            response_data['optimized_route'] = optimized_route.to_dict(orient='records')
# ...

# The column "optimized_route" is the ensured sorted of the list according to the customer inital position.
