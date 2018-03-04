# -*- coding: utf-8 -*-
"""
@author: Vikram Kohli

URLs used for testing:
https://www.allrecipes.com/recipe/13076/bacon-and-potato-soup/
https://www.allrecipes.com/recipe/100506/irish-potato-farls/

Edge cases to be accounted for in the ingredient parser:
'1/4 cup all-purpose flour, plus extra for dusting'; the clause beginning with 'plus' doesn't do so hot
The word 'cup' is interpreted by NLTK's tagger as an adjective?? 
I'm just gonna... manually fix that as well as any other edge cases that show up
"""

import time
from bs4 import BeautifulSoup
import urllib.request
from nltk import pos_tag, word_tokenize
from nltk import wordnet as wn
import sys

'''
URLs used for testing:
'''   

#  Corrections for the NLTK part-of-speech tagger; can just update this while testing on various recipes
NN_corrections = ['cup']
JJ_corrections = ['small', 'medium', 'large']

# was thinking of puting some stuff like 'extra' in here, but what about like... 'extra-virgin olive oil'
# something to consider, I guess
CD_corrections = []     

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

def parse_ingredient(description):
    ing_data = {'name': [], 'quantity': [], 'measurement': [], 'descriptor': [], 'preparation': []}
    text = word_tokenize(description)
    parts_tuples = pos_tag(text)
    parts = []
    # Some necessary preprocessing because the NLTK part-of-speech tagger is kinda meh sometimes
    for t in parts_tuples:
        if t[0] in NN_corrections:
            parts.append([t[0], 'NN'])
        elif t[0] in JJ_corrections:
            parts.append([t[0], 'JJ'])
        elif t[0] in CD_corrections:
            parts.append([t[0], 'CD'])
        else:
            parts.append(list(t))
    print(description) # temporary: to delete
    i = 0
    while(i < len(parts)):
        if parts[i][1] == 'CD':
            ing_data['quantity'].append(parts[i][0])
            if len(parts[i:]) > 1:
                if (parts[i+1][1] == 'NN' or parts[i+1][1] == 'NNS'):
                    if len(parts[i:]) <= 2 or parts[i+2][1] != ',':
                        ing_data['measurement'].append(parts[i+1][0])
                        i = i+1
                elif len(parts[i:]) > 2:
                    if parts[i+1][1] == 'JJ' and (parts[i+2][1] == 'NN' or parts[i+2][1] == 'NNS'):
                        if len(parts[i:]) <= 3 or parts[i+3][1] != ',':
                            ing_data['descriptor'].append(parts[i+1][0])
                            ing_data['measurement'].append(parts[i+2][0])
                            i = i + 2
        elif parts[i][1] == 'RB':
            if parts[i+1][1] == 'VBD':
                ing_data['preparation'].append(parts[i][0])
        elif parts[i][1] == 'VBD':
            ing_data['preparation'].append(parts[i][0])
        elif parts[i][1] == 'JJ':
            ing_data['descriptor'].append(parts[i][0])
            if len(parts[i:]) > 1 and (parts[i][0] == 'low' or parts[i][0] == 'high') and (parts[i+1][1] == 'NN' or parts[i+1][1] == 'RB'):
                ing_data['descriptor'].append(parts[i+1][0])
                i = i + 1
        elif parts[i][1] == 'NN' or parts[i][1] == 'NNS' or parts[i][1] == 'NNP':
            ing_data['name'].append(parts[i][0])
        i = i + 1
    print(ing_data)

if __name__ == '__main__':
    all_strings = fetch_page("https://www.allrecipes.com/recipe/100506/irish-potato-farls/")
    ing_strings = all_strings[0]
    dir_strings = all_strings[1]
    for ing_string in ing_strings:
        parse_ingredient(ing_string)

 