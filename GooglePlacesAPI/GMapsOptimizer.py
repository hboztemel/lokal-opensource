import folium
import math
import pandas as pd
from shapely.geometry import Polygon, Point


class GMapsOptimizer:
    def __init__(self, corner_sets, radius, spacing_factor):
        """
        Initializes the GMapsOptimizer with one or more rectangular areas.

        Args:
            corner_sets (list of lists of tuples): A list where each inner list
                                                   represents the (lat, lon) corners
                                                   of a rectangular area.
                                                   Example: [[(lat1, lon1), ...], [(lat_a, lon_a), ...]]
            radius (float): Radius of the circles in meters.
            spacing_factor (float): A factor between 0 and 1 that adjusts the distance
                                    between circle centers.
                                    0 = maximum overlap (centers are radius distance apart)
                                    1 = minimum overlap (centers are 2*radius distance apart, i.e., touching)
        """
        self.corner_sets = corner_sets
        self.radius = radius
        self.spacing_factor = spacing_factor
        self.earth_radius = 6371000  # Approximate Radius of Earth in meters

        self.circle_centers = []
        # Added 'area_id' column to distinguish circles originating from different input areas
        self.boundary_dataframe = pd.DataFrame(columns=["lat", "lon", "radius", "area_id"])

        # Pre-process polygons for efficient point-in-polygon checks
        self.polygons = [Polygon(cs) for cs in self.corner_sets]

    def _distance(self, lat1, lon1, lat2, lon2):
        """
        Calculates the Haversine distance between two latitude/longitude points on Earth's surface.

        Args:
            lat1, lon1 (float): Latitude and longitude of the first point.
            lat2, lon2 (float): Latitude and longitude of the second point.

        Returns:
            float: The distance in meters.
        """
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return self.earth_radius * c

    def _point_in_any_rectangle(self, point_coords):
        """
        Checks if a given (latitude, longitude) point is inside any of the defined rectangular areas.

        Args:
            point_coords (tuple): A tuple (latitude, longitude) representing the point.

        Returns:
            bool: True if the point is within any of the polygons, False otherwise.
        """
        point_shapely = Point(point_coords)
        for poly in self.polygons:
            if poly.contains(point_shapely):
                return True
        return False

    def generate_circle_centers(self):
        """
        Generates circle centers to cover all defined rectangular areas.
        It sweeps a grid over the combined bounding box of all areas and
        adds a circle center if the grid point falls within any of the areas.
        """
        all_lats = [lat for cs in self.corner_sets for lat, lon in cs]
        all_lons = [lon for cs in self.corner_sets for lat, lon in cs]

        if not all_lats or not all_lons:
            print("No corner sets provided. Cannot generate circles.")
            return

        # Determine the overall bounding box for all areas
        min_lat = min(all_lats)
        max_lat = max(all_lats)
        min_lon = min(all_lons)
        max_lon = max(all_lons)

        # Calculate steps for latitude and longitude based on radius and spacing factor
        # This converts meters to degrees latitude and longitude
        lat_step = self.radius / self.earth_radius * (180 / math.pi)
        # Longitude step needs to account for the convergence of meridians (cosine of latitude)
        # Using min_lat for a slightly safer (smaller) step
        lon_step = self.radius / (self.earth_radius * math.cos(math.radians(max(abs(min_lat), abs(max_lat))))) * (
                    180 / math.pi)

        # Adjust step based on spacing factor for desired overlap/coverage
        # (1 + spacing_factor) makes steps larger, leading to less overlap.
        # If spacing_factor is 0, step is 'radius' equivalent in degrees (max overlap)
        # If spacing_factor is 1, step is '2*radius' equivalent in degrees (circles just touching)
        lat_step *= (1 + self.spacing_factor)
        lon_step *= (1 + self.spacing_factor)

        # Iterate over the grid covering the entire bounding box
        lat = min_lat
        while lat <= max_lat:
            lon = min_lon
            while lon <= max_lon:
                # Check if the current grid point is inside any of the input polygons
                if self._point_in_any_rectangle((lat, lon)):
                    self.circle_centers.append((lat, lon))

                    # Determine which area this circle belongs to (for 'area_id' in DataFrame)
                    area_found = -1
                    for i, poly in enumerate(self.polygons):
                        if poly.contains(Point(lat, lon)):
                            area_found = i + 1  # Assign area_id starting from 1
                            break

                    # Use pd.concat for appending row to DataFrame
                    self.boundary_dataframe = pd.concat([
                        self.boundary_dataframe,
                        pd.DataFrame([{"lat": lat, "lon": lon, "radius": self.radius, "area_id": area_found}])
                    ], ignore_index=True)
                lon += lon_step
            lat += lat_step
        print(f"Generated {len(self.circle_centers)} circle centers.")

    def plot_map(self):
        """
        Plots a Folium map with all defined rectangular areas and the generated circles.
        Each area polygon will have a different color.
        """
        all_lats = [lat for cs in self.corner_sets for lat, lon in cs]
        all_lons = [lon for cs in self.corner_sets for lat, lon in cs]

        if not all_lats or not all_lons:
            print("No corners provided for map plotting.")
            return None

        # Center the map on the overall average of all corners
        avg_lat = sum(all_lats) / len(all_lats)
        avg_lon = sum(all_lons) / len(all_lons)

        # Initialize map with an appropriate zoom level
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)

        # Define a list of colors for the different polygons
        polygon_colors = ["blue", "green", "purple", "orange", "darkred", "cadetblue", "darkgreen", "darkblue"]

        # Add each rectangular area to the map
        for i, corners_list in enumerate(self.corner_sets):
            folium.Polygon(
                locations=corners_list,
                color=polygon_colors[i % len(polygon_colors)],  # Cycle through predefined colors
                weight=2,
                fill=True,
                fill_opacity=0.2,  # Make polygon fills slightly transparent
                tooltip=f"Area {i + 1}"  # Add a tooltip for each area
            ).add_to(m)

        # Add all generated circles to the map
        for lat, lon in self.circle_centers:
            folium.Circle(
                location=(lat, lon),
                radius=self.radius,
                color="red",  # Color of the circle outline
                fill=True,
                fill_opacity=0.4,  # Transparency of the circle fill
                popup=f"Latitude: {lat}, Longitude: {lon}"  # Pop-up on click
            ).add_to(m)

        return m

