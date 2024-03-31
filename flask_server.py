from flask import Flask, send_from_directory, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import random, string
import requests
import os
import threading
import time

plantnet_key = "2b10DLylT9jvQ1NN9Zp7DfSZO"
trefle_key = "7692y6buPOpY7oDTKpYzfxklyC0OLm8d4NkJiAwdKPs"

current_image_number = 0
namesize = 12

base_image_url = 'http://hikersharvest.tech/images/'
base_plantnet_url = "https://my-api.plantnet.org/v2/identify/all?"
base_trefle_url = "http://trefle.io/api/v1/species/"


toxic_cats = {}
toxic_dogs = {}
toxic_horses = {}

SIZE = 256, 256

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


######## INTERNAL FUNCTIONS ######

def randomstring(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


def plant_net_api_call(image_urls):
    response = requests.get(base_plantnet_url + "images=" + image_urls + "&include-related-images=false&no-reject=false&lang=en&api-key=" + plantnet_key)
    ## you should probably toss in some error handling here
    return response

def trefle_api_call(scientific_name):
    response = requests.get(base_trefle_url + "search?" + "q=" + scientific_name + "&limit=1" + "&token=" + trefle_key)
    link = response.json()['data'][0]['links']['self']
    result = requests.get("http://trefle.io" + link + "?token=" + trefle_key)
    return result

def clear_image(image_name):
    time.sleep(6)
    os.remove('mysite/images/' + image_name + '.jpg')

def generate_wiki_url(name):
    return "https://en.wikipedia.org/wiki/" + "_".join(name.split())

def load_toxicity_values():
    with open("/home/therealestforager/toxicity/toxic_for_cats.txt", 'r') as file:
        while True:
            line = file.readline()

            if not line:
                break
            lower = line.lower()
            sections = lower.strip().split(" ")
            for section in sections:
                toxic_cats[section] = 1
    with open("/home/therealestforager/toxicity/toxic_for_dogs.txt", 'r') as file:
        while True:
            line = file.readline()

            if not line:
                break
            lower = line.lower()
            sections = lower.strip().split(" ")
            for section in sections:
                toxic_dogs[section] = 1
    with open("/home/therealestforager/toxicity/toxic_for_horses.txt", 'r') as file:
        while True:
            line = file.readline()

            if not line:
                break
            lower = line.lower()
            sections = lower.strip().split(" ")
            for section in sections:
                toxic_horses[section] = 1





##### FLASK API ######


@app.route('/')
def home():
    return "Welcome to Hiker's Harvest!"


## kowalski, analysis
@app.route('/id-plant', methods=['POST'])
def handle_image_input():

    if request.method == 'POST':
        file = request.files['image']
        name = randomstring(namesize)
        file.save('mysite/images/' + name + '.jpg')
        ## delete the file after 6 seconds
        thread = threading.Thread(target=clear_image, kwargs={'image_name':name})
        thread.start()
        url = base_image_url + name + '.jpg'
        response = plant_net_api_call(url)
        data = response.json()
        #### is it even a plant?
        if 'results' not in data:
            return jsonify(None)
        scientific_name = data['results'][0]['species']['scientificNameWithoutAuthor']
        plant_info = trefle_api_call(scientific_name).json()



        ## here we construct the final chunk of data

        final_chunk = {}

        final_chunk['confidence'] = data['results'][0]['score']
        final_chunk['common_name'] = data['results'][0]['species']['commonNames'][0]
        final_chunk['scientific_name'] = scientific_name
        final_chunk['edible_humans'] = plant_info['data']['edible']
        lower = scientific_name.lower()
        split_name = lower.split(" ")
        for name in split_name:
            if name in toxic_cats:
                final_chunk['edible_cats'] = False
                break
            else:
                 final_chunk['edible_cats'] = True
        for name in split_name:
            if name in toxic_dogs:
                final_chunk['edible_dogs'] = False
                break
            else:
                 final_chunk['edible_dogs'] = True
        for name in split_name:
            if name in toxic_horses:
                final_chunk['edible_horses'] = False
                break
            else:
                 final_chunk['edible_horses'] = True

        final_chunk['toxicity'] = plant_info['data']['specifications']['toxicity']
        final_chunk['wikipedia_url'] = generate_wiki_url(final_chunk['common_name'])

        return jsonify(final_chunk)
    else:
        return 400, jsonify("Failure :(")




## image url retrieval
@app.route('/images/<image_name>/')
def get_image(image_name):
    return send_from_directory('images', image_name)


load_toxicity_values()
