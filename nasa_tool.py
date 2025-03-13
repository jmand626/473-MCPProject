"""
NASA Data Integration Tool

This module provides functions to interact with NASA APIs and implements the Model Context Protocol (MCP).
It allows AI models to request and integrate real-time space data into their responses.
"""

import requests
import json
import os
from datetime import datetime, timedelta
import re

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# NASA API key - using the provided key
NASA_API_KEY = 'vrLarPvunisrxeRSAFei0AaDY9hCtenVt6htfVyo'

class NasaApiTool:
    def __init__(self, api_key=None):
        # Use provided API key or get from environment variable or use the default key
        self.api_key = api_key or os.environ.get('NASA_API_KEY', NASA_API_KEY)
        
    def get_tool_definition(self):
        return {
            "type": "function",
            "function": {
                "name": "nasa_api",
                "description": "Access NASA data including astronomy picture of the day, Mars rover photos, and near-Earth objects",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "endpoint": {
                            "type": "string",
                            "enum": ["apod", "mars_photos", "neo", "earth"],
                            "description": "NASA API endpoint to query. Use 'apod' for Astronomy Picture of the Day, 'mars_photos' for Mars rover photos, 'neo' for Near-Earth Objects, and 'earth' for Earth imagery."
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for the query in YYYY-MM-DD format, defaults to today"
                        },
                        "rover": {
                            "type": "string",
                            "enum": ["curiosity", "opportunity", "spirit", "perseverance"],
                            "description": "Mars rover to get photos from (for mars_photos endpoint)"
                        },
                        "camera": {
                            "type": "string",
                            "description": "Camera name for Mars rover photos (optional)"
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of items to return (default: 1)"
                        }
                    },
                    "required": ["endpoint"]
                }
            }
        }
    
    def call(self, params):
        # Normalize the endpoint name
        endpoint = self._normalize_endpoint(params.get("endpoint", ""))
        date = params.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        try:
            if endpoint == "apod":
                return self._get_astronomy_picture(date)
            elif endpoint == "mars_photos":
                rover = params.get("rover", "curiosity")
                camera = params.get("camera")
                return self._get_mars_photos(rover, date, camera)
            elif endpoint == "neo":
                count = params.get("count", 5)
                return self._get_near_earth_objects(date, count)
            elif endpoint == "earth":
                return self._get_earth_imagery(date)
            else:
                return {"error": f"Invalid endpoint specified: {endpoint}"}
        except Exception as e:
            return {"error": str(e)}
    
    def _normalize_endpoint(self, endpoint):
        """Normalize endpoint names to handle different variations"""
        endpoint = endpoint.lower().strip()
        
        # Handle different variations of APOD
        if endpoint in ["apod", "astronomy picture of the day", "astronomy-picture-of-the-day", "astronomy_picture_of_the_day"]:
            return "apod"
        
        # Handle different variations of Mars photos
        if endpoint in ["mars_photos", "mars photos", "mars-photos", "mars_rover", "mars rover", "mars-rover"]:
            return "mars_photos"
        
        # Handle different variations of NEO
        if endpoint in ["neo", "near earth objects", "near-earth-objects", "near_earth_objects"]:
            return "neo"
        
        # Handle different variations of Earth
        if endpoint in ["earth", "earth imagery", "earth-imagery", "earth_imagery"]:
            return "earth"
        
        # If no match, return the original
        return endpoint
    
    def _get_astronomy_picture(self, date):
        url = f"https://api.nasa.gov/planetary/apod?api_key={self.api_key}&date={date}"
        response = requests.get(url)
        data = response.json()
        return {
            "title": data.get("title"),
            "date": data.get("date"),
            "explanation": data.get("explanation"),
            "image_url": data.get("url"),
            "media_type": data.get("media_type"),
            "copyright": data.get("copyright", "NASA")
        }
    
    def _get_mars_photos(self, rover, date, camera=None):
        url = f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos?earth_date={date}&api_key={self.api_key}"
        if camera:
            url += f"&camera={camera}"
        
        response = requests.get(url)
        data = response.json()
        
        if not data.get("photos"):
            return {"message": f"No photos available for {rover} on {date}"}
        
        photos = data["photos"][:5]  # Limit to 5 photos
        return {
            "rover": rover,
            "date": date,
            "photo_count": len(photos),
            "photos": [
                {
                    "id": photo["id"],
                    "sol": photo["sol"],
                    "camera": photo["camera"]["full_name"],
                    "earth_date": photo["earth_date"],
                    "img_src": photo["img_src"]
                }
                for photo in photos
            ]
        }
    
    def _get_near_earth_objects(self, date, count=5):
        # For NEO, we use a 7-day range from the specified date
        start_date = date
        end_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
        
        url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start_date}&end_date={end_date}&api_key={self.api_key}"
        response = requests.get(url)
        data = response.json()
        
        all_neo = []
        for day in data["near_earth_objects"]:
            all_neo.extend(data["near_earth_objects"][day])
        
        # Sort by closest approach and take top 'count'
        all_neo.sort(key=lambda x: float(x["close_approach_data"][0]["miss_distance"]["kilometers"]))
        selected_neo = all_neo[:count]
        
        return {
            "total_count": data["element_count"],
            "period": f"{start_date} to {end_date}",
            "near_earth_objects": [
                {
                    "name": neo["name"],
                    "id": neo["id"],
                    "diameter_min_km": neo["estimated_diameter"]["kilometers"]["estimated_diameter_min"],
                    "diameter_max_km": neo["estimated_diameter"]["kilometers"]["estimated_diameter_max"],
                    "is_potentially_hazardous": neo["is_potentially_hazardous_asteroid"],
                    "close_approach_date": neo["close_approach_data"][0]["close_approach_date"],
                    "miss_distance_km": neo["close_approach_data"][0]["miss_distance"]["kilometers"],
                    "relative_velocity_kph": neo["close_approach_data"][0]["relative_velocity"]["kilometers_per_hour"]
                }
                for neo in selected_neo
            ]
        }
    
    def _get_earth_imagery(self, date):
        # Earth imagery requires lat/lon coordinates
        # For demo purposes, we'll use a fixed location (New York City)
        lat = 40.71
        lon = -74.00
        
        url = f"https://api.nasa.gov/planetary/earth/imagery?lon={lon}&lat={lat}&date={date}&api_key={self.api_key}"
        
        try:
            response = requests.get(url)
            data = response.json()
            return {
                "date": date,
                "location": "New York City",
                "coordinates": {"lat": lat, "lon": lon},
                "image_url": data.get("url", "No image available for this date/location")
            }
        except:
            return {
                "message": "Earth imagery may not be available for the specified date/location",
                "note": "The Earth imagery API has limited coverage and may return errors for some dates."
            }

