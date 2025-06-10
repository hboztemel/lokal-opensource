#!/bin/bash

# CONFIGURATION
API_KEY="your_api_key"

### INPUT CSV MUST CONTAIN "maps_id" column ###
INPUT_CSV="./np_postprocessed.csv"
OUTPUT_CSV="./pd_output.csv" 
LOG_FOLDER="./logs"
mkdir -p "$LOG_FOLDER"

# Create header for output CSV
echo "maps_id,display_name,good_for_groups,good_for_children,primary_type,editorial_summary" > "$OUTPUT_CSV"

# Progress counter
i=0

tail -n +2 "$INPUT_CSV" | while IFS=',' read -r maps_id_raw rest_of_line || [[ -n "$maps_id_raw" ]]; do
    ((i++))

    # Fix: Clean the maps_id from the raw input line
    # 'tr -d '\r'' removes Windows-style carriage returns
    # 'xargs' removes leading/trailing spaces and newlines
    maps_id=$(echo "$maps_id_raw" | tr -d '\r' | xargs)

    # Skip if Place ID is empty after cleaning
    if [[ -z "$maps_id" ]]; then
        echo "Skipping row $i: Empty Place ID found after cleaning. Raw: '$maps_id_raw'"
        continue
    fi

    echo "--- Processing Place ID $i: $maps_id ---"

    # Construct URL with the now correctly populated maps_id
    URL="https://places.googleapis.com/v1/places/$maps_id"

    # API Request
    RESPONSE=$(curl -sS -X GET \
        -H "Content-Type: application/json" \
        -H "X-Goog-Api-Key: $API_KEY" \
        -H "X-Goog-FieldMask: *" \
        "$URL" 2>&1) # Redirect stderr to stdout to capture curl errors

    # Save raw response (optional). Use the clean maps_id for the filename.
    echo "$RESPONSE" > "$LOG_FOLDER/response_${maps_id}.json"

    # Check for API error in the response
    if echo "$RESPONSE" | jq -e '.error' > /dev/null; then
        ERROR_MESSAGE=$(echo "$RESPONSE" | jq -r '.error.message // "Unknown API error"')
        ERROR_STATUS=$(echo "$RESPONSE" | jq -r '.error.status // "N/A"')
        echo "API Error for $maps_id (Status: $ERROR_STATUS): $ERROR_MESSAGE"
        # Set fields to empty if an error occurs to ensure output consistency
        display_name=""
        good_for_groups=""
        good_for_children=""
        primary_type=""
        editorial_summary="" # Initialize editorial_summary as empty on error
        # Append empty record and continue to next Place ID
        echo "\"$maps_id\",\"$display_name\",\"$good_for_groups\",\"$good_for_children\",\"$primary_type\",\"$editorial_summary\"" >> "$OUTPUT_CSV"
        sleep 0.3
        continue
    fi

    # Extract fields
    # Use // empty to handle missing fields gracefully
    display_name=$(echo "$RESPONSE" | jq -r '.displayName.text // empty')
    good_for_groups=$(echo "$RESPONSE" | jq -r '.goodForGroups // empty')
    good_for_children=$(echo "$RESPONSE" | jq -r '.goodForChildren // empty')
    primary_type=$(echo "$RESPONSE" | jq -r '.primaryType // empty')
    # Extract editorial_summary.text if it exists, otherwise empty
    editorial_summary=$(echo "$RESPONSE" | jq -r '.editorialSummary.text // empty')

    # Check if any meaningful data returned from the API call
    if [[ -z "$display_name" && -z "$primary_type" && -z "$editorial_summary" ]]; then
        echo "No meaningful data found for: $maps_id (after successful API call, fields might be empty)" | tee -a "$LOG_FOLDER/missing_ids.log"
    fi

    # Append to output CSV
    # Each field is enclosed in double quotes to handle commas/special characters within data
    echo "\"$maps_id\",\"$display_name\",\"$good_for_groups\",\"$good_for_children\",\"$primary_type\",\"$editorial_summary\"" >> "$OUTPUT_CSV"

    # Introduce a small delay to respect API rate limits
    sleep 0.3
done

echo "All Place Details requests completed. Results saved to: $OUTPUT_CSV"
