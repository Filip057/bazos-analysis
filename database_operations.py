import re

def check_if_car(car_data):
    
    heading = car_data['heading']
    model = car_data['model']
    
    if model == None:
        return False

    non_car_keywords = [ 'ALU','kola' ,'kol' ,'sada','díly', 'sklo', 'pneu', 'pneumatiky', 'disky', 'sedadla', 'baterie', 'náhradní', 'zrcátka', 'motocykl', 'motorky', 'moto', 'kolo', 'kola', 
                        'skútr','motorové', 'karavany', 'choppery', 'endura', 'autobus', 'autodíly', 'zimní', 'letní',]
    
    non_car_pattern = re.compile(r'\b(?:' + '|'.join(map(re.escape, non_car_keywords)) + r')\b', re.IGNORECASE)
    
    # Check if any non-car keyword is present in the heading
    is_car = not bool(non_car_pattern.search(heading))

    return is_car



