import numpy as np
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from folium.features import DivIcon

from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler
import joblib

import ipywidgets as widgets
from IPython.display import display


class TourRouter:
    locations = {
        "istanbul": (41.0260660, 28.9739962),
        "mugla": (37.0343836, 27.4305260),
        "izmir": (38.4184575, 27.1292222),
        "florence": (43.7694297, 11.2551939),
        "milan": (45.4641652, 9.1918621)
    }

    cluster_map = {
        "city_photography": (4, 3),
        "city_culture": (2, 7),
        "city_history": (5, 2),
        "aesthetic_beauties": (6, 7),
        "family_fun": (4, 0),
        "religious_journeys": (9, 8),
        "modern_view": (4, 0),
        "natural_beauties": (0, 4),
        "city_art": (2, 8),
        "city_romantism": (4, 3),
        "city_fun": (2, 4),
    }

    def __init__(self, model_path=None):
        self.model = self.load_model(model_path) if model_path else None

    @staticmethod
    def load_model(path='model.pkl'):
        return joblib.load(path)

    @staticmethod
    def router(dataset, user_location, n_points, theme_list, city, prior=0.5):
        city = city[0] if isinstance(city, list) else city
        dataset = dataset[dataset['city'] == city].copy()

        if not user_location or user_location == [0, 0]:
            if city and city.lower() in TourRouter.locations:
                user_location = TourRouter.locations[city.lower()]
            else:
                raise ValueError("City must be provided and supported if user_location is not specified.")

        selected_clusters = set()
        for theme in theme_list:
            if theme in TourRouter.cluster_map:
                selected_clusters.update(TourRouter.cluster_map[theme])

        filtered_data = dataset[dataset['cluster'].isin(selected_clusters)].copy()

        if filtered_data.empty:
            raise ValueError("No locations found for selected themes and clusters.")

        coords = filtered_data[['lat', 'long']].values
        knn = NearestNeighbors(n_neighbors=min(n_points * 3, len(filtered_data)))
        knn.fit(coords)

        distances, indices = knn.kneighbors([user_location])
        nearest_locs = filtered_data.iloc[indices[0]].copy()
        nearest_locs['distance'] = distances[0]

        scaler = MinMaxScaler()
        nearest_locs['norm_dist'] = scaler.fit_transform(nearest_locs[['distance']])
        nearest_locs['norm_score'] = scaler.fit_transform(nearest_locs[['score']])

        nearest_locs['ranking_metric'] = prior * nearest_locs['norm_score'] + (1 - prior) * (1 - nearest_locs['norm_dist'])

        top_locs = nearest_locs.sort_values(by='ranking_metric').head(n_points)

        return top_locs.reset_index(drop=True)

    @staticmethod
    def mapper(results, city, user_location):
        if user_location is None or user_location == [0, 0]:
            if city is None or city.lower() not in TourRouter.locations:
                raise ValueError("City must be provided and supported if user_location is not specified.")
            user_location = TourRouter.locations[city.lower()]

        m = folium.Map(location=user_location, zoom_start=12)

        folium.Marker(
            location=user_location,
            popup="Initial",
            icon=folium.Icon(color='green', icon='user')
        ).add_to(m)

        folium.map.Marker(
            user_location,
            icon=DivIcon(
                icon_size=(30, 30),
                icon_anchor=(15, 15),
                html='<div style="font-size: 12pt; color : green"><b>Start</b></div>',
            )
        ).add_to(m)

        for idx, row in results.iterrows():
            location = [row['lat'], row['long']]
            label = f"Destination {idx + 1}"

            folium.Marker(
                location=location,
                popup=f"{label}: {row['location_name']}",
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)

            folium.map.Marker(
                location,
                icon=DivIcon(
                    icon_size=(30, 30),
                    icon_anchor=(15, 15),
                    html=f'<div style="font-size: 12pt; color : black"><b>{idx + 1}</b></div>',
                )
            ).add_to(m)

        return m

    @staticmethod
    def recommender(df, user_location, theme_list=["city_art", "city_culture", "natural_beauties"],
                    n_points=9, city="milan", prior=0.5):
        recommended_route = TourRouter.router(df, user_location, n_points, theme_list, city, prior=prior)
        return TourRouter.mapper(recommended_route, city, user_location)


    def RunFuseModel(url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vS9JLoP3-ZC1znJ5U-wr00-pjbBKvQSLIsNkkEZZ4ad6x0dwQJI3HTspfGqFfSnOJRlx8JsLF1GTmlg/pub?output=csv'):

        df = pd.read_csv(url)

        city_list = widgets.SelectMultiple(
            options=['milan', 'florence', 'istanbul', 'izmir', 'mugla'],
            value=['milan'],
            description='1 - Destination City:',
            # orientation='horizontal',
            style={'description_width': 'initial'},
            layout={'width': '500px'}
        )


        theme_list = widgets.SelectMultiple(
            options=[
                'city_art', 'city_romantism', 'city_fun', 'city_history',
                'modern_view', 'natural_beauties', 'city_photography'
            ],
            value=['city_art'],
            description='2 - Select your Theme(s):',
            style={'description_width': 'initial'},
            layout={'width': '500px'}

        )

        n_points_slider = widgets.IntSlider(
            value=5,
            min=4,
            max=9,
            step=1,
            description='3 - Number of Locations:',
            style={'description_width': 'initial'},
            layout={'width': '500px'}
        )

        prior_slider = widgets.FloatSlider(
            value=0,
            min=0.0,
            max=1.0,
            step=0.20,
            description='4 - Eco-Friendly Tour (%):',
            style={'description_width': 'initial'},
            layout={'width': '500px'}
        )

        lat_input = widgets.FloatText(
            value=0.0,
            description='(Optional) Starting Point Latitude:',
            style={'description_width': 'initial'},
            layout={'width': '500px'}
        )

        lon_input = widgets.FloatText(
            value=0.0,
            description='(Optional) Starting Point Longitude:',
            style={'description_width': 'initial'},
            layout={'width': '500px'}
        )

        run_button = widgets.Button(
            description='CREATE YOUR JOURNEY!',
            button_style='info',  # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Click to run',
            icon='check',  # (FontAwesome icon name)
            layout={'width': '500px'}

        )

        def on_run_clicked(b):
            print("Running your route recommendation...")

            city = list(city_list.value)
            theme = list(theme_list.value)
            n_points = n_points_slider.value
            prior = 1 - prior_slider.value  # Assuming UI slider goes from 0 to 1
            lat = lat_input.value
            lon = lon_input.value

            # Input checks
            if not city:
                print("❗ Please select a city.")
                return
            if not theme:
                print("❗ Please select at least one theme.")
                return

            # Handle missing coordinates
            if lat is None or lon is None:
                user_location = [0, 0]
            else:
                user_location = [lat, lon]

            try:
                map_obj = TourRouter.recommender(
                    df,
                    user_location=user_location,
                    theme_list=theme,
                    n_points=n_points,
                    city=city[0],
                    prior=prior
                )
                display(map_obj)
            except Exception as e:
                print("❌ Failed to run recommendation:", e)


        header = widgets.HTML(
            value="<h2>🗺️ Welcome to the Pilot Fuse Model for Lokal AI!</h2><h4>Author: H. Batuhan Oztemel</h4><p>Please select your preferences below:</p></p>P.S. Multiple choices are welcomed!</p>"
        )

        display(header)
        display(city_list)
        display(theme_list)
        display(n_points_slider, prior_slider)
        display(lat_input, lon_input)
        display(run_button)
        run_button.on_click(on_run_clicked)
