#!/bin/bash

# CONFIGURATION
API_KEY="your_api_key"
CIRCLES_CSV="./Circles.csv"
TYPES_FILE="./Definitions.txt"
OUTPUT_CSV="./np_output.csv"
LOG_FOLDER="./logs"
mkdir -p "$LOG_FOLDER"

CITY="Istanbul"
COUNTRY="Turkiye"

INCLUDED_TYPES=$(jq -Rs 'split("\n") | map(select(. != ""))' "$TYPES_FILE")

echo "maps_id,location_name,rating,reviews,lat,long,primary_type,types,business_status,city,country" > "$OUTPUT_CSV"

# Progress counter
i=0

while IFS=',' read -r lat long radius; do
    ((i++))
    echo "Requesting area $i → lat: $lat, long: $long, radius: $radius"

    # Construct JSON request body
    REQUEST_BODY=$(jq -n \
        --argjson types "$INCLUDED_TYPES" \
        --arg lat "$lat" \
        --arg long "$long" \
        --arg radius "$radius" \
        '{
            includedTypes: $types,
            maxResultCount: 20,
            locationRestriction: {
                circle: {
                    center: {
                        latitude: ($lat | tonumber),
                        longitude: ($long | tonumber)
                    },
                    radius: ($radius | tonumber)
                }
            },
            rankPreference: "DISTANCE"
        }')

    # Perform the POST request
    RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
        -H "X-Goog-Api-Key: $API_KEY" \
        -H "X-Goog-FieldMask: places.id,places.displayName.text,places.rating,places.userRatingCount,places.location,places.primaryType,places.types,places.businessStatus" \
        -d "$REQUEST_BODY" \
        "https://places.googleapis.com/v1/places:searchNearby")

    echo "$RESPONSE" > "$LOG_FOLDER/response_circle_${i}.json"

    echo "$RESPONSE" | jq -r --arg city "$CITY" --arg country "$COUNTRY" '
        .places[]? |
        [
            .id,
            .displayName.text,
            (.rating // ""),
            (.userRatingCount // ""),
            (.location.latitude // ""),
            (.location.longitude // ""),
            (.primaryType // ""),
            (.types | join("/") // ""),
            (.businessStatus // ""),
            $city,
            $country
        ] | @csv
    ' >> "$OUTPUT_CSV"

    # Handle empty response
    if [[ $(echo "$RESPONSE" | jq '.places | length') -eq 0 ]]; then
        echo "No results for circle $i (lat: $lat, long: $long)"
    fi

    sleep 0.3
done < "$CIRCLES_CSV"

echo "All requests completed. Results saved to: $OUTPUT_CSV"
