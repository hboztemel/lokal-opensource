from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer, util
from sklearn.preprocessing import MinMaxScaler
from geopy.distance import geodesic
from functools import lru_cache

app = FastAPI()
# model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") #Heavier model
# model = SentenceTransformer("sentence-transformers/paraphrase-MiniLM-L6-v2") #Lighter model

# metadata = pd.read_csv("metadata.csv")
# embeddings = np.load("embeddings5_2.npy")

# Lazy loading with cache
@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") #Heavier model
    # return SentenceTransformer("sentence-transformers/paraphrase-MiniLM-L6-v2") #Lighter model

@lru_cache(maxsize=1)
def load_metadata():
    return pd.read_csv("metadata.csv")

@lru_cache(maxsize=1)
def load_embeddings():
    return np.load("embeddings5.npy") #Heavier model
    # return np.load("embeddings1.npy") #Lighter model

class RecommendationRequest(BaseModel):
    query: str
    city: str
    user_lat: Optional[float] = None
    user_long: Optional[float] = None
    top_n: int = 5
    similarity_coef: float = 10.0
    rating_coef: float = 2.0
    review_coef: float = 4.0
    proximity_coef: float = 1.5

@app.post("/recommend")
def recommend(req: RecommendationRequest):

    model = get_model()
    metadata = load_metadata()
    embeddings = load_embeddings()

    city_df = metadata[
        (metadata["city"] == req.city) &
        (metadata["primary_type"].notna()) &
        (metadata["primary_type"] != "")
    ].reset_index(drop=True)

    city_embeddings = embeddings[city_df.index.values]

    user_lat = req.user_lat if req.user_lat is not None else city_df["lat"].median()
    user_long = req.user_long if req.user_long is not None else city_df["long"].median()
    proximity_coef = req.proximity_coef if req.user_lat is not None else 0.0

    query_embedding = model.encode([req.query], convert_to_tensor=True, device="cpu")
    similarities = util.cos_sim(query_embedding, city_embeddings)[0].cpu().numpy()
    city_df["similarity"] = similarities

    scaler_rating = MinMaxScaler()
    scaler_reviews = MinMaxScaler()
    city_df["normalized_rating"] = scaler_rating.fit_transform(city_df[["rating"]])
    city_df["normalized_reviews"] = scaler_reviews.fit_transform(np.log1p(city_df[["reviews"]]))

    def distance_score(lat, long):
        km = geodesic((lat, long), (user_lat, user_long)).km
        return np.exp(-km / 5)

    city_df["distance_score"] = city_df.apply(
        lambda row: distance_score(row["lat"], row["long"]), axis=1
    )

    city_df["final_score"] = (
        req.similarity_coef * city_df["similarity"] +
        req.rating_coef * city_df["normalized_rating"] +
        req.review_coef * city_df["normalized_reviews"] +
        proximity_coef * city_df["distance_score"]
    )

    columns = ['maps_id', 'location_name', 'final_score', 'rating', 'reviews',
               'lat', 'long', 'primary_type', 'types', 'GPT_summary']

    result = city_df[columns].sort_values(by="final_score", ascending=False).head(req.top_n)

    return result.to_dict(orient="records")
