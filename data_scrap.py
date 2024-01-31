from collections import Counter
from bs4 import BeautifulSoup
import requests
import re

# SECTION FOR STOPWORDS
import nltk
nltk.download('punkt')
stopwords_set = set()

with open('stopwords-cs.txt', 'r', encoding='utf-8') as file:
    for line in file:
        word = line.strip()  # Remove leading/trailing whitespace and newline characters
        stopwords_set.add(word)

CAR_URL = 'https://auto.bazos.cz/'

# - znacka 
# - model 
# - cena 
# - najezd
# - stari 
# - vykon 

CAR_BRANDS = ['alfa', 'audi', 'bmw', 'citroen', 'dacia', 'fiat', 
              'ford', 'honda', 'hyundai', 'chevrolet', 'kia', 'mazda', 'mercedes', 'mitsubishi', 
              'nissan', 'opel', 'peugeot', 'renault', 'seat', 'suzuki', 'skoda', 'toyota', 'volkswagen'
              'volvo']

def scrap_this_url(url):
    response = requests.get(url=url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup


# Scrapping to get all car brands, returns list of car url endpoints 
def get_all_brands_url():
    brands_url = []

    soup = scrap_this_url(CAR_URL)

    menubar = soup.find(class_="barvaleva")
    if menubar:
        a_tags = menubar.find_all('a')
        for tag in a_tags[:24]:
            car_href = tag.get('href')
            brand = car_href[1:-1]
            brands_url.append((brand ,f'https://auto.bazos.cz{car_href}'))
    
    return brands_url

def get_all_pages(url_brand_list: list):
    dict_url = {}

    for brand_url in url_brand_list:
        soup = scrap_this_url(brand_url[1])
        num_of_objs_text = soup.find('div', class_='inzeratynadpis').text.split('z ')[1].strip()
        num_of_objs = int(num_of_objs_text.replace(' ', ''))

        if brand_url[0] not in dict_url:
            dict_url[brand_url[0]] = []
        
        dict_url[brand_url[0]].append(brand_url[1])

        for x in range(20,num_of_objs,20):
            dict_url[brand_url[0]].append(f'{brand_url[1]}{x}/')
    
    return dict_url



# scrap the page and returns list of urls to detail offer 
def get_car_detail_url_onpage(dict_url: dict) -> list:
       base_url = 'https://auto.bazos.cz'
       for brand, urls_list in dict_url.items():  # Iterate over each brand and its list of URLs
        for page_url in urls_list:  # Iterate over each page URL
            soup = scrap_this_url(page_url)
            headings = soup.find_all('div', class_='inzeraty inzeratyflex')
            if headings:
                for head in headings:
                    relative_url = head.find('a').get('href')
                    absolute_url = f"{base_url}{relative_url}"
                    yield absolute_url  # Yield the car detail URL
            else:
                print('Header not found for:', page_url)


# scraps the detail page of offer and returns data from it 
def get_car_details(car_url):

    soup = scrap_this_url(car_url)

    header = soup.find(class_="nadpisdetail").text
    x = soup.find('table').find('td', class_='listadvlevo').find('table').find_all('tr')[-1].text
    price = int("".join(re.findall(r'\d+', x)))
    description = soup.find('div', class_='popisdetail').text.strip()

    print(header)
    print(price)
    print(len(description))

STRING_LIST = [
    'Nadstandardně vybavený vůz: Rok výroby 2019,6-mist,najeto 93 tisíc,v záruce, motor 2.0 Ecoblue 170k - bixenonové světlomety včetně denního svícení s LED technologií s funkcí odbočovacích světel a přední mlhové světlomety - parkovací kamera - nástupní schůdek vpravo i vlevo -jednosedadlo řidiče nastavitelné v 8 směrech s loketní opěrkou - vyhřívání sedadla řidiče a spolujezdce - čelní airbag spolujezdce a boční a hlavové airbagy vpředu - Audio sada 24 -Sync 3 s dotykovým displejem a hlasovým ovladaním,navigace s bezlatnou aktualizaci s ovládáním rádia na volantu, 6 reproduktorů, 4" displej, Bluetooth, USB, automatické nouzové volání Emergency Assist - Sada Viditelnost Plus - elektricky vyhřívané čelní sklo, elektricky ovládaná, sklopná vyhřívaná vnější zrcátka, ukazatel hladiny ostřikovače, automatické světlomety, automatické stěrače s dešťovým senzorem - dvoukřidle výklopné dveře vzadu - s vyhřívaným zadním sklem, - tažné zařízení včetně systému stabilizace přívěsu,zesílená zadní náprava,chránič motoru ze spodu,antiradar vestavěny,alarm,plechové 4 disky včetně letních gum vzorek 90%,elektrony celoroční pneu ,cena uvedena bez DPH,první majitel Barva černá',
    'Prodám pěkné BMW e46 330i 170kw. Motor: 3.0i 170kw Rok výroby: 2002 Najeto: 400 xxx km Převodovka: Manuál 5q Barva: blacksapphire metallic Plní EURO 4 Auto na svůj věk v zachovalém stavu. Výbava: - Jedná se o originální Mpaket II z výroby (žádná dodělávka). - Originální M kola R18 na zimních pneu. - Xenonové světlomety - 4x elektrické okna - multifunkční volant - střešní okno - atd STK do roku 2025 Auto původem z ČR, kde jsme třetím majitelem. Servisováno u AutoBeky. Vady: Ťuknutý zadní nárazník, chycené zadní dveře a nárazník, žere olej cca 1l na 1000km. Rozdrbané bočnice u sedadla řidiče. V případě zájmu není problém domluvit se na testovací jízdě, kontrole. V případě rychlého jednání možná sleva',
    'Mazda CX 5 2,2 D 110 kW v provozu od 9/2014 najeto 170 000 km nafta výkon 110 kW STK 1/2025 servisní knížka šestistupňová převodovka možnost sjednání prodloužené záruky kryjící mechanické a elektrické poruchy vozu až na 36 měsíců s vozem je možno ihned odjet, nejvýhodnější pojištění a převozní značku vyřídíme na místě, přihlášení pouze 800 Kč Výbava: - automatická klimatizace - navigace - tempomat - bezklíčové ovládání - hlídání mrtvého úhlu - vyhřívané sedačky - BOSE premium sound - parkovací senzory - multifunkční volant - originál rádio - 4x el. okna - el. zrcátka - el. sklopná zrcátka - vyhřívaná zrcátka - 6x airbag - palubní počítač - dešťový senzor - alu kola 17 - automatické svícení - mlhovky - bluetooth prohlédněte si i další naše vozy na prodej sms a maily NEPIŠTE, pouze volat, děkuji'
]

def get_car_describtion(car_detail_urls: list) -> list:
    describtions = []
    for url in car_detail_urls:
        soup = scrap_this_url(url=url)
        text = soup.find('div', class_='popisdetail').text.strip()
        describtions.append(text)
    return describtions


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


# scrap all brands 
# for each brand 
#   scrap all car urls details 
#   How to do it with multible pages?? 
#   for each car detail 
#       scrap car description 
#           save it into list as str 
# run frequency analysis 




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

# TEST String analysis to find MILEAGE
LONGSTRING = "Nabízíme k prodeji Citroen C-Elysée ve výbavě Tendance s motorizací 1.2 PureTech (60 kW - 82 koní). Vůz zakoupen jako nový v České republice (1. registrace 12/2017), po 1. majiteli s pravidelnou servisní historií podloženou servisní knihou. Aktuálně najeto 40 866 km. Vůz s nízkými provozními náklady, s jasnou historií a minulostí - nehavarováno. Drobné kosmetické vady. Bezpečnostní systémy: ABS, ESP, Protiprokluzový systém kol (ASR) Asistenční systémy: Tempomat Zabezpečení vozidla: Centrální zamykání, Dálkové centrální zamykání Vnitřní výbava a komfort: Deaktivace airba u spolujezdce, El. ovládání oken, El. ovládání zrcátek, Nastavitelný volant, Posilovač řízení, Senzor tlaku v pneumatikách, Venkovní teploměr, Vyhřívaná zrcátka Palubní systémy a konektivita: Autorádio, CD přehrávač, Originální autorádio, Palubní počítač Sedadla: Dělená zadní sedadla, Nastavitelná sedadla, Příprava pro isofix Světelná technika: Mlhovky Vnější výbava: Tónovaná skla Výpis Cebia zašleme na vyžádání. K vidění v Dolním Benešově (PSČ: 747 22). Podobné jako Škoda Rapid, Hyundai i20, Hyundai i30, Kia Cee'd aj."
LONGSTR2 = "Prodám Honda Civic 1.4i, uvedení do provozu: 21.01.2011, najeto: 155 000 km, palivo: benzín, objem: 1339, výkon: 73KW Původ ČR, 1.Majitel, STK do 3/2025, Nové Zimní Pneu, prověřeno společností Cebia, 2x klíč, Servisní knížka výbava: Automatická Klimatizace, Palubní počítač, Centrální zamykání, El.okna, El.zrcátka, Rádio, ABS, ESP, 6x Airbag, AUX, Tažné zařízení, Startování tlačítkem, Tonovaná skla"
LONGSTR3 = "Prodám BMW F31 320D Touring 2.0 140kW CR AUTOMAT, rok první registrace 10/2017 (model 2018), najeto 184.000km. STK do 9/2025 Možnost odpočtu DPH - Cena s DPH - PÍSEMNÁ ZÁRUKA NA PŮVOD VOZU A STAV NAJETÝCH KM"
LONGSTR4 = 'Prodám C5 Rok výroby 2008, Dvoulitr 100 kW, najeto 239tis km. Vše funkční, dvou zónová klimatizace, kompletní servis v létě 2023. STK platná do září 2025. Nové zimní pneu na hlinikových 16 + sada letních kol (hliníkové 17). Vnitřek zachovaly, sedadla po celou dobu v návlecích. Na pravé straně mírně promáčknuté zadní dvere a blatník. Auto bez investic. Při rychlém jednání možná sleva.'
LONGSTR5 = 'Mazda 3 2,2 Skyactiv D Rok výroby: 2014 Najeto: 170 xxx km Palivo: Diesel Převodovka: manuál (6ti stupňová) Výkon: 110kW (150 HP) STK: do únor 2026'       

if __name__ == "__main__":
    # brand_list = get_all_brands_url()
    # all_pages_dict = get_all_pages(url_brand_list=brand_list)
    # car_details_url = get_car_detail_url_onpage(dict_url=all_pages_dict)
    # describtions_list = get_car_describtion(car_detail_urls=car_details_url)
    # print(get_frequency_analysis(string_list=describtions_list).most_common(30))

    # TEST 
    ls = {'volvo': ['https://auto.bazos.cz/volvo/60/']}
    detail_urls = get_car_detail_url_onpage(dict_url=ls)
    details_list = get_car_describtion(car_detail_urls=detail_urls)
    print(get_frequency_analysis(string_list=details_list).most_common(10))
    
    