from time import sleep
from datetime import datetime
from requests import get, post
from string import punctuation
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

get_url = "https://tcesffb3s8.execute-api.ap-south-1.amazonaws.com/dev/productscraping/getinput"
post_url = "https://tcesffb3s8.execute-api.ap-south-1.amazonaws.com/dev/sitestats"


def find_model(name):
    model = None
    model_found = False
    n = name.split()
    for i in n:
        for j in i:
            try:
                j = int(j)
                model_found = True
                model = i
                return model_found, model
            except:
                pass
    return model_found, model


def model_filter(name, model):
    return True if model.lower() in name.lower() else False


def get_data():
    #For API
    while True:
        data_dict = get(get_url).json()
        if data_dict['responseCode'] == 200:
            break
        else:
            #print('Data not available..')
            sleep(3)
    #For testing
#    data_dict = {
#        "responseCode": 200,
#        "responseMessage": "get scraping data from rabbitmq successfully",
#        "preferencePojo": {
#            "preferenceId": 84,
#            "userId": 1,
#            "url_scrap": "https://www.becextech.com.au/",
#            "product_scrap": "Apple  New Apple iPhone 12 Pro Max Dual SIM 5G 6GB RAM 512GB Blue (1 YEAR AU WARRANTY + "
#                             "PRIORITY DELIVERY)   New Apple iPhone 12 Pro Max Dual SIM 5G 6GB RAM 512GB Blue",
#            "createdDate": "2021-02-25 05:34:10",
#            "category": "Mobile",
#            "sku": "sku",
#            "price": 50.0,
#            "variancepercentage": 0,
#            "status": 0,
#            "seller": "xtrem"
#        }
#    }
    if data_dict['responseCode'] != 200:
        return False, False, False, False
    prd = data_dict['preferencePojo']
    name = prd['product_scrap']
    price = prd['price']
    seller = prd['seller']
    return True, name, price, seller, prd


def post_data(data_list, min_price, competion, comp_price, time, url, prd):
    response = None
    uploaded = False
    upload = ''
    for data in data_list:
        sub = {
            "siteUrl": url,
            "productName": data['name'],
            "preferenceId": prd['preferenceId'],
            "minPrice": min_price,
            "userPrice": prd['price'],
            "competitionPrice": comp_price,
            "seller": data['merchant'],
            "processing_time": data['time'] + time,
            "competionName": competion
        }
        # For API
        # while True:
        #     try:
        #         response = post(post_url, json=sub)
        #         if response.status_code == 200:
        #             break
        #     except:
        #         print('Can\'t post data retrying in 3 seconds')
        #         sleep(3)
        if float(data['price']) == float(min_price) and not uploaded:
            response = post(post_url, json=sub)
            upload = sub
            uploaded = True
        # For Manual
        print(f"{sub['productName']}\n user price: {sub['userPrice']}, min price: {sub['minPrice']}, comp price: {sub['competitionPrice']} actual price: {data['price']}\n")
    print(f'\n\nuploaded data:-\n{upload}\n\n')
    #sleep(10)      #for evry input
    return response


def calculate(data_list, price):
    p_l = []
    m_l = []
    for i in data_list:
        if i['price'] != '0':
            p_l.append(i['price'])
            m_l.append((i['merchant'], i['price']))
    try:
        min_price = min(p_l)
    except:
        min_price = '0'
    p_l.sort()

    for p in p_l:
        try:
            if float(p) > price:
                for m in m_l:
                    if m[1] == p:
                        return min_price, m[0], m[1]
        except:
            pass

    return min_price, 'NA', 0


def clean_text(string: str):
    text = ''
    for char in string:
        if char not in punctuation.replace('()', '').replace('&', ''):
            text = text + char
    return text


def clean_price(string: str):
    price = ''
    acceptable = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '.']
    for char in string:
        if char in acceptable:
            price = price + char
    return price


def sort_price(data_list: list):
    price_list = [n['price'] for n in data_list]
    try:
        price_list.sort(reverse=False)
    except:
        pass
    data_sorted = []
    for price in price_list:
        for single_data in data_list:
            if single_data['price'] == price and single_data not in data_sorted:
                data_sorted.append(single_data)

    return data_sorted


class Compare:
    @staticmethod
    def clean_text(given_string: str):
        text = ''.join([word for word in given_string if word not in punctuation])
        text = text.lower()
        return text

    @staticmethod
    def cosine_sim_vectors(vec1, vec2):
        vec1 = vec1.reshape(1, -1)
        vec2 = vec2.reshape(1, -1)

        return cosine_similarity(vec1, vec2)[0][0]

    def filter(self, main_string: str, to_compare: list, given_filter: float):
        t1 = datetime.now()
        print(f'{len(to_compare)} Data Found', end=' ')
        words = []
        for i in to_compare:
            words.append(i['name'])

        words.append(main_string)
        cleaned = list(map(self.clean_text, words))
        vectorized = CountVectorizer().fit_transform(cleaned)
        vector = vectorized.toarray()
        original = vector[-1]
        products = vector[:-1]
        filtered = []
        n = 0
        for product in products:
            similarity = self.cosine_sim_vectors(product, original)
            if similarity >= given_filter:
                filtered.append(to_compare[n])
            n += 1
        ret_data = []
        for i in to_compare:
            for j in filtered:
                if i == j:
                    ret_data.append(i)
        print(f'{len(ret_data)} will be uploaded..')
        return sort_price(ret_data), (datetime.now() - t1).total_seconds() / len(to_compare)
