from collections import Counter
from bs4 import BeautifulSoup
import re

import asyncio
import aiohttp

import time

# dictionary for car brands and its models
import car_models

from database_operations import check_if_car, fetch_data_into_database


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
# Filter for string, clear it out of stop words
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


# ANALYSING STRINGS FNCS
# Getting data from string with regex
def get_mileage(long_string: str):
    text = re.sub(r'[^\w\s]', '', long_string.lower())
    words_uned = text.split()
    # Define regular expression pattern for mileage
    pattern = r'(\d{1,3}(?:\s?\d{3})*(?:\.\d+)?)\s?km'  # Matches numbers with optional thousands separators followed by optional ' km'
    pattern2 = r'(\d{1,3}(?:\s?\d{3})*)(?:\.|\s?tis\.?)\s?km'   # Matches mileage value with 'tis' representing thousands followed by 'km'
    pattern3 = r'(\d{1,3}(?:\s?\d{3})*)(?:\s?xxx\s?km)'

    # Find all matches of the pattern in the text
    matches1 = re.findall(pattern, text)
    matches2 = re.findall(pattern2, text)
    matches3 = re.findall(pattern3, text)

    # Extract mileage from the matches
    mileage = None
    if matches1:  # Check pattern 1 matches first
        try:
            mileage = int(matches1[0].replace(' ', ''))  # Remove spaces and dots from the matched value
        except ValueError:
                pass
    elif matches2:  # If pattern 1 doesn't match, check pattern 2 matches
        try:
            mileage = int(matches2[0].replace(' ', '')) * 1000  # Convert 'tis' to thousands
        except ValueError:
                pass
    elif matches3:
        try:
            mileage = int(matches3[0].replace(' ', '')) * 1000
        except ValueError:
                pass
    return mileage

def get_power(long_string: str):
    text = re.sub(r'[^\w\s]', '', long_string.lower())
    pattern_kW = re.compile(r'(\d{1,3})\s?kw', re.IGNORECASE)
    match = pattern_kW.search(text)
    if match:
        return int(re.sub(r'\D', '', match.group(1)))  # Remove non-digit characters
    return None

def get_year_manufacture(long_string: str) -> int:
    pattern = re.compile(r'(?:rok výroby|R\.?V\.?|rok|r\.?v\.?|výroba)?\s*(\d{4})\b', re.IGNORECASE)
    match = pattern.search(long_string)
    if match:
        return int(match.group(1))
    return None

def get_model(brand, header: str) -> str:
    models = CAR_MODELS.get(brand)
    if models is not None:
        pattern = re.compile(r'\b(?:' + '|'.join(models) + r')\b', re.IGNORECASE)
        match = pattern.search(header)
        if match:
            return match.group(0)
    return None

# ASYNCHRONOUS WEB SCRAPPING
# Cascade of web srappping to get detail info about car offer 

async def fetch_data(url, session):
    async with session.get(url) as response:
        return await response.text()
# getting urls for brands
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

# for each brand getting urls for all their pages
async def get_all_pages_for_brands(brand_url_list, session):
    # Fetch all pages for each brand asynchronously
    allpages_for_brand_list = []
    for brand_url in brand_url_list:
        brand, base_url = brand_url
        data = await fetch_data(base_url, session)
        soup = BeautifulSoup(data, 'html.parser')
        num_of_objs_text = soup.find('div', class_='inzeratynadpis').text.split('z ')[1].strip()
        num_of_objs = int(num_of_objs_text.replace(' ', ''))
        pages = [f"{base_url}{x}/" for x in range(20, num_of_objs, 20)]
        allpages_for_brand_list.append((brand, pages))
    return allpages_for_brand_list

# [(brand, [all brand url pages])]

# going through brand pages and getting urls for car offers detail
async def get_urls_for_details(brand_pages, session):
    async def fetch_and_process(url):
        data = await fetch_data(url, session)
        soup = BeautifulSoup(data, 'html.parser')
        headings = soup.find_all('div', class_='inzeraty inzeratyflex')
        urls_detail_list = []
        if headings:
            for head in headings:
                relative_url = head.find('a').get('href')
                absolute_url = f"https://auto.bazos.cz{relative_url}"
                urls_detail_list.append(absolute_url)
        return urls_detail_list

    tasks = [fetch_and_process(url) for brand, pages in brand_pages for url in pages]
    results = await asyncio.gather(*tasks)
    
    final_list = [(brand, url) for brand, pages in brand_pages for urls in results for url in urls]
    return final_list

# [(brand, [all detail urls])]

# scrapping description, heading
async def get_descriptions_headings_price(brand_urls, session):
    async def fetch_and_process(brand, url):
        data = await fetch_data(url, session)
        soup = BeautifulSoup(data, 'html.parser')

        description = soup.find('div', class_='popisdetail').text.strip()
        heading = soup.find(class_="nadpisdetail").text.strip()
        price_nc = soup.find('table').find('td', class_='listadvlevo').find('table').find_all('tr')[-1].text
        price_digits = ''.join(re.findall(r'\d+', price_nc))
        price = int(price_digits) if price_digits else None

        is_car = check_if_car(description, heading, price=price)
        if not is_car:
            return None

        return brand, url, description, heading, price  # Return URL as well

    tasks = [fetch_and_process(brand, url) for brand, url in brand_urls]
    results = await asyncio.gather(*tasks)

    final_list = [result for result in results if result is not None]
    return final_list

# processing the string and retrieving the data
async def process_data(brand, url, description, heading, price):
    model = get_model(brand=brand, header=heading)
    mileage = get_mileage(long_string=description) or get_mileage(long_string=heading)
    year_manufacture = get_year_manufacture(long_string=description) or get_year_manufacture(long_string=heading)
    power = get_power(long_string=description) or get_power(long_string=heading)

    car_data = {
        "brand": brand,
        "model": model,
        "year_manufacture": year_manufacture,
        "mileage": mileage,
        "power": power,
        "price": price,
        "heading": heading,
        "url": url  # Add URL
    }
    return car_data


# all together 
async def main():
    # Step 1: Get car brands URLs
    # brand_urls = await get_brand_urls()
    async with aiohttp.ClientSession() as session:
        # Step 2: Get all pages for each brand
        brand_pages = await get_all_pages_for_brands([('chevrolet', 'https://auto.bazos.cz/toyota/')], session)
        
        # Step 3: Get URLs for details on each page concurrently
        urls_detail_list = await get_urls_for_details(brand_pages, session)
        
        # Step 4: Get descriptions, headings, and prices concurrently
        descriptions_headings_price_list = await get_descriptions_headings_price(urls_detail_list, session)
        
        # Step 5: Create tasks for processing data asynchronously
        tasks = [process_data(brand, description, heading, price, url) for brand, description, heading, price, url in descriptions_headings_price_list
]
        processed_data = await asyncio.gather(*tasks)
        
        

        # Step 6: Save data into database 
        await fetch_data_into_database(data=processed_data)

async def run():
    await main()



if __name__ == "__main__":
    start_time= time.time()
    asyncio.run(run())
    end_time = time.time()
    print("Execution time:",end_time-start_time)
    

