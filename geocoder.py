import pandas as pd
from geopy.geocoders import ArcGIS
import time

# Load input csv file 
input_filename = "Addresses CC - Sheet1.csv"
output_filename = "geocoded_canada_addresses2.csv"

df = pd.read_csv(input_filename)

# Combine your split columns
# Change 'Street_Address', 'City', and 'Province' to match your exact CSV headers
df['Search_Query'] = (
    df['Street'].astype(str) + ", " + 
    df['City'].astype(str) + ", " + 
    df['Province'].astype(str) + ", Canada"
)

# Initialize the ArcGIS Geocoder 
geolocator = ArcGIS()

# Lists to temporarily hold the data for the new columns
postal_codes = []
latitudes = []
longitudes = []

print(f"Starting conversion for {len(df)} addresses...")
start_time = time.time()

# Process each address row by row
for index, query in enumerate(df['Search_Query']):
    try:
        # Request full geographic details from ArcGIS
        location = geolocator.geocode(query, out_fields="*")
        
        if location and location.raw:
            # Extract the raw attributes dictionary
            attributes = location.raw.get('attributes', {})
            # ArcGIS stores the retrieved postal code under the 'Postal' key
            postal = attributes.get('Postal', None)

            # Double-check and fallback to 'PostalExt' if 'Postal' is still short
            if not postal or len(str(postal).replace(" ", "")) < 6:
                postal_ext = attributes.get('PostalExt', '')
                if postal and postal_ext:
                    postal = f"{postal} {postal_ext}"
            
            postal_codes.append(postal)
            latitudes.append(location.latitude)
            longitudes.append(location.longitude)
        else:
            postal_codes.append(None)
            latitudes.append(None)
            longitudes.append(None)
            
    except Exception as e:
        print(f"Skipping row {index} due to error: {e}")
        postal_codes.append(None)
        latitudes.append(None)
        longitudes.append(None)
    
    # Progress update printout every 100 rows
    if (index + 1) % 100 == 0:
        print(f"Progress: {index + 1}/{len(df)} rows completed...")

# Store the retrieved data into brand new columns in dataframe
df['Postal_Code'] = postal_codes
df['Latitude'] = latitudes
df['Longitude'] = longitudes

# Drop the temporary search string and save the final dataset to a new CSV
df = df.drop(columns=['Search_Query'])
df.to_csv(output_filename, index=False)

end_time = time.time()
print(f"\nDone! Processed dataset in {round((end_time - start_time)/60, 2)} minutes.")
print(f"Your output file is saved as: '{output_filename}'")
