''' random name generator '''

import random
from satorilib.utils.name import adjectives, animals, foods

def getRandomNoun():
    if random.randint(1, 100) > 13:
        return random.choice(animals.animals)
    else:
        return random.choice(foods.foods)
    
def getRandomName():
    return random.choice(adjectives.adjectivesUpperCase) + ' ' + getRandomNoun()