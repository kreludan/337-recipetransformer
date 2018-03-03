# -*- coding: utf-8 -*-
"""
@author: Vikram Kohli

URLs used for testing:
https://www.allrecipes.com/recipe/13076/bacon-and-potato-soup/
https://www.allrecipes.com/recipe/100506/irish-potato-farls/

Edge cases to be accounted for in the ingredient parser:
'1/4 cup all-purpose flour, plus extra for dusting'; the clause beginning with 'plus' doesn't do so hot
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
    ing_data = [[],[],[],[],[]]     # name, quantity, measurement, descriptor, preparation
    text = word_tokenize(description)
    parts = pos_tag(text)
    i = 0
    print(description)
    while(i < len(parts)):
        print(parts[i][0])
        if parts[i][1] == 'CD':
            ing_data[1].append(parts[i][0])
            if (parts[i+1][1] == 'NN' or parts[i+1][1] == 'NNS') and parts[i+2][1] != ',':
                print('hit')
                ing_data[2].append(parts[i+1][0])
                i = i+1
            elif parts[i+1][1] == 'JJ' and (parts[i+2][1] == 'NN' or parts[i+2][1] == 'NNS') and parts[i+3][1] != None and parts[i+3][1] != ',':
                ing_data[3].append(parts[i+1][0])
                ing_data[2].append(parts[i+2][0])
                i = i+2
        elif parts[i][1] == 'RB':
            if parts[i+1][1] == 'VBD':
                ing_data[4].append(parts[i][0])
        elif parts[i][1] == 'VBD':
            ing_data[4].append(parts[i][0])
        elif parts[i][1] == 'JJ':
            ing_data[3].append(parts[i][0])
            if (parts[i][0] == 'low' or parts[i][0] == 'high') and (parts[i+1][1] == 'NN' or parts[i+1][1] == 'RB'):
                ing_data[3].append(parts[i+1][0])
                i = i+1
        elif parts[i][1] == 'NN' or parts[i][1] == 'NNS' or parts[i][1] == 'NNP':
            ing_data[0].append(parts[i][0])
        i = i+1
    print(ing_data)

if __name__ == '__main__':
    all_strings = fetch_page("https://www.allrecipes.com/recipe/100506/irish-potato-farls/")
    ing_strings = all_strings[0]
    dir_strings = all_strings[1]
    for ing_string in ing_strings:
        parse_ingredient(ing_string)

 