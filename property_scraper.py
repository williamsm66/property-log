import asyncio
import httpx
from parsel import Selector
import json
import re
import os
import random
from typing import Dict, Any, Optional

class PropertyScraper:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

    def find_json_objects(self, text: str, decoder=json.JSONDecoder()):
        """Find JSON objects in text, and generate decoded JSON data"""
        pos = 0
        while True:
            match = text.find("{", pos)
            if match == -1:
                break
            try:
                result, index = decoder.raw_decode(text[match:])
                yield result
                pos = match + index
            except ValueError:
                pos = match + 1

    def extract_key_features(self, selector):
        """Extract key features from the property page"""
        key_features = []
        feature_selectors = [
            '#key-features ul li::text',
            '.key-features ul li::text',
            '.property-features li::text',
            '.key-features__list-item::text'
        ]
        
        for selector_pattern in feature_selectors:
            features = selector.css(selector_pattern).getall()
            if features:
                key_features = [f.strip() for f in features if f.strip()]
                break
        
        return key_features

    def extract_station_details(self, selector):
        """Extract nearest station and its distance"""
        station_info = {}
        
        station_selectors = [
            '.nearby-stations__station',
            '.station-item',
            '[data-test="nearbyLocation"]'
        ]
        
        for station_selector in station_selectors:
            station_elements = selector.css(station_selector)
            if station_elements:
                first_station = station_elements[0]
                
                # Try different selectors for station name
                name_selectors = [
                    '.station-name::text',
                    '.station-title::text',
                    'h3::text',
                    '[data-test="location-name"]::text'
                ]
                
                for name_selector in name_selectors:
                    station_name = first_station.css(name_selector).get()
                    if station_name:
                        station_info['name'] = station_name.strip()
                        break
                
                # Try different selectors for distance
                distance_selectors = [
                    '.distance-miles::text',
                    '.station-distance::text',
                    '[data-test="distance"]::text',
                    '.distance::text'
                ]
                
                for distance_selector in distance_selectors:
                    distance_text = first_station.css(distance_selector).get()
                    if distance_text:
                        distance_match = re.search(r'([\d.]+)\s*(miles?|mi|km)', distance_text.lower())
                        if distance_match:
                            distance = float(distance_match.group(1))
                            unit = distance_match.group(2)
                            if 'km' in unit:
                                distance = distance * 0.621371  # Convert km to miles
                            station_info['distance'] = round(distance, 2)
                            break
        
        return station_info

    async def scrape_rightmove(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape property details from a Rightmove URL"""
        if not url or 'rightmove.co.uk' not in url:
            print("Invalid Rightmove URL provided")
            return None

        async with httpx.AsyncClient(
            headers={
                "User-Agent": random.choice(self.user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            timeout=30.0
        ) as client:
            try:
                print(f"Fetching property data from: {url}")
                response = await client.get(url)
                response.raise_for_status()
                
                # Parse the HTML
                selector = Selector(text=response.text)
                
                # Find all script tags
                scripts = selector.xpath('//script/text()').getall()
                
                # Look for property data in scripts
                property_data = None
                for script in scripts:
                    for obj in self.find_json_objects(script):
                        if isinstance(obj, dict) and 'propertyData' in obj:
                            property_data = obj['propertyData']
                            break
                    if property_data:
                        break

                if not property_data:
                    print("No property data found in the page")
                    return None

                # Extract required information
                main_photo = property_data.get('images', [{}])[0].get('url') if property_data.get('images') else None
                floorplan = property_data.get('floorplans', [{}])[0].get('url') if property_data.get('floorplans') else None
                description = property_data.get('text', {}).get('description', '')
                address = property_data.get('address', {}).get('displayAddress', '')
                estate_agent = property_data.get('customer', {}).get('branchDisplayName', '')

                # Extract price information
                price = None
                price_data = property_data.get('prices', {})
                if price_data:
                    if 'primaryPrice' in price_data:
                        price = price_data['primaryPrice']
                    elif 'displayPrices' in price_data and price_data['displayPrices']:
                        price = price_data['displayPrices'][0].get('displayPrice')

                # Extract bedrooms and bathrooms
                bedrooms = None
                bathrooms = None
                property_type = None

                # Try to get from property data first
                if 'bedrooms' in property_data:
                    bedrooms = property_data['bedrooms']
                if 'bathrooms' in property_data:
                    bathrooms = property_data['bathrooms']
                if 'propertyType' in property_data:
                    property_type = property_data.get('propertyType')

                # If not found, try to extract from key features or description
                if not any([bedrooms, bathrooms, property_type]):
                    features_text = ' '.join(self.extract_key_features(selector)).lower()
                    description_lower = description.lower()
                    
                    # Look for bedrooms
                    if not bedrooms:
                        bed_match = re.search(r'(\d+)\s*bed', features_text + ' ' + description_lower)
                        if bed_match:
                            bedrooms = int(bed_match.group(1))
                    
                    # Look for bathrooms
                    if not bathrooms:
                        bath_match = re.search(r'(\d+)\s*bath', features_text + ' ' + description_lower)
                        if bath_match:
                            bathrooms = int(bath_match.group(1))
                    
                    # Look for property type
                    if not property_type:
                        property_types = ['detached', 'semi-detached', 'terraced', 'flat', 'apartment', 'bungalow', 'maisonette']
                        for pt in property_types:
                            if pt in features_text or pt in description_lower:
                                property_type = pt.title()
                                break

                # Check if it's an auction property
                is_auction = any(
                    auction_word in description.lower() 
                    for auction_word in ['auction', 'guide price', 'for auction']
                )

                # Extract key features and station details
                key_features = self.extract_key_features(selector)
                station_info = self.extract_station_details(selector)
                
                result = {
                    'main_photo': main_photo,
                    'floorplan': floorplan,
                    'description': description,  # Return full description
                    'key_features': key_features,
                    'address': address,
                    'is_auction': is_auction,
                    'estate_agent': estate_agent,
                    'nearest_station': station_info.get('name'),
                    'station_distance': station_info.get('distance'),
                    'price': price,
                    'bedrooms': bedrooms,
                    'bathrooms': bathrooms,
                    'property_type': property_type
                }

                # Remove None values
                return {k: v for k, v in result.items() if v is not None}

            except httpx.HTTPError as e:
                print(f"HTTP error occurred: {str(e)}")
                return None
            except Exception as e:
                print(f"Error scraping property: {str(e)}")
                return None

async def main():
    # Test URL - replace with an actual Rightmove property URL
    url = "https://www.rightmove.co.uk/properties/153994193#/?channel=RES_BUY"
    
    scraper = PropertyScraper()
    result = await scraper.scrape_rightmove(url)
    
    if result:
        print("\n=== PROPERTY DETAILS ===")
        for key, value in result.items():
            print(f"\n{key.upper()}:")
            if isinstance(value, list):
                if value:
                    print("List contents:")
                    for item in value:
                        print(f"  - {item}")
                else:
                    print("Empty list")
            else:
                print(value)
    else:
        print("Failed to scrape property data")

if __name__ == "__main__":
    asyncio.run(main())
    import asyncio
    asyncio.run(main())