def get_astronomy_picture(date=None):
    """
    Get the Astronomy Picture of the Day from NASA API
    
    Args:
        date (str, optional): Date in YYYY-MM-DD format. Defaults to today.
    
    Returns:
        dict: APOD data including title, explanation, and image URL
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}&date={date}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return {"error": f"API error: {response.status_code}", "message": response.text}
    
    data = response.json()
    
    return {
        "title": data.get("title"),
        "date": data.get("date"),
        "explanation": data.get("explanation"),
        "image_url": data.get("url"),
        "media_type": data.get("media_type"),
        "copyright": data.get("copyright", "NASA")
    }

def get_mars_photos(rover="curiosity", date=None):
    """
    Get Mars rover photos from NASA API
    
    Args:
        rover (str, optional): Mars rover name. Defaults to "curiosity".
        date (str, optional): Date in YYYY-MM-DD format. Defaults to today.
    
    Returns:
        dict: Mars rover photos data
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    url = f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos?earth_date={date}&api_key={NASA_API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return {"error": f"API error: {response.status_code}", "message": response.text}
    
    data = response.json()
    
    if not data.get("photos"):
        return {"message": f"No photos available for {rover} on {date}"}
    
    photos = data["photos"][:5]  # Limit to 5 photos
    return {
        "rover": rover,
        "date": date,
        "photo_count": len(photos),
        "photos": [
            {
                "id": photo["id"],
                "sol": photo["sol"],
                "camera": photo["camera"]["full_name"],
                "earth_date": photo["earth_date"],
                "img_src": photo["img_src"]
            }
            for photo in photos
        ]
    }

def get_neo_objects(date=None, count=5):
    """
    Get Near Earth Objects data from NASA API
    
    Args:
        date (str, optional): Start date in YYYY-MM-DD format. Defaults to today.
        count (int, optional): Number of NEOs to return. Defaults to 5.
    
    Returns:
        dict: Near Earth Objects data
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Calculate end date (7 days from start date)
    start_date = date
    end_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
    
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start_date}&end_date={end_date}&api_key={NASA_API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return {"error": f"API error: {response.status_code}", "message": response.text}
    
    data = response.json()
    
    all_neo = []
    for day in data["near_earth_objects"]:
        all_neo.extend(data["near_earth_objects"][day])
    
    # Sort by closest approach and take top 'count'
    all_neo.sort(key=lambda x: float(x["close_approach_data"][0]["miss_distance"]["kilometers"]))
    selected_neo = all_neo[:count]
    
    return {
        "total_count": data["element_count"],
        "period": f"{start_date} to {end_date}",
        "near_earth_objects": [
            {
                "name": neo["name"],
                "id": neo["id"],
                "diameter_min_km": neo["estimated_diameter"]["kilometers"]["estimated_diameter_min"],
                "diameter_max_km": neo["estimated_diameter"]["kilometers"]["estimated_diameter_max"],
                "is_potentially_hazardous": neo["is_potentially_hazardous_asteroid"],
                "close_approach_date": neo["close_approach_data"][0]["close_approach_date"],
                "miss_distance_km": neo["close_approach_data"][0]["miss_distance"]["kilometers"],
                "relative_velocity_kph": neo["close_approach_data"][0]["relative_velocity"]["kilometers_per_hour"]
            }
            for neo in selected_neo
        ]
    }

def get_epic_imagery(date=None):
    """
    Get Earth Polychromatic Imaging Camera (EPIC) imagery from NASA API
    
    Args:
        date (str, optional): Date in YYYY-MM-DD format. Defaults to most recent available.
    
    Returns:
        dict: EPIC imagery data
    """
    # First, get available dates
    url = f"https://api.nasa.gov/EPIC/api/natural/available?api_key={NASA_API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return {"error": f"API error: {response.status_code}", "message": response.text}
    
    available_dates = response.json()
    
    # If no date specified or date not available, use most recent
    if date is None or date not in available_dates:
        date = available_dates[0]  # Most recent date
    
    # Get EPIC imagery for the date
    url = f"https://api.nasa.gov/EPIC/api/natural/date/{date}?api_key={NASA_API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        return {"error": f"API error: {response.status_code}", "message": response.text}
    
    data = response.json()
    
    if not data:
        return {"message": f"No EPIC imagery available for {date}"}
    
    # Format the date for image URL construction
    dt = datetime.strptime(date, "%Y-%m-%d")
    formatted_date = dt.strftime("%Y/%m/%d")
    
    # Take the first 3 images
    images = data[:3]
    
    return {
        "date": date,
        "image_count": len(data),
        "images": [
            {
                "id": img["identifier"],
                "caption": img["caption"],
                "image_url": f"https://api.nasa.gov/EPIC/archive/natural/{formatted_date}/png/{img['image']}.png?api_key={NASA_API_KEY}",
                "date": img["date"],
                "centroid_coordinates": {
                    "lat": img["centroid_coordinates"]["lat"],
                    "lon": img["centroid_coordinates"]["lon"]
                }
            }
            for img in images
        ]
    }

def get_nasa_response(user_query):
    """
    Analyze a user query and fetch relevant NASA data
    
    Args:
        user_query (str): User's natural language query
    
    Returns:
        tuple: (data_type, nasa_data) or (None, None) if no relevant data
    """
    # Define keywords for different NASA API endpoints
    apod_keywords = ["astronomy picture", "apod", "picture of the day", "nasa image", "space photo"]
    mars_keywords = ["mars", "rover", "curiosity", "perseverance", "opportunity", "spirit"]
    neo_keywords = ["asteroid", "near earth", "neo", "object", "impact", "potentially hazardous"]
    epic_keywords = ["earth", "epic", "blue marble", "planet photo", "earth view", "earth image"]
    
    query = user_query.lower()
    
    # Check for APOD request
    if any(keyword in query for keyword in apod_keywords):
        # Check for specific date request
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', query)
        date = date_match.group(1) if date_match else None
        
        return "apod", get_astronomy_picture(date)
    
    # Check for Mars rover request
    elif any(keyword in query for keyword in mars_keywords):
        # Try to identify specific rover
        rover = "curiosity"  # default
        if "perseverance" in query:
            rover = "perseverance"
        elif "opportunity" in query:
            rover = "opportunity"
        elif "spirit" in query:
            rover = "spirit"
            
        # Check for specific date request
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', query)
        date = date_match.group(1) if date_match else None
        
        return "mars", get_mars_photos(rover, date)
    
    # Check for Near Earth Objects request
    elif any(keyword in query for keyword in neo_keywords):
        # Check for specific date request
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', query)
        date = date_match.group(1) if date_match else None
        
        return "neo", get_neo_objects(date)
    
    # Check for EPIC imagery request
    elif any(keyword in query for keyword in epic_keywords):
        # Check for specific date request
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', query)
        date = date_match.group(1) if date_match else None
        
        return "epic", get_epic_imagery(date)
    
    # No match found
    return None, None

def format_nasa_response(user_query, nasa_data, data_type):
    """
    Format NASA data into a user-friendly response
    
    Args:
        user_query (str): Original user query
        nasa_data (dict): NASA API response data
        data_type (str): Type of NASA data (apod, mars, neo, epic)
    
    Returns:
        str: Formatted response
    """
    if "error" in nasa_data:
        return f"Sorry, I encountered an error when trying to fetch NASA data: {nasa_data['error']}"
    
    if "message" in nasa_data:
        return f"NASA API message: {nasa_data['message']}"
    
    response = ""
    
    if data_type == "apod":
        response = f"""Today's Astronomy Picture of the Day is titled "{nasa_data['title']}" from {nasa_data['date']}.

Image URL: {nasa_data['image_url']}

Description: {nasa_data['explanation'][:500]}{'...' if len(nasa_data['explanation']) > 500 else ''}

Credit: {nasa_data.get('copyright', 'NASA')}

You can view this image and more at NASA's official APOD website: https://apod.nasa.gov/apod/
"""
    elif data_type == "mars":
        if "message" in nasa_data:
            response = f"NASA Mars Rover Data: {nasa_data['message']}"
        else:
            photos_text = "\n".join([
                f"- Photo {i+1}: Taken by {photo['camera']} on {photo['earth_date']} (Sol {photo['sol']})\n  URL: {photo['img_src']}"
                for i, photo in enumerate(nasa_data['photos'][:3])
            ])
            
            response = f"""I found {nasa_data['photo_count']} recent photos from the {nasa_data['rover']} Mars rover, dated {nasa_data['date']}.

Here are some of them:

{photos_text}

You can find more Mars rover photos on NASA's website: https://mars.nasa.gov/
"""
    elif data_type == "neo":
        objects = nasa_data['near_earth_objects']
        objects_text = "\n".join([
            f"- {obj['name']}: {obj['diameter_min_km']:.2f}-{obj['diameter_max_km']:.2f} km diameter, " +
            f"passing on {obj['close_approach_date']} at a distance of {float(obj['miss_distance_km']):.2f} km, " +
            f"{'⚠️ Potentially hazardous' if obj['is_potentially_hazardous'] else 'Not considered hazardous'}"
            for obj in objects[:3]
        ])
        
        response = f"""I found data on {nasa_data['total_count']} near-Earth objects from {nasa_data['period']}.

Here are the closest approaches:

{objects_text}

This information comes from NASA's Near Earth Object Web Service (NeoWs).
"""
    elif data_type == "epic":
        if "message" in nasa_data:
            response = f"NASA EPIC Data: {nasa_data['message']}"
        else:
            images_text = "\n".join([
                f"- Image {i+1}: {img['caption']} (at coordinates: {img['centroid_coordinates']['lat']}, {img['centroid_coordinates']['lon']})\n  URL: {img['image_url']}"
                for i, img in enumerate(nasa_data['images'][:3])
            ])
            
            response = f"""I found {nasa_data['image_count']} Earth images from NASA's EPIC camera for {nasa_data['date']}.

Here are some of them:

{images_text}

These images come from NASA's Earth Polychromatic Imaging Camera (EPIC).
"""
    
    return response

# Example of the MCP interface
def process_query(query):
    """
    Process a user query and return NASA data if relevant.
    This function implements the Model Context Protocol interface.
    
    Args:
        query (str): User's natural language query
    
    Returns:
        dict: Response with NASA data or None
    """
    data_type, nasa_data = get_nasa_response(query)
    
    if data_type and nasa_data:
        formatted_response = format_nasa_response(query, nasa_data, data_type)
        return {
            "response": formatted_response,
            "source": f"NASA {data_type.upper()} API",
            "data": nasa_data
        }
    
    return None

if __name__ == "__main__":
    # Example usage
    test_queries = [
        "Show me today's astronomy picture of the day",
        "What photos did the Mars rover take recently?",
        "Are there any asteroids passing near Earth?",
        "Show me images of Earth from space"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = process_query(query)
        if result:
            print(f"Source: {result['source']}")
            print(f"Response:\n{result['response']}")
        else:
            print("No NASA data found for this query.") 