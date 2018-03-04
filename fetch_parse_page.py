# -*- coding: utf-8 -*-
"""
@author: Vikram Kohli

Ingredient parser testing; URLs used + issues encountered

https://www.allrecipes.com/recipe/13076/bacon-and-potato-soup/
Issues: no huge ones; used this recipe as a 'starting point' for making the parser

https://www.allrecipes.com/recipe/100506/irish-potato-farls/
Issues: '1/4 cup all-purpose flour, plus extra for dusting' didn't do so great (esp. the clause w/ 'plus')
The word 'cup' is interpreted by NLTK's tagger as an adjective? Same with 'medium' as a noun.
Gonna keep a running global list of these things that can be manually fixed before parsing, at the top of the file.

https://www.allrecipes.com/recipe/79754/lauries-stuffed-peppers/
More manual fixes required... maybe there's a better part-of-speech tagger out there
Forgot to account for details that are included in parentheses; I think they probably belong in the descriptor section
How to deal with words like 'with'? At least for the first try, I'm gonna just append 'with' to both the name and descriptor
Because it seems like that'll be sufficient to tell what's going on

https://www.allrecipes.com/recipe/11116/cream-cheese-sugar-cookies/
First big issue with the parser shows up here... '1 egg yolk' has the parser thinking 'egg' is the measurement.
Probably just best to keep a running list of 'measurement' words, and separate food items from measurements based on that.
This fixed it for this URL; double checked with other recipes and seemed good.

https://www.allrecipes.com/recipe/11901/to-die-for-fettuccini-alfredo/
Small issue; 'ground' isn't picked up as a past-tense verb, but as a noun; adding a fix
Updating 'to taste' to be a measurement worked out OK

https://www.allrecipes.com/recipe/12804/seared-scallops-with-spicy-papaya-sauce/
Labeled as a 'gourmet'/complex recipe, so maybe something will happen? (':
Nope. It was getting confused about verb past participles but that was fixed fairly fast
"""

from bs4 import BeautifulSoup
import urllib.request
from nltk import pos_tag, word_tokenize

#   For now, the URL has to be manually changed here
#   Ideally by the end we'll have some walkthrough / user input interface which will be nicer
set_url = "https://www.allrecipes.com/recipe/12804/seared-scallops-with-spicy-papaya-sauce/"

def fetch_page(link):
    with urllib.request.urlopen(link) as url:
        s = url.read()
        soup = BeautifulSoup(s, "lxml")
        
        # Fetch ingredients
        
        ing_spans = soup.findAll("span", {"class": "recipe-ingred_txt added"})
        ing_strings = [span.text for span in ing_spans]
    
        # Fetch directions
        
        dir_spans = soup.findAll("span", {"class": "recipe-directions__list--item"})
        dir_strings = [span.text for span in dir_spans]
        
        return [ing_strings, dir_strings]

def deparenthesize(tokenized_phrase):   # stuff in parentheses most often seems like descriptors, so just doing that beforehand
    parenthesized_indices = []
    for i in range(0, len(tokenized_phrase)):
        if tokenized_phrase[i] == '(':
            parenthesized_indices.append(i)
            for j in range(i+1, len(tokenized_phrase)):
                parenthesized_indices.append(j)
                if tokenized_phrase[j] == ')':
                    break
    deparenthesized = [tokenized_phrase[i] for i in range(0, len(tokenized_phrase)) if i not in parenthesized_indices]
    parenthesized = [tokenized_phrase[i] for i in range(0, len(tokenized_phrase)) if i in parenthesized_indices]
    return [deparenthesized, parenthesized]

def parse_ingredient(description):
    #  Keeping a running list of types of measurements; seems like a reasonable way to resolve it
    measurements = ['cup', 'dash', 'can', 'pack', 'pint', 'teaspoon', 'tablespoon', 'pound', 'ounce', 'pinch', 
                    'clove', 'stalk', 'slices']

    #  Corrections for the NLTK part-of-speech tagger; can just update this while testing on various recipes
    JJ_corrections = ['small', 'medium', 'large']
    VBD_corrections = ['ground']
    
    #  was thinking of puting some stuff like 'extra' / 'to taste' as numbers, but what about like... 'extra-virgin olive oil'
    #  something to consider, I guess
    CD_corrections = []     
    
    #  maybe to change, idk; seems like the only place we'd need it
    NN_corrections = ['with']
    
    
    ing_data = {'name': [], 'quantity': [], 'measurement': [], 'descriptor': [], 'preparation': []}
    tokens = word_tokenize(description)
    
    
    #  Stuff in parentheses gets auto-chosen as a descriptor
    text = deparenthesize(tokens)[0]
    ing_data['descriptor'] = deparenthesize(tokens)[1]
    parts_tuples = pos_tag(text)


    #  Some necessary preprocessing because the NLTK part-of-speech tagger is kinda meh sometimes; also to get measurement words
    parts = []
    for t in parts_tuples:
        is_measurement = False
        for m in measurements:
            if m in t[0]:
                is_measurement = True
                break
        if is_measurement == True:
            parts.append([t[0], 'MEASUREMENT'])
        elif t[0] in NN_corrections:
            parts.append([t[0], 'NN'])
        elif t[0] in JJ_corrections:
            parts.append([t[0], 'JJ'])
        elif t[0] in VBD_corrections:
            parts.append([t[0], 'VBD'])
        elif t[0] in CD_corrections:
            parts.append([t[0], 'CD'])
        else:
            parts.append(list(t))
            
            
    #print(description) 
    
    # Classify relevant words based on their part of speech / assigned tag
    i = 0
    while(i < len(parts)):
        # Special case before everything else; the phrase 'to taste' should be a measurement
        if len(parts[i:]) > 1 and parts[i][0] == 'to' and parts[i+1][0] == 'taste':
            ing_data['measurement'].append(parts[i][0])
            ing_data['measurement'].append(parts[i+1][0])
            i = i+1
        # Rest of it is handled as usual, according to modified part-of-speech tags
        if parts[i][1] == 'CD':
            ing_data['quantity'].append(parts[i][0])
        elif parts[i][1] == 'MEASUREMENT':
            ing_data['measurement'].append(parts[i][0])
        elif parts[i][1] == 'RB':
            if parts[i+1][1] == 'VBD' or parts[i+1][1] == 'VBN':
                ing_data['preparation'].append(parts[i][0])
        elif parts[i][1] == 'VBD' or parts[i][1] == 'VBN':
            ing_data['preparation'].append(parts[i][0])
        elif parts[i][1] == 'JJ':
            ing_data['descriptor'].append(parts[i][0])
            if len(parts[i:]) > 1 and (parts[i][0] == 'low' or parts[i][0] == 'high') and (parts[i+1][1] == 'NN' or parts[i+1][1] == 'RB'):
                ing_data['descriptor'].append(parts[i+1][0])
                i = i + 1
        elif parts[i][1] == 'NN' or parts[i][1] == 'NNS' or parts[i][1] == 'NNP' or parts[i][1] == 'VBG':
            ing_data['name'].append(parts[i][0])
        i = i + 1
    return ing_data

if __name__ == '__main__':
    all_strings = fetch_page(set_url)
    ing_strings = all_strings[0]
    dir_strings = all_strings[1]
    for ing_string in ing_strings:
        print(parse_ingredient(ing_string))

 
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    