from collections import Counter
from bs4 import BeautifulSoup
import requests
import re

import asyncio
import aiohttp

import time

import car_models

# SECTION FOR STOPWORDS
import nltk
nltk.download('punkt')
stopwords_set = set()

with open('stopwords-cs.txt', 'r', encoding='utf-8') as file:
    for line in file:
        word = line.strip()  # Remove leading/trailing whitespace and newline characters
        stopwords_set.add(word)

CAR_URL = 'https://auto.bazos.cz/'

CAR_MODELS = car_models.CAR_MODELS

CAR_BRANDS = ['alfa', 'audi', 'bmw', 'citroen', 'dacia', 'fiat', 
              'ford', 'honda', 'hyundai', 'chevrolet', 'kia', 'mazda', 'mercedes', 'mitsubishi', 
              'nissan', 'opel', 'peugeot', 'renault', 'seat', 'suzuki', 'skoda', 'toyota', 'volkswagen'
              'volvo']

def preprocess_text(text):
    # Tokenize text, remove stopwords, and convert to lowercase
    tokens = nltk.word_tokenize(text)
    filtered_tokens = [token.lower() for token in tokens if token.lower() not in stopwords_set and token.isalnum()]
    return filtered_tokens

# analyse string to get frequecy of words in offers 
def get_frequency_analysis(string_list: list):

    combined_text = ' '.join(string_list)
    preprocessed_text = preprocess_text(combined_text)
    word_counts = Counter(preprocessed_text)
    return word_counts


# ANALYSING STRINGS

def get_mileage(long_string: str):
    text = re.sub(r'[^\w\s]', '', long_string.lower())
    words_uned = text.split()
    # Define regular expression pattern for mileage
    pattern = r'(\d{1,3}(?:\s?\d{3})*(?:\.\d+)?)\s?km'  # Matches numbers with optional thousands separators followed by optional ' km'
    pattern2 = r'(\d{1,3}(?:\s?\d{3})*)(?:\.|tis\.?)\s?km'  # Matches mileage value with 'tis' representing thousands followed by 'km'
    pattern3 = r'(\d{1,3}(?:\s?\d{3})*)(?:\s?xxx\s?km)'

    # Find all matches of the pattern in the text
    matches1 = re.findall(pattern, text)
    matches2 = re.findall(pattern2, text)
    matches3 = re.findall(pattern3, text)

    # Extract mileage from the matches
    mileage = None
    if matches1:  # Check pattern 1 matches first
        mileage = int(matches1[0].replace(' ', ''))  # Remove spaces and dots from the matched value
    elif matches2:  # If pattern 1 doesn't match, check pattern 2 matches
        mileage = int(matches2[0].replace(' ', '')) * 1000  # Convert 'tis' to thousands
    elif matches3:
        mileage = int(matches3[0].replace(' ', '')) * 1000
    return mileage

def get_power(long_string: str):
    text = re.sub(r'[^\w\s]', '', long_string.lower())
    power = None

    pattern_kW = r'(\d{1,3})\s?kw'

    matches_kW = re.findall(pattern_kW, text, re.IGNORECASE)
    if matches_kW:  # If kW pattern matches
        power = int(matches_kW[0].replace(' ', '').replace('.', ''))  # Remove spaces and dots from the matched value

    return power

def get_year_manufacture(long_string: str) -> int: 
    manufacture_year = None
    clean_string = "".join(preprocess_text(text=long_string))

    pattern = r'(?:rok výroby|R\.?V\.?|manufacture year|model year):\s*(\d{4})\b'

    matches = re.findall(pattern, clean_string, re.IGNORECASE)
    if matches:
        manufacture_year = int(matches[0])      

    return manufacture_year

def get_model(brand ,header: str) -> str:
    models = CAR_MODELS.get(brand)
    if models is not None:
        pattern = r'\b(?:' + '|'.join(models) + r')\b'
        match = re.search(pattern, header, re.IGNORECASE)
        if match:
            return match.group(0)
    return None

# ASYNCHRONOUS 

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def get_brand_urls():
    # Fetch car brands URLs asynchronously
    brand_url_list = []
    data = await fetch_data(CAR_URL)
    soup = BeautifulSoup(data, 'html.parser')
    menubar = soup.find(class_="barvaleva")
    if menubar:
        a_tags = menubar.find_all('a')
        for tag in a_tags[:24]:
            car_href = tag.get('href')
            brand = car_href[1:-1]
            brand_url_list.append((brand,f'https://auto.bazos.cz{car_href}'))
    return brand_url_list

# [(bran, brand_url)]

