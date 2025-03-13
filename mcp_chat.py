import ollama
import json
import sys
import requests
from datetime import datetime, timedelta
from nasa_tool import NasaApiTool, process_query

# Model to use for the chat application
MODEL_NAME = 'llama3.2:latest'

# NASA API key - using the provided key
NASA_API_KEY = 'vrLarPvunisrxeRSAFei0AaDY9hCtenVt6htfVyo'

def get_astronomy_picture(date=None):
    """Get the Astronomy Picture of the Day from NASA API"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}&date={date}"
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

def get_mars_photos(rover="curiosity", date=None):
    """Get Mars rover photos from NASA API"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    url = f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos?earth_date={date}&api_key={NASA_API_KEY}"
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

def get_neo_objects(date=None, count=5):
    """Get Near Earth Objects data from NASA API"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Calculate end date (7 days from start date)
    start_date = date
    end_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
    
    url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start_date}&end_date={end_date}&api_key={NASA_API_KEY}"
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

def get_model_response_with_nasa_data(user_query, nasa_data, data_type):
    """Generate a direct response using the NASA data without relying on the model"""
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
    
    return response

def mcp_chat():
    """
    Chat application that implements the Model Context Protocol by integrating
    NASA API data with a local LLM.
    """
    # Check if Ollama is available
    try:
        ollama.list()
    except Exception as e:
        print(f"Error: Unable to connect to Ollama. {str(e)}")
        print(f"Please install Ollama and the {MODEL_NAME} model.")
        sys.exit(1)
    
    print("\n" + "="*50)
    print(f"NASA-enhanced Chat using {MODEL_NAME}")
    print("="*50)
    print("This implementation demonstrates the Model Context Protocol (MCP)")
    print("by integrating NASA API data with a local LLM.")
    print("\nAsk about:")
    print("- Astronomy Picture of the Day (try: 'show me today's astronomy picture')")
    print("- Mars Rover photos (try: 'what photos did the Mars rover take recently?')")
    print("- Near-Earth Objects (try: 'are there any asteroids passing near Earth?')")
    print("- Earth imagery (try: 'show me images of Earth from space')")
    print("\nType 'exit' to quit")
    
    messages = []
    
    # Initialize NASA API tool
    nasa_tool = NasaApiTool()
    
    # Add an initial system message to help the model
    system_message = {
        "role": "system", 
        "content": "You are a helpful AI assistant with knowledge about space and NASA."
    }
    messages.append(system_message)
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        
        # Process the query using the NASA tool (MCP implementation)
        nasa_response = process_query(user_input)
        
        # Add user message to conversation history
        messages.append({"role": "user", "content": user_input})
        
        # If we have NASA data, use it
        if nasa_response:
            print(f"\nFetching data from {nasa_response['source']}...")
            prepared_response = nasa_response['response']
            print(f"\nAssistant: {prepared_response}")
            
            # Add the NASA-based response to conversation history
            messages.append({"role": "assistant", "content": prepared_response})
        else:
            # Otherwise, just get a regular response from the model
            print("Thinking...")
            try:
                response = ollama.chat(model=MODEL_NAME, messages=messages)
                content = response.get('message', {}).get('content', '')
                
                if content:
                    print(f"\nAssistant: {content}")
                    messages.append(response["message"])
                else:
                    print("\nNo response received from the model.")
            except Exception as e:
                print(f"\nError getting response from model: {str(e)}")

if __name__ == "__main__":
    try:
        mcp_chat()
    except KeyboardInterrupt:
        print("\nChat session terminated by user. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1) 