if __name__ == "__main__":
    print("Starting GMapsOptimizer demonstration...")

    # Define multiple sets of corners for different geographical areas
    corners1 = [(41.90665632093537, 12.444106035745042),
                    (41.920986165507635, 12.485878723385273),
                    (41.88566966505911, 12.507843030961459),
                    (41.87445022399441, 12.479931279143306)]

    corners2 = [(45.451999, 9.177265),
                     (45.470536, 9.190695),
                     (45.460010, 9.215280),
                     (45.441473, 9.201849)]

    # Example 3: A small area in Paris, France
    corners3 = [(48.8500, 2.2900),
                     (48.8600, 2.3000),
                     (48.8550, 2.3100),
                     (48.8450, 2.3050)]

    # Combine all corner sets into a single list
    all_areas_to_cover = [corners1, corners2, corners3]

    # Define parameters for the circles
    search_radius_meters = 500  # Radius of each circle in meters
    coverage_spacing_factor = 0.5  # Adjusts overlap: 0 for max overlap, 1 for circles just touching

    # Create an instance of GMapsOptimizer with all defined areas and parameters
    circle_coverage_instance = GMapsOptimizer(
        all_areas_to_cover,
        search_radius_meters,
        coverage_spacing_factor
    )

    circle_coverage_instance.generate_circle_centers()

    print("\nDataFrame of all generated circle centers (first 5 rows):")
    print(circle_coverage_instance.boundary_dataframe.head())
    print(f"Total number of circle centers generated: {len(circle_coverage_instance.boundary_dataframe)}")

    output_csv_path = 'all_circle_centers_data.csv'
    circle_coverage_instance.boundary_dataframe.to_csv(output_csv_path, index=False)
    print(f"Circle centers data saved to '{output_csv_path}'.")

    map_output = circle_coverage_instance.plot_map()

    if map_output:
        output_html_path = 'map_with_multiple_areas_coverage.html'
        map_output.save(output_html_path)
        print(f"Interactive map saved to '{output_html_path}'.")
    else:
        print("\nMap could not be generated as no valid corners were provided.")

    print("\nDemonstration complete.")