async def get_all_pages_for_brands(brand_url_list):
    # Fetch all pages for each brand asynchronously
    allpages_for_brand_list = []
    for brand_url in brand_url_list:
        brand, base_url = brand_url
        data = await fetch_data(base_url)
        soup = BeautifulSoup(data, 'html.parser')
        num_of_objs_text = soup.find('div', class_='inzeratynadpis').text.split('z ')[1].strip()
        num_of_objs = int(num_of_objs_text.replace(' ', ''))
        pages = [f"{base_url}{x}/" for x in range(20, num_of_objs, 20)]
        allpages_for_brand_list.append((brand, pages))
    return allpages_for_brand_list

# [(brand, [all brand url pages])]

async def get_urls_for_details(allpages_for_brand_list):
    # Fetch URLs for details on each page asynchronously
    final_list = []
    for pages in allpages_for_brand_list:
        brand = pages[0]
        urls_detail_list = []
        for page_url in pages[1]:
            data = await fetch_data(page_url)
            soup = BeautifulSoup(data, 'html.parser')
            headings = soup.find_all('div', class_='inzeraty inzeratyflex')
            if headings:
                for head in headings:
                    relative_url = head.find('a').get('href')
                    absolute_url = f"https://auto.bazos.cz{relative_url}"
                    urls_detail_list.append(absolute_url)
        final_list.append((brand, urls_detail_list))
    return final_list

# [(brand, [all detail urls])]

async def get_descriptions_headings_price(brand_details_urls):
    # Fetch descriptions and headings asynchronously
    final_list = []
    for brand, urls_detail_list in brand_details_urls:
        descriptions_headings_price_list = []
        for url in urls_detail_list:
            data = await fetch_data(url)
            soup = BeautifulSoup(data, 'html.parser')
            description = soup.find('div', class_='popisdetail').text.strip()
            heading = soup.find(class_="nadpisdetail").text.strip()
            price_nc= soup.find('table').find('td', class_='listadvlevo').find('table').find_all('tr')[-1].text
            price_digits = ''.join(re.findall(r'\d+', price_nc))
            price = int(price_digits[0]) if price_digits else None
            descriptions_headings_price_list.append((brand, description, heading, price))  # Include brand in the tuple
        final_list.extend(descriptions_headings_price_list)  # Extend the final_list with descriptions_headings_list
    return final_list

async def process_data(brand, description, heading, price):
    # Process data asynchronously
    # Perform string analysis, extract information like brand, model, mileage, power, year of manufacture, price
    # Return car JSON
    model = get_model(brand=brand, header=heading)
    mileage = get_mileage(long_string=description)
    year_manufacture = get_year_manufacture(long_string=description)
    
    car_data = {
        "brand": brand,
        "model": model,
        "year_manufacture": year_manufacture,
        "mileage": mileage,
        "price": price
    }
    return car_data

async def main():
    # Step 1: Get car brands URLs
    brand_url_list = await get_brand_urls()

    # Select a subset of brand URLs for testing
    brand_url_list = brand_url_list[11:12]  # Select the first brand URL for testing
    
    # Step 2: Get all pages for each brand
    allpages_for_brand_list = await get_all_pages_for_brands(brand_url_list)

    # Select a subset of pages for testing
    allpages_for_brand_list = allpages_for_brand_list[:1]  # Select the first page for testing
    
    # Step 3: Get URLs for details on each page
    urls_detail_list = await get_urls_for_details(allpages_for_brand_list)
    
    # Select a subset of URLs for testing
    urls_detail_list = urls_detail_list[:1]  # Select the first URL for testing
    
    # Step 4: Get descriptions and headings
    descriptions_headings_list = await get_descriptions_headings_price(urls_detail_list)
    
    # Step 5: Create tasks for processing data asynchronously
    tasks = [process_data(brand, description, heading, price) for brand, description, heading, price in descriptions_headings_list]
    processed_data = await asyncio.gather(*tasks)
    
    # Step 6: Handle processed data
    for car_data in processed_data:
        print(car_data)

async def run():
    await main()



if __name__ == "__main__":
    asyncio.run(run())
    print(time.time())
    
"""
1. get car brands url, returns brand_url_list
2. takes brand_url_list, get get all pages for each brand, returns allpages_for_brand_list
3. takes returns allpages_for_brand_list, get get all urls for detail on page, returns urls_detail_list 
4. takes urls_detail_list, get describtion text and heading text from detail url
5. process data (describtion text and heading text) - analyse string for each car offer
6. create car json with brand, model, mileage, power, year of manufacture, price
7. save it into dabase 
8. create api endpoint with filters and comparison 
"